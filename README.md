# Attendance Monitoring System — Smart Approval Process

> AI-powered face recognition attendance system with 68-point landmark alignment, duplicate detection, and smart approval workflow.

## Architecture

```
Employee Registration → Face Capture → SSD MobileNet V1 → 68 Landmarks → Face Embedding → MongoDB
Attendance Verification → Face Match → Smart Approval → Result UI
```

## Project Structure

```
attendance-monitoring-antigravity/
├── backend/
│   ├── main.py                    ← FastAPI app entry point
│   ├── database.py                ← Local MongoDB connection
│   ├── config.py                  ← Configuration / .env settings
│   ├── models/
│   │   ├── employee.py            ← Employee Pydantic models
│   │   └── attendance.py          ← Attendance & Approval models
│   ├── services/
│   │   ├── face_detector.py       ← SSD MobileNet V1 face detection
│   │   ├── face_landmark.py       ← 68-point landmark alignment
│   │   ├── face_recognition.py    ← 128-d face embedding generation
│   │   └── attendance_service.py  ← Smart approval logic
│   └── routes/
│       ├── employee.py            ← Registration endpoints
│       └── attendance.py          ← Verification & approval endpoints
├── frontend/
│   ├── index.html                 ← Home / landing page
│   ├── register.html              ← Employee registration
│   ├── attendance.html            ← Mark attendance
│   ├── result.html                ← Dashboard & approval
│   ├── css/style.css              ← Global design system
│   └── js/
│       ├── register.js            ← Registration logic
│       └── attendance.js          ← Attendance logic
├── models/
│   ├── ssd_mobilenet_v1/          ← SSD MobileNet V1 model files
│   ├── shape_predictor_68_face_landmarks/ ← dlib landmark model
│   └── face_recognition/          ← face_recognition library models
├── .env                           ← MongoDB credentials (DO NOT COMMIT)
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

> **Note on dlib/face-recognition:** These packages require C++ build tools.
> On Windows, install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
> Alternative: install pre-built wheels from https://github.com/jloh02/dlib

### 3. Start Local MongoDB
Ensure the MongoDB service is running on `localhost:27017`. The application uses the database `attendance-monitoring-system`; MongoDB creates it and its collections when data is first written.

```env
MONGODB_URI=mongodb://localhost:27017/
DATABASE_NAME=attendance-monitoring-system
```

### 4. Download Model Files (Optional but Recommended)

**SSD MobileNet V1** (better face detection):
```
models/ssd_mobilenet_v1/deploy.prototxt
models/ssd_mobilenet_v1/res10_300x300_ssd_iter_140000.caffemodel
```
Download: https://github.com/opencv/opencv/tree/master/samples/dnn/face_detector

**68-Point Landmarks** (face alignment):
```
models/shape_predictor_68_face_landmarks/shape_predictor_68_face_landmarks.dat
```
Download: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2

Without these files, the system falls back to Haar Cascade + simple crop.

### 5. Run the Application
```bash
uvicorn backend.main:app --reload
```

Open in browser:
- **App:** http://127.0.0.1:8000
- **API Docs:** http://127.0.0.1:8000/docs

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/employee/register` | Register employee + face embedding |
| GET  | `/employee/` | List all employees |
| GET  | `/employee/{id}` | Get single employee |
| POST | `/attendance/verify` | Verify face & submit attendance |
| GET  | `/attendance/` | All attendance records |
| GET  | `/attendance/{employee_id}` | Employee attendance history |
| GET  | `/attendance/result/{id}` | Get specific attendance record |
| POST | `/attendance/approval/{id}` | Manager approve/reject |
| GET  | `/health` | System health check |

## Smart Approval Logic

| Condition | Result |
|-----------|--------|
| High confidence (≥80%) + On time | ✅ Auto-Approved |
| Confidence ≥65% (any time) | ⏳ Pending (Manager Review) |
| Low confidence (<65%) | ❌ Rejected |

## Face Processing Pipeline

```
Camera Image
     ↓
SSD MobileNet V1 (Face Detection)
     ↓
68-Point Landmark Detection (Alignment)
     ↓
Face Recognition Network (128-d Embedding)
     ↓
Cosine / Euclidean Distance Comparison
     ↓
Match / No Match
```

## Security Notes

- Employee ID alone never grants attendance — face verification is always required
- Face embeddings are stored, **not** raw images
- Duplicate attendance is blocked at database level (unique index)
- Manager approval endpoints should be protected by role-based auth in production
- Add liveness detection (anti-spoofing) before production deployment
- Protect `.env` — never commit to version control

## MongoDB Collections

**employees**
```json
{
  "employee_id": "EMP001",
  "name": "Dinesh",
  "face_embedding": [0.023, -0.124, ...],
  "created_at": "2026-10-10"
}
```

**attendance**
```json
{
  "employee_id": "EMP001",
  "name": "Dinesh",
  "date": "2026-10-10",
  "time": "09:12:45",
  "status": "Present",
  "approval_status": "Pending",
  "confidence": 0.923,
  "late": false
}
```

**approval_requests**
```json
{
  "attendance_id": "...",
  "employee_id": "EMP001",
  "status": "Pending",
  "approved_by": null,
  "reason": null
}
```
# Attendance-monitoring-systemFinall
