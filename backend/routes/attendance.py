"""
Attendance Routes — Verification, history, and smart approval.
"""
import logging
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend.config import FACE_MATCH_THRESHOLD
from backend.database import attendance_collection, approval_collection, employees_collection
from backend.models.attendance import ApprovalAction
from backend.services import face_recognition as fr_service
from backend.services.attendance_service import build_approval_doc, build_attendance_doc
from backend.services.face_detector import decode_image, detect_faces
from backend.services.face_landmark import align_face

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attendance", tags=["Attendance"])


# ── Helpers ─────────────────────────────────────────────────────────────────

def _oid(doc: dict) -> str:
    return str(doc.get("_id", ""))


def _clean(doc: dict) -> dict:
    """Remove MongoDB _id and convert ObjectId fields to strings."""
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


# ── Verify & Submit Attendance ───────────────────────────────────────────────

@router.post("/verify", summary="Verify face and submit attendance")
async def verify_attendance(
    employee_id: str = Form(..., description="Employee ID to verify"),
    face_image: UploadFile = File(..., description="Live face image for verification"),
):
    if any(c is None for c in [employees_collection, attendance_collection, approval_collection]):
        raise HTTPException(status_code=503, detail="Database not connected.")

    # ── 1. Check Employee ID exists ──────────────────────────────────────────
    employee = employees_collection.find_one({"employee_id": employee_id})
    if not employee:
        raise HTTPException(
            status_code=404,
            detail=f"Employee ID '{employee_id}' not found. Please register first.",
        )

    # ── 2. Decode submitted image ────────────────────────────────────────────
    contents = await face_image.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    image = decode_image(contents)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")

    # ── 3. Detect face ────────────────────────────────────────────────────────
    detections = detect_faces(image)
    if not detections:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "verified": False,
                "employee_id": employee_id,
                "message": "No face detected in the submitted image.",
                "attendance_recorded": False,
            },
        )

    best = max(detections, key=lambda d: d["confidence"])

    # ── 4. Align face ─────────────────────────────────────────────────────────
    aligned = align_face(image, best["box"])
    if aligned is None:
        raise HTTPException(status_code=422, detail="Face alignment failed.")

    # ── 5. Generate embedding ─────────────────────────────────────────────────
    submitted_embedding = fr_service.get_face_embedding(aligned)
    if submitted_embedding is None:
        raise HTTPException(status_code=500, detail="Failed to generate face embedding.")

    # ── 6. Compare with registered embedding ─────────────────────────────────
    stored_embedding = employee.get("face_embedding", [])
    matched, confidence = fr_service.is_match(
        submitted_embedding, stored_embedding, threshold=FACE_MATCH_THRESHOLD
    )

    if not matched:
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "verified": False,
                "employee_id": employee_id,
                "message": (
                    f"Face verification FAILED. "
                    f"The submitted face does not match the registered employee. "
                    f"Confidence: {confidence:.2%}"
                ),
                "confidence": confidence,
                "attendance_recorded": False,
            },
        )

    # ── 7. Duplicate attendance check ─────────────────────────────────────────
    today = datetime.now().strftime("%Y-%m-%d")
    duplicate = attendance_collection.find_one(
        {"employee_id": employee_id, "date": today}
    )
    if duplicate:
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "verified": True,
                "employee_id": employee_id,
                "name": employee["name"],
                "message": f"Attendance already recorded for {today}.",
                "attendance_recorded": False,
                "existing_attendance": {
                    "date": duplicate["date"],
                    "time": duplicate["time"],
                    "status": duplicate["status"],
                    "approval_status": duplicate["approval_status"],
                },
            },
        )

    # ── 8. Smart Approval & Save Attendance ───────────────────────────────────
    att_doc = build_attendance_doc(
        employee_id=employee_id,
        name=employee["name"],
        confidence=confidence,
    )

    try:
        att_result = attendance_collection.insert_one(att_doc)
        attendance_id = str(att_result.inserted_id)
    except Exception as e:
        if "duplicate key" in str(e).lower():
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "verified": True,
                    "message": "Attendance already recorded for today.",
                    "attendance_recorded": False,
                },
            )
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # ── 9. Create Approval Request (if Pending) ───────────────────────────────
    if att_doc["approval_status"] == "Pending":
        approval_doc = build_approval_doc(attendance_id, employee_id)
        approval_collection.insert_one(approval_doc)

    logger.info(
        f"[Attendance] '{employee_id}' verified. Confidence={confidence:.4f} "
        f"Late={att_doc['late']} Approval={att_doc['approval_status']}"
    )

    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "verified": True,
            "attendance_recorded": True,
            "attendance_id": attendance_id,
            "employee_id": employee_id,
            "name": employee["name"],
            "date": att_doc["date"],
            "time": att_doc["time"],
            "status": att_doc["status"],
            "approval_status": att_doc["approval_status"],
            "confidence": att_doc["confidence"],
            "late": att_doc["late"],
        },
    )


# ── Get Attendance History ────────────────────────────────────────────────────

@router.get("/{employee_id}", summary="Get attendance history for an employee")
async def get_attendance_history(employee_id: str, limit: int = 30):
    if attendance_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected.")

    records = list(
        attendance_collection.find(
            {"employee_id": employee_id}, {"_id": 0}
        ).sort("date", -1).limit(limit)
    )
    return {"employee_id": employee_id, "total": len(records), "records": records}


@router.get("/", summary="Get all attendance records")
async def get_all_attendance(date: Optional[str] = None, limit: int = 100):
    if attendance_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected.")

    query = {"date": date} if date else {}
    records = list(
        attendance_collection.find(query, {"_id": 0}).sort("date", -1).limit(limit)
    )
    return {"total": len(records), "records": records}


# ── Result by Attendance ID ───────────────────────────────────────────────────

@router.get("/result/{attendance_id}", summary="Get result for a specific attendance record")
async def get_result(attendance_id: str):
    if attendance_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected.")
    try:
        oid = ObjectId(attendance_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid attendance ID format.")

    record = attendance_collection.find_one({"_id": oid})
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found.")

    record["attendance_id"] = str(record.pop("_id"))
    return record


# ── Manager Approval ──────────────────────────────────────────────────────────

@router.post("/approval/{attendance_id}", summary="Approve or reject an attendance request")
async def process_approval(attendance_id: str, action: ApprovalAction):
    """Manager-only endpoint to approve or reject a pending attendance record."""
    if any(c is None for c in [attendance_collection, approval_collection]):
        raise HTTPException(status_code=503, detail="Database not connected.")

    if action.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")

    try:
        oid = ObjectId(attendance_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid attendance ID format.")

    # Update attendance record
    new_status = "Approved" if action.action == "approve" else "Rejected"
    att_update = attendance_collection.update_one(
        {"_id": oid},
        {"$set": {"approval_status": new_status}},
    )
    if att_update.matched_count == 0:
        raise HTTPException(status_code=404, detail="Attendance record not found.")

    # Update approval_requests document
    approval_collection.update_one(
        {"attendance_id": attendance_id},
        {
            "$set": {
                "status": new_status,
                "approved_by": action.manager_id,
                "reason": action.reason,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        },
    )

    return {
        "success": True,
        "attendance_id": attendance_id,
        "new_status": new_status,
        "approved_by": action.manager_id,
    }
