from flask import Flask, request, jsonify, send_file, abort, make_response, render_template
from flask_cors import CORS
from celery import Celery
from celery.result import AsyncResult
import uuid
import os
import re

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)  # Enable CORS for all routes
app.config['UPLOAD_FOLDER'] = '/app/uploads'
app.config['PROCESSED_FOLDER'] = '/app/processed'
app.config['SERVER_URL'] = 'http://itlx8314:5000'
app.config['BASEPATH'] = '/kifotobox'
# Configure Celery
app.config['CELERY_BROKER_URL'] = 'redis://redis:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://redis:6379/0'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit to 16 MB

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Define a regular expression for a valid task_id (alphanumeric and dashes only)
TASK_ID_REGEX = re.compile(r'^[a-zA-Z0-9\-]{10,50}$')
PROMPTS=["A sepia-toned vintage photograph of a young student sitting casually on an ornate chair. He is wearing a formal suit with a graduation cap and has a relaxed, confident posture. The man is exuding a scholarly and nonchalant vibe. The setting is a simple studio with a plain backdrop and a curtain on one side, adding to the old-fashioned, antique aesthetic.",
         "An astronaut in space",
         "A formula one driver in front of is Formula one car. The setting is the racetrack.",
         "A scubadiver under water. The setting is a colorful coral reef with many fishes"]
    
def validate_task_id(task_id):
    if not TASK_ID_REGEX.match(task_id):
        abort(400, description="Invalid task_id format.")

basepath = app.config['BASEPATH']

# Route to serve the main webpage
@app.route(f'{basepath}/')
def index():
    return render_template('index.html')

# Route to serve the Datenschutzerklärung page
@app.route(f'{basepath}/datenschutz')
def datenschutz():
    return render_template('datenschutz.html')

# Upload route for the client to submit the image
@app.route(f'{basepath}/upload', methods=['PUT'])
def upload_image():
    if 'image' not in request.files  or 'prompt_id' not in request.form:
        return jsonify({'error': 'No image file or prompt id provided'}), 400, {'Content-Type': 'application/json'}

    image = request.files['image']
    prompt_id = int(request.form['prompt_id'])
    image_id = str(uuid.uuid4())
    server_url = f"{app.config['SERVER_URL']}{basepath}"

    if prompt_id < 0 or prompt_id >= len(PROMPTS):
        return jsonify({'error': 'Invalid prompt_id'}), 400
    
    # Save the image using the task ID
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{image_id}.jpg")
    image.save(image_path)

    try:
        task = celery.send_task('tasks.process_image_task', args=[image_id, server_url, PROMPTS[prompt_id], prompt_id])
    except Exception as e:
        os.remove(image_path)  # Cleanup the saved image if task submission fails
        return jsonify({'error': 'Failed to submit task'}), 500, {'Content-Type': 'application/json'}
    task_id = task.id

    return jsonify({'task_id': task_id, 'image_id': image_id}), 202, {'Content-Type': 'application/json'}

@app.route(f'{basepath}/status/<task_id>', methods=['GET'])
def get_status(task_id):
    # Validate the task_id parameter
    validate_task_id(task_id)

    result = AsyncResult(task_id, app=celery)
    if result.state == 'PENDING':
        return {'status': 'Processing'}, 202, {'Content-Type': 'application/json'}
    elif result.state == 'SUCCESS':
        return {'status': 'Completed', 'result': result.result}, 200, {'Content-Type': 'application/json'}
    else:
        return {'status': 'Failed'}, 500, {'Content-Type': 'application/json'}

# Route for the client to retrieve the processed image    
@app.route(f'{basepath}/processed/<image_id>', methods=['GET'])
def get_image(image_id):
    # Validate the task_id parameter
    validate_task_id(image_id)
    
    processed_image_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{image_id}.jpg")

    if not os.path.exists(processed_image_path):
        return jsonify({'error': 'Image not found'}), 404, {'Content-Type': 'application/json'}

        # Create the response object
    response = make_response(send_file(processed_image_path, mimetype='image/jpeg'))

    # Manually set Cache-Control headers to disable caching
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response

# Route for the worker to download the unprocessed image
@app.route(f'{basepath}/unprocessed/<image_id>', methods=['GET'])
def download_image(image_id):
    # Validate the task_id parameter
    validate_task_id(image_id)

    image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{image_id}.jpg")
    if not os.path.exists(image_path):
        return jsonify({'error': 'Image not found'}), 404, {'Content-Type': 'application/json'}
    return send_file(image_path, mimetype='image/jpeg', as_attachment=True)

# Route for the worker to upload the processed image
@app.route(f'{basepath}/processed/<image_id>', methods=['POST'])
def upload_processed_image(image_id):
    # Validate the task_id parameter
    validate_task_id(image_id)

    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400, {'Content-Type': 'application/json'}
    image = request.files['image']

    processed_image_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{image_id}.jpg")
    if os.path.exists(processed_image_path):
        return jsonify({'error': 'File already exists'}), 409, {'Content-Type': 'application/json'}
    image.save(processed_image_path)

    return jsonify({'status': 'success', 'image_id': image_id}), {'Content-Type': 'application/json'}

    
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
