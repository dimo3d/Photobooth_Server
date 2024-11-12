from flask import Flask, request, jsonify, send_file
from celery import Celery
from celery.result import AsyncResult
import uuid
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/app/uploads'
app.config['PROCESSED_FOLDER'] = '/app/processed'
app.config['SERVER_URL'] = 'http://flask-server:5000'
app.config['BASEPATH'] = '/KIFOTOBOX'
# Configure Celery
app.config['CELERY_BROKER_URL'] = 'redis://redis:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://redis:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Upload route for the client to submit the image
@app.route(f'{app.config['BASEPATH']}/upload', methods=['PUT'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    image = request.files['image']
    image_id = str(uuid.uuid4())
    server_url = f"{app.config['SERVER_URL']}"
    task = celery.send_task('tasks.process_image_task', args=[image_id, server_url])
    task_id = task.id

    # Save the image using the task ID
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{image_id}.jpg")
    image.save(image_path)

    return jsonify({'task_id': task_id, 'image_id': image_id}), 202

@app.route(f'{app.config['BASEPATH']}/status/<task_id>', methods=['GET'])
def get_status(task_id):
    result = AsyncResult(task_id, app=celery)
    if result.state == 'PENDING':
        return {'status': 'Processing'}, 202
    elif result.state == 'SUCCESS':
        return {'status': 'Completed', 'result': result.result}, 200
    else:
        return {'status': 'Failed'}, 500

# Route for the client to retrieve the processed image    
@app.route(f'{app.config['BASEPATH']}/processed/<image_id>', methods=['GET'])
def get_image(image_id):
    processed_image_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{image_id}.jpg")

    if not os.path.exists(processed_image_path):
        return jsonify({'error': 'Image not found'}), 404

    return send_file(processed_image_path, mimetype='image/jpeg')


# Route for the worker to download the unprocessed image
@app.route(f'{app.config['BASEPATH']}/unprocessed/<image_id>', methods=['GET'])
def download_image(image_id):
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{image_id}.jpg")
    if not os.path.exists(image_path):
        return jsonify({'error': 'Image not found'}), 404
    return send_file(image_path, mimetype='image/jpeg')

# Route for the worker to upload the processed image
@app.route(f'{app.config['BASEPATH']}/processed/<task_id>', methods=['POST'])
def upload_processed_image(task_id):
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    image = request.files['image']
    processed_image_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{task_id}.jpg")
    image.save(processed_image_path)

    return jsonify({'status': 'success', 'task_id': task_id})

    
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)