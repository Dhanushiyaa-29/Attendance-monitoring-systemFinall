/**
 * attendance.js — Attendance Marking Logic
 * Handles camera access, face capture, API verification, and result display.
 */

const API_BASE = 'http://127.0.0.1:8000';

// ── DOM References ────────────────────────────────────────────
const employeeIdInput  = document.getElementById('att-employee-id');
const cameraPanel      = document.getElementById('att-camera-panel');
const cameraPlaceholder= document.getElementById('att-camera-placeholder');
const cameraVideo      = document.getElementById('att-video');
const cameraCanvas     = document.getElementById('att-canvas');
const overlayGuide     = document.getElementById('att-overlay');
const statusText       = document.getElementById('att-status-text');
const btnStart         = document.getElementById('att-btn-start');
const btnCapture       = document.getElementById('att-btn-capture');
const btnRetake        = document.getElementById('att-btn-retake');
const btnVerify        = document.getElementById('att-btn-verify');
const uploadInput      = document.getElementById('att-upload');
const attendanceForm   = document.getElementById('attendance-form');
const resultArea       = document.getElementById('att-result-area');

// ── State ─────────────────────────────────────────────────────
let stream       = null;
let capturedBlob = null;

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

// ── Validate Form ─────────────────────────────────────────────
function validateForm() {
  const idOk   = /^[A-Za-z0-9_-]{2,20}$/.test(employeeIdInput.value.trim());
  const faceOk = capturedBlob !== null;
  btnVerify.disabled = !(idOk && faceOk);
}

employeeIdInput.addEventListener('input', validateForm);

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
    statusText.textContent = 'Look straight into the camera';

    btnStart.classList.add('hidden');
    btnCapture.classList.remove('hidden');
    btnRetake.classList.add('hidden');

    showToast('Camera Ready', 'Align your face in the guide circle, then click Capture.', 'info');
  } catch (err) {
    console.error('Camera error:', err);
    showToast('Camera Error', `${err.message}. Try uploading a photo instead.`, 'error');
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
    capturedBlob = blob;
    stopCamera();
    cameraVideo.classList.add('hidden');
    cameraCanvas.classList.remove('hidden');
    overlayGuide.style.display = 'none';
    cameraPanel.classList.remove('active');
    cameraPanel.classList.add('captured');

    btnCapture.classList.add('hidden');
    btnRetake.classList.remove('hidden');
    btnStart.classList.add('hidden');

    showToast('Captured', 'Face photo captured. Click Verify to submit.', 'success');
    validateForm();
  }, 'image/jpeg', 0.92);
}

function retake() {
  capturedBlob = null;
  cameraCanvas.classList.add('hidden');
  cameraPlaceholder.classList.remove('hidden');
  cameraPanel.classList.remove('captured', 'active');
  btnRetake.classList.add('hidden');
  btnCapture.classList.add('hidden');
  btnStart.classList.remove('hidden');
  resultArea.innerHTML = '';
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
    showToast('Invalid File', 'Please select a valid image file.', 'error');
    return;
  }

  stopCamera();
  capturedBlob = file;

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
      showToast('Photo Loaded', `"${file.name}" ready for verification.`, 'success');
      validateForm();
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
});

