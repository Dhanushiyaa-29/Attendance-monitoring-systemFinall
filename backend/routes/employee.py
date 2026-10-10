"""
Employee Routes — Registration and listing.
"""
import io
import logging
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.database import employees_collection
from backend.models.employee import EmployeeResponse
from backend.services.face_detector import decode_image, detect_faces
from backend.services.face_landmark import align_face
from backend.services import face_recognition as fr_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/employee", tags=["Employee"])


@router.post("/register", summary="Register a new employee with face capture")
async def register_employee(
    name: str = Form(..., description="Employee full name"),
    employee_id: str = Form(..., description="Unique employee ID e.g. EMP001"),
    face_image: UploadFile = File(..., description="Employee face image"),
):
    # ── 1. Validate employee_id uniqueness ──────────────────────────────────
    if employees_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected.")

    existing = employees_collection.find_one({"employee_id": employee_id})
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Employee ID '{employee_id}' is already registered.",
        )

    # ── 2. Validate and decode image ─────────────────────────────────────────
    contents = await face_image.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    image = decode_image(contents)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image. Please upload a valid JPEG/PNG.")

    # ── 3. Detect face ───────────────────────────────────────────────────────
    detections = detect_faces(image)
    if not detections:
        raise HTTPException(
            status_code=422,
            detail="No face detected in the uploaded image. Please try again with a clearer photo.",
        )

    # Use the highest-confidence detection
    best = max(detections, key=lambda d: d["confidence"])
    if best["confidence"] < 0.5:
        raise HTTPException(
            status_code=422,
            detail=f"Face detection confidence too low ({best['confidence']:.2f}). Please use a clearer image.",
        )

    # ── 4. Align face ────────────────────────────────────────────────────────
    aligned_face = align_face(image, best["box"])
    if aligned_face is None:
        raise HTTPException(status_code=422, detail="Face alignment failed. Please try again.")

    # ── 5. Generate embedding ────────────────────────────────────────────────
    embedding = fr_service.get_face_embedding(aligned_face)
    if embedding is None:
        raise HTTPException(status_code=500, detail="Failed to generate face embedding.")

    # ── 6. Save to MongoDB ───────────────────────────────────────────────────
    doc = {
        "employee_id": employee_id,
        "name": name.strip(),
        "face_embedding": embedding.tolist(),
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }

    try:
        result = employees_collection.insert_one(doc)
        logger.info(f"[Register] Employee '{employee_id}' registered. Doc ID: {result.inserted_id}")
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Employee ID '{employee_id}' already exists.")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "message": f"Employee '{name}' registered successfully.",
            "employee_id": employee_id,
            "name": name.strip(),
            "created_at": doc["created_at"],
        },
    )


@router.get("/", summary="List all registered employees")
async def list_employees():
    if employees_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected.")

    employees = list(
        employees_collection.find(
            {},
            {"_id": 0, "face_embedding": 0},  # Never expose embeddings
        )
    )
    return {"total": len(employees), "employees": employees}


@router.get("/{employee_id}", summary="Get a single employee's details")
async def get_employee(employee_id: str):
    if employees_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected.")

    emp = employees_collection.find_one(
        {"employee_id": employee_id},
        {"_id": 0, "face_embedding": 0},
    )
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")
    return emp
