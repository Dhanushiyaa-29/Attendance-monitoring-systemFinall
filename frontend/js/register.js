/**
 * register.js — Employee Registration Logic
 * Handles camera access, face capture, file upload, and API submission.
 */

const API_BASE = 'http://127.0.0.1:8000';

// ── DOM References ────────────────────────────────────────────
const nameInput        = document.getElementById('employee-name');
const idInput          = document.getElementById('employee-id');
const cameraPanel      = document.getElementById('camera-panel');
const cameraPlaceholder= document.getElementById('camera-placeholder');
const cameraVideo      = document.getElementById('camera-video');
const cameraCanvas     = document.getElementById('camera-canvas');
const overlayGuide     = document.getElementById('camera-overlay-guide');
const statusText       = document.getElementById('camera-status-text');
const btnStart         = document.getElementById('btn-start-camera');
const btnCapture       = document.getElementById('btn-capture');
const btnRetake        = document.getElementById('btn-retake');
const btnRegister      = document.getElementById('btn-register');
const uploadInput      = document.getElementById('upload-photo');
const registerForm     = document.getElementById('register-form');
const registerCard     = document.getElementById('register-card');
const successCard      = document.getElementById('success-card');
const successMessage   = document.getElementById('success-message');
const successDetails   = document.getElementById('success-details');
const btnRegisterAnother = document.getElementById('btn-register-another');

// ── State ─────────────────────────────────────────────────────
let stream       = null;
let capturedBlob = null;
let capturedFrom = null; // 'camera' | 'upload'

// ── Toast Utility ─────────────────────────────────────────────
function showToast(title, message, type = 'info') {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type]}</span>
    <div>
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('toast-exit');
    setTimeout(() => toast.remove(), 300);
  }, 5000);
}

// ── Step Indicator ────────────────────────────────────────────
function setStep(step) {
  [1, 2, 3].forEach(i => {
    const el = document.getElementById(`step-${i}`);
    el.classList.remove('active', 'done');
    if (i < step) el.classList.add('done');
    else if (i === step) el.classList.add('active');
  });
}

// ── Validate Form ─────────────────────────────────────────────
function validateForm() {
  const nameOk = nameInput.value.trim().length >= 2;
  const idOk   = /^[A-Za-z0-9_-]{2,20}$/.test(idInput.value.trim());
  const faceOk = capturedBlob !== null;
  btnRegister.disabled = !(nameOk && idOk && faceOk);
  if (nameOk && idOk && !faceOk) setStep(2);
  else if (nameOk && idOk && faceOk) setStep(3);
  else setStep(1);
}

nameInput.addEventListener('input', validateForm);
idInput.addEventListener('input', validateForm);

// ── Camera Controls ───────────────────────────────────────────
async function startCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
    });
    cameraVideo.srcObject = stream;
    cameraPlaceholder.classList.add('hidden');
    cameraVideo.classList.remove('hidden');
    cameraCanvas.classList.add('hidden');
    cameraPanel.classList.add('active');
    overlayGuide.style.display = 'block';
    statusText.textContent = 'Position your face inside the guide';

    btnStart.classList.add('hidden');
    btnCapture.classList.remove('hidden');
    btnRetake.classList.add('hidden');

    showToast('Camera Active', 'Position your face in the oval guide and click Capture.', 'info');
  } catch (err) {
    console.error('Camera error:', err);
    showToast('Camera Error', `Could not access camera: ${err.message}. Try uploading a photo instead.`, 'error');
  }
}

function captureFrame() {
  if (!stream) return;
  const width  = cameraVideo.videoWidth  || 640;
  const height = cameraVideo.videoHeight || 480;
  cameraCanvas.width  = width;
  cameraCanvas.height = height;
  const ctx = cameraCanvas.getContext('2d');
  ctx.drawImage(cameraVideo, 0, 0, width, height);

  cameraCanvas.toBlob(blob => {
    capturedBlob  = blob;
    capturedFrom  = 'camera';
    // Stop stream
    stopCamera();
    // Show canvas
    cameraVideo.classList.add('hidden');
    cameraCanvas.classList.remove('hidden');
    overlayGuide.style.display = 'none';
    cameraPanel.classList.remove('active');
    cameraPanel.classList.add('captured');

    btnCapture.classList.add('hidden');
    btnRetake.classList.remove('hidden');
    btnStart.classList.add('hidden');

    showToast('Face Captured', 'Photo captured successfully. You can retake or proceed to register.', 'success');
    validateForm();
  }, 'image/jpeg', 0.92);
}

