from celery import Celery
import os
import requests
import tempfile

# Initialize Celery app
celery = Celery('tasks', broker='redis://redis:6379/0')

UPLOAD_FOLDER = '/app/uploads'
PROCESSED_FOLDER = '/app/processed'

@celery.task(name="tasks.process_image_task")
def process_image_task(image_id, server_url):
    """
    Processes the image using the task ID as the identifier.
    """
    # Download the image from the Flask server
    download_url = f"{server_url}/unprocessed/{image_id}"
    upload_url = f"{server_url}/processed/{image_id}"
    headers = {
        "Accept": "image/jpeg",  # Explicitly request a JPEG image
        "User-Agent": "WorkerDownloader/1.0"
    }
    response = requests.get(download_url,headers=headers, stream=True, timeout=60)
    response.raise_for_status()  # Check for HTTP errors

    # Check if the response has a Content-Length header
    content_length = response.headers.get('Content-Length')
    if content_length:
        content_length = int(content_length)
        print(f"Expected Content-Length: {content_length} bytes")

    if response.status_code != 200:
        raise Exception(f"Failed to download image from {download_url}")

    # Verify the downloaded file size
    downloaded_size = len(response.content)
    print(f"Downloaded file size: {downloaded_size} bytes")

    # Save the downloaded image to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', dir='/app/tmp') as temp_file:
        temp_image_path = temp_file.name
        for chunk in response.iter_content(chunk_size=8196):
            if chunk:
                temp_file.write(chunk)
                temp_file.flush()
        print(f"Unprocessed image saved at: {temp_image_path}")
        file_size = os.path.getsize(temp_image_path)
        print(f"File written to disk: {temp_image_path} (Size: {file_size} bytes)")

    # Simulate image processing (copy the file in chunks)
    try:
        with open(temp_image_path, 'rb') as input_file, tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', dir='/app/tmp') as processed_file:
            processed_image_path = processed_file.name

            # Read and write the file in chunks
            while chunk := input_file.read(4096):  # 4 KB chunks
                processed_file.write(chunk)

            # Explicitly flush the buffer
            processed_file.flush()

        print(f"Processed image saved at: {processed_image_path}")
    except Exception as e:
        print(f"Error during file processing: {str(e)}")

    # Upload the processed image back to the Flask server
    with open(processed_image_path, 'rb') as processed_file:
        files = {'image': processed_file}
        upload_response = requests.post(upload_url, files=files, timeout=60)

    # Clean up temporary files
    os.remove(temp_image_path)
    os.remove(processed_image_path)

    if upload_response.status_code != 200:
        raise Exception("Failed to upload processed image")

    return {'status': 'success', 'image_id': image_id}