// ── Result Rendering ──────────────────────────────────────────
function renderResult(data) {
  resultArea.innerHTML = '';

  if (data.verified && data.attendance_recorded) {
    // ── SUCCESS ──
    const confPct = Math.round((data.confidence || 0) * 100);
    const confBarClass = confPct >= 80 ? '' : confPct >= 65 ? ' medium' : ' low';
    const approvalClass = {
      Approved: 'badge-success',
      Pending:  'badge-warning',
      Rejected: 'badge-danger',
    }[data.approval_status] || 'badge-neutral';

    resultArea.innerHTML = `
      <div class="card result-card result-success fade-in">
        <div class="card-body" style="padding:36px 32px;">
          <div class="result-icon">✅</div>
          <h2 style="text-align:center;font-size:1.3rem;font-weight:800;margin-bottom:4px;">Attendance Recorded</h2>
          <p style="text-align:center;color:var(--text-secondary);font-size:0.85rem;margin-bottom:28px;">
            Face verified successfully
          </p>

          <div>
            <div class="result-row">
              <span class="result-label">Employee Name</span>
              <span class="result-value">${data.name}</span>
            </div>
            <div class="result-row">
              <span class="result-label">Employee ID</span>
              <span class="result-value">${data.employee_id}</span>
            </div>
            <div class="result-row">
              <span class="result-label">Date</span>
              <span class="result-value">${data.date}</span>
            </div>
            <div class="result-row">
              <span class="result-label">Time</span>
              <span class="result-value">${data.time}</span>
            </div>
            <div class="result-row">
              <span class="result-label">Attendance Status</span>
              <span class="badge badge-success">● ${data.status}</span>
            </div>
            <div class="result-row">
              <span class="result-label">Approval Status</span>
              <span class="badge ${approvalClass}">${data.approval_status}</span>
            </div>
            <div class="result-row">
              <span class="result-label">Arrival</span>
              ${data.late
                ? '<span class="badge badge-warning">Late Arrival</span>'
                : '<span class="badge badge-success">On Time</span>'}
            </div>
            <div class="result-row" style="flex-direction:column;align-items:flex-start;gap:8px;border:none;">
              <div style="display:flex;justify-content:space-between;width:100%;">
                <span class="result-label">Face Match Confidence</span>
                <span class="result-value">${confPct}%</span>
              </div>
              <div class="confidence-bar" style="width:100%;">
                <div class="confidence-fill${confBarClass}" style="width:${confPct}%;"></div>
              </div>
            </div>
          </div>

          <div style="display:flex;gap:12px;margin-top:24px;">
            <a href="/result.html" class="btn btn-primary flex-1">📊 View Dashboard</a>
            <button class="btn btn-ghost flex-1" onclick="resetForm()">📸 Mark Another</button>
          </div>
        </div>
      </div>
    `;

  } else if (data.verified && !data.attendance_recorded) {
    // ── DUPLICATE ──
    const ex = data.existing_attendance || {};
    resultArea.innerHTML = `
      <div class="card result-card result-duplicate fade-in">
        <div class="card-body" style="padding:36px 32px;text-align:center;">
          <div class="result-icon" style="background:rgba(245,158,11,0.15);">📋</div>
          <h2 style="font-size:1.2rem;font-weight:800;margin-bottom:8px;">Already Recorded</h2>
          <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:20px;">
            Attendance for <strong>${data.employee_id}</strong> has already been submitted today.
          </p>
          ${ex.date ? `
            <div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-md);padding:16px;text-align:left;margin-bottom:20px;">
              <div class="result-row"><span class="result-label">Date</span><span class="result-value">${ex.date}</span></div>
              <div class="result-row"><span class="result-label">Time</span><span class="result-value">${ex.time}</span></div>
              <div class="result-row" style="border:none;"><span class="result-label">Approval</span><span class="badge badge-warning">${ex.approval_status}</span></div>
            </div>
          ` : ''}
          <div style="display:flex;gap:12px;">
            <a href="/result.html" class="btn btn-primary flex-1">📊 View Dashboard</a>
            <button class="btn btn-ghost flex-1" onclick="resetForm()">🔄 Try Again</button>
          </div>
        </div>
      </div>
    `;

  } else {
    // ── FAILURE ──
    resultArea.innerHTML = `
      <div class="card result-card result-failed fade-in">
        <div class="card-body" style="padding:36px 32px;text-align:center;">
          <div class="result-icon" style="background:rgba(239,68,68,0.15);">❌</div>
          <h2 style="font-size:1.2rem;font-weight:800;margin-bottom:8px;color:#f87171;">Face Verification Failed</h2>
          <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:20px;">
            ${data.message || 'The submitted face does not match the registered employee.'}
          </p>
          <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);border-radius:var(--radius-md);padding:16px;text-align:left;margin-bottom:20px;">
            <div class="result-row"><span class="result-label">Employee ID</span><span class="result-value">${data.employee_id}</span></div>
            ${data.confidence !== undefined ? `
              <div class="result-row" style="flex-direction:column;align-items:flex-start;gap:8px;border:none;">
                <div style="display:flex;justify-content:space-between;width:100%;">
                  <span class="result-label">Match Confidence</span>
                  <span class="result-value" style="color:#f87171;">${Math.round((data.confidence||0)*100)}%</span>
                </div>
                <div class="confidence-bar" style="width:100%;">
                  <div class="confidence-fill low" style="width:${Math.round((data.confidence||0)*100)}%;"></div>
                </div>
              </div>
            ` : ''}
          </div>
          <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:20px;">
            Attendance was <strong>NOT</strong> recorded.
          </p>
          <div style="display:flex;gap:12px;">
            <button class="btn btn-danger flex-1" onclick="resetForm()">🔄 Try Again</button>
            <a href="/register.html" class="btn btn-outline flex-1">👤 Register First</a>
          </div>
        </div>
      </div>
    `;
  }

  // Scroll to result
  resultArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Reset Form ────────────────────────────────────────────────
