const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('capture-btn');
const resultImg = document.getElementById('result-img');
const statusMsg = document.getElementById('status-msg');
const promptSelect = document.getElementById('prompt-select');
const einwilligungDialog = document.getElementById('einwilligung-dialog');
const einwilligungAkzeptieren = document.getElementById('einwilligung-akzeptieren');
const einwilligungAblehnen = document.getElementById('einwilligung-ablehnen');

const basePath = '/kifotobox';
const SERVER_URL = `${window.location.origin}${basePath}`;
let imageId = null;
console.log(`Server URL: ${SERVER_URL}`);
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

// Show the consent dialog
function showEinwilligungDialog() {
    einwilligungDialog.style.display = 'block';
}

// Hide the consent dialog
function hideEinwilligungDialog() {
    einwilligungDialog.style.display = 'none';
}
// Upload the captured image to the server with the selected prompt
async function uploadImage(imageData) {
    try {
        const blob = dataURItoBlob(imageData);
        const formData = new FormData();
        formData.append('image', blob, 'photo.jpg');
        formData.append('prompt_id', promptSelect.value);

        const response = await axios.put(`${SERVER_URL}/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });

        imageId = response.data.image_id;
        statusMsg.textContent = `Image uploaded. Chosen prompt: ${response.data.prompt}. Waiting for processing...`;
        checkForProcessedImage();
    } catch (error) {
        console.error('Error uploading image:', error);
        alert('Failed to upload image.');
    }
}
// Function to generate a QR code
function generateQRCode(url) {
    const qrCodeContainer = document.getElementById('qrcode');
    qrCodeContainer.innerHTML = ''; // Clear any previous QR code
    new QRCode(qrCodeContainer, {
        text: url,
        width: 200,
        height: 200,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
    });
}

// Poll the server for the processed image
async function checkForProcessedImage() {
    if (!imageId) return;

    try {
        const response = await axios.get(`${SERVER_URL}/processed/${imageId}`);
        if (response.status === 200) {
            const imageUrl = `${SERVER_URL}/processed/${imageId}`;
            resultImg.src = imageUrl;
            resultImg.style.display = 'block';
            statusMsg.textContent = 'Here is your processed image!';
            generateQRCode(imageUrl);
            document.getElementById('qr-container').style.display = 'block';
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
captureBtn.addEventListener('click', showEinwilligungDialog);

// Event listener for the "Zustimmen" button
einwilligungAkzeptieren.addEventListener('click', () => {
    hideEinwilligungDialog();
    const imageData = captureImage();
    uploadImage(imageData);
});

// Event listener for the "Ablehnen" button
einwilligungAblehnen.addEventListener('click', hideEinwilligungDialog);

// Start the webcam when the page loads
startCamera();