function retake() {
  capturedBlob = null;
  capturedFrom = null;
  cameraCanvas.classList.add('hidden');
  cameraPlaceholder.classList.remove('hidden');
  cameraPanel.classList.remove('captured', 'active');
  btnRetake.classList.add('hidden');
  btnCapture.classList.add('hidden');
  btnStart.classList.remove('hidden');
  validateForm();
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
}

btnStart.addEventListener('click', startCamera);
btnCapture.addEventListener('click', captureFrame);
btnRetake.addEventListener('click', retake);

// ── File Upload ───────────────────────────────────────────────
uploadInput.addEventListener('change', () => {
  const file = uploadInput.files[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    showToast('Invalid File', 'Please select a valid image file (JPEG, PNG).', 'error');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showToast('File Too Large', 'Image must be smaller than 10 MB.', 'error');
    return;
  }

  stopCamera();
  capturedBlob = file;
  capturedFrom = 'upload';

  // Preview in canvas
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => {
      cameraCanvas.width  = img.width;
      cameraCanvas.height = img.height;
      const ctx = cameraCanvas.getContext('2d');
      ctx.drawImage(img, 0, 0);

      cameraPlaceholder.classList.add('hidden');
      cameraVideo.classList.add('hidden');
      cameraCanvas.classList.remove('hidden');
      overlayGuide.style.display = 'none';
      cameraPanel.classList.remove('active');
      cameraPanel.classList.add('captured');

      btnStart.classList.add('hidden');
      btnCapture.classList.add('hidden');
      btnRetake.classList.remove('hidden');

      showToast('Photo Loaded', `"${file.name}" loaded for registration.`, 'success');
      validateForm();
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
});

// ── Form Submission ───────────────────────────────────────────
registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!capturedBlob) {
    showToast('No Face Image', 'Please capture or upload a face photo first.', 'warning');
    return;
  }

  const name       = nameInput.value.trim();
  const employeeId = idInput.value.trim().toUpperCase();

  // Validate
  if (!name || name.length < 2) {
    showToast('Invalid Name', 'Please enter a valid full name (at least 2 characters).', 'warning');
    return;
  }
  if (!/^[A-Za-z0-9_-]{2,20}$/.test(employeeId)) {
    showToast('Invalid ID', 'Employee ID must be 2-20 alphanumeric characters.', 'warning');
    return;
  }

  // Loading state
  btnRegister.disabled = true;
  btnRegister.innerHTML = '<span class="btn-spinner"></span> Registering...';
  btnRegister.classList.add('btn-loading');

  try {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('employee_id', employeeId);
    formData.append('face_image', capturedBlob, 'face.jpg');

    const res = await fetch(`${API_BASE}/employee/register`, {
      method: 'POST',
      body: formData,
    });

    const data = await res.json();

    if (res.ok && data.success) {
      // Show success card
      registerCard.classList.add('hidden');
      successCard.classList.remove('hidden');
      successMessage.textContent = data.message;
      successDetails.innerHTML = `
        <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-md);padding:16px;">
          <div class="result-row"><span class="result-label">Name</span><span class="result-value">${data.name}</span></div>
          <div class="result-row"><span class="result-label">Employee ID</span><span class="result-value">${data.employee_id}</span></div>
          <div class="result-row" style="border:none;"><span class="result-label">Registered On</span><span class="result-value">${data.created_at}</span></div>
        </div>
      `;
      stopCamera();
      showToast('Registered!', `${name} has been registered successfully.`, 'success');
    } else {
      const errorMsg = data.detail || 'Registration failed. Please try again.';
      showToast('Registration Failed', errorMsg, 'error');
      btnRegister.disabled = false;
      btnRegister.innerHTML = '✨ Register Employee';
      btnRegister.classList.remove('btn-loading');
    }
  } catch (err) {
    console.error('Registration error:', err);
    showToast('Connection Error', 'Could not connect to the backend. Make sure the server is running.', 'error');
    btnRegister.disabled = false;
    btnRegister.innerHTML = '✨ Register Employee';
    btnRegister.classList.remove('btn-loading');
  }
});

// ── Register Another ──────────────────────────────────────────
btnRegisterAnother.addEventListener('click', () => {
  successCard.classList.add('hidden');
  registerCard.classList.remove('hidden');
  nameInput.value = '';
  idInput.value   = '';
  capturedBlob    = null;
  capturedFrom    = null;
  cameraCanvas.classList.add('hidden');
  cameraPlaceholder.classList.remove('hidden');
  cameraPanel.classList.remove('captured', 'active');
  btnStart.classList.remove('hidden');
  btnCapture.classList.add('hidden');
  btnRetake.classList.add('hidden');
  btnRegister.disabled = true;
  btnRegister.innerHTML = '✨ Register Employee';
  setStep(1);
});

// ── Cleanup on page unload ─────────────────────────────────────
window.addEventListener('beforeunload', stopCamera);
