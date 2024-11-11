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
    response = requests.get(download_url, stream=True)
    if response.status_code != 200:
        raise Exception(f"Failed to download image from {download_url}")

    # Save the downloaded image to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
        temp_image_path = temp_file.name
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)

    # Simulate image processing (copy the file for now)
    with open(temp_image_path, 'rb') as input_file, tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as processed_file:
        processed_image_path = processed_file.name
        processed_file.write(input_file.read())

    # Upload the processed image back to the Flask server
    with open(processed_image_path, 'rb') as processed_file:
        files = {'image': processed_file}
        upload_response = requests.post(upload_url, files=files)

    # Clean up temporary files
    os.remove(temp_image_path)
    os.remove(processed_image_path)

    if upload_response.status_code != 200:
        raise Exception("Failed to upload processed image")

    return {'status': 'success', 'image_id': image_id}