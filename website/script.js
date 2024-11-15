const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('capture-btn');
const resultImg = document.getElementById('result-img');
const statusMsg = document.getElementById('status-msg');

const SERVER_URL = 'http://localhost:5000/kifotobox';
let imageId = null;

// Access the user's webcam
async function startCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
    } catch (error) {
        console.error('Error accessing webcam:', error);
        alert('Could not access the webcam. Please check your browser permissions.');
    }
}

// Capture an image from the video feed
function captureImage() {
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg');
}

// Upload the captured image to the server
async function uploadImage(imageData) {
    try {
        const blob = dataURItoBlob(imageData);
        const formData = new FormData();
        formData.append('image', blob, 'photo.jpg');

        const response = await axios.put(`${SERVER_URL}/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        imageId = response.data.image_id;
        statusMsg.textContent = 'Image uploaded. Waiting for processing...';
        checkForProcessedImage();
    } catch (error) {
        console.error('Error uploading image:', error);
        alert('Failed to upload image.');
    }
}

// Poll the server for the processed image
async function checkForProcessedImage() {
    if (!imageId) return;

    try {
        const response = await axios.get(`${SERVER_URL}/processed/${imageId}`);
        if (response.status === 200) {
            resultImg.src = `${SERVER_URL}/processed/${imageId}`;
            resultImg.style.display = 'block';
            statusMsg.textContent = 'Here is your processed image!';
        } else {
            setTimeout(checkForProcessedImage, 2000); // Retry every 2 seconds
        }
    } catch (error) {
        console.error('Error checking for processed image:', error);
        setTimeout(checkForProcessedImage, 2000);
    }
}

// Convert a data URI to a Blob
function dataURItoBlob(dataURI) {
    const byteString = atob(dataURI.split(',')[1]);
    const mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }
    return new Blob([ab], { type: mimeString });
}

// Event listener for the capture button
captureBtn.addEventListener('click', () => {
    const imageData = captureImage();
    uploadImage(imageData);
});

// Start the webcam when the page loads
startCamera();