function resetForm() {
  capturedBlob = null;
  cameraCanvas.classList.add('hidden');
  cameraPlaceholder.classList.remove('hidden');
  cameraPanel.classList.remove('captured', 'active');
  btnRetake.classList.add('hidden');
  btnCapture.classList.add('hidden');
  btnStart.classList.remove('hidden');
  resultArea.innerHTML = '';
  validateForm();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Form Submission ───────────────────────────────────────────
attendanceForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  if (!capturedBlob) {
    showToast('No Face Image', 'Please capture or upload your face photo first.', 'warning');
    return;
  }

  const employeeId = employeeIdInput.value.trim().toUpperCase();
  if (!/^[A-Za-z0-9_-]{2,20}$/.test(employeeId)) {
    showToast('Invalid ID', 'Please enter a valid Employee ID.', 'warning');
    return;
  }

  // Loading state
  btnVerify.disabled = true;
  btnVerify.innerHTML = '<span class="btn-spinner"></span> Verifying...';
  btnVerify.classList.add('btn-loading');
  resultArea.innerHTML = '';

  try {
    const formData = new FormData();
    formData.append('employee_id', employeeId);
    formData.append('face_image', capturedBlob, 'face.jpg');

    const res = await fetch(`${API_BASE}/attendance/verify`, {
      method: 'POST',
      body: formData,
    });

    const data = await res.json();

    if (res.ok || res.status === 200) {
      renderResult(data);
      if (data.verified && data.attendance_recorded) {
        showToast('Attendance Recorded!', `Welcome, ${data.name}! Attendance marked for ${data.date}.`, 'success');
      } else if (data.verified && !data.attendance_recorded) {
        showToast('Already Recorded', 'Your attendance was already submitted today.', 'warning');
      } else {
        showToast('Verification Failed', 'Face did not match. Attendance NOT recorded.', 'error');
      }
    } else {
      const errorMsg = data.detail || 'Verification failed. Please try again.';
      showToast('Error', errorMsg, 'error');
      renderResult({ verified: false, employee_id: employeeId, message: errorMsg });
    }
  } catch (err) {
    console.error('Attendance error:', err);
    showToast('Connection Error', 'Could not reach the backend. Make sure the server is running.', 'error');
  } finally {
    btnVerify.disabled = false;
    btnVerify.innerHTML = '🔍 Verify & Mark Attendance';
    btnVerify.classList.remove('btn-loading');
    validateForm();
  }
});

// ── Cleanup ───────────────────────────────────────────────────
window.addEventListener('beforeunload', stopCamera);
