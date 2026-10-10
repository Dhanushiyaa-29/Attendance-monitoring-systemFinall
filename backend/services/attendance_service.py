"""
Attendance Service — Smart Approval Logic.
Handles duplicate checks, time-based rules, and auto/manual approval decisions.
"""
from datetime import datetime, time as dtime
import logging
from typing import Optional

from backend.config import (
    WORK_START_HOUR,
    WORK_START_MINUTE,
    LATE_THRESHOLD_MINUTES,
    FACE_MATCH_THRESHOLD,
)

logger = logging.getLogger(__name__)

# Work start time as a time object
_WORK_START = dtime(WORK_START_HOUR, WORK_START_MINUTE)
_LATE_DELTA_MINUTES = LATE_THRESHOLD_MINUTES


def is_late(attendance_time: dtime) -> bool:
    """Return True if the given time is past the late-arrival threshold."""
    start_minutes = _WORK_START.hour * 60 + _WORK_START.minute
    arrival_minutes = attendance_time.hour * 60 + attendance_time.minute
    return (arrival_minutes - start_minutes) > _LATE_DELTA_MINUTES


def determine_approval_status(confidence: float, late: bool) -> str:
    """
    Smart approval decision:

    - High confidence + on time  → Approved automatically
    - High confidence + late     → Pending (manager review)
    - Low confidence             → Rejected
    """
    if confidence >= 0.80 and not late:
        return "Approved"
    elif confidence >= 0.65:
        return "Pending"
    else:
        return "Rejected"


def build_attendance_doc(
    employee_id: str,
    name: str,
    confidence: float,
    now: Optional[datetime] = None,
) -> dict:
    """
    Build the attendance MongoDB document.
    Applies time rules and smart approval.
    """
    if now is None:
        now = datetime.now()

    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    current_time = now.time()

    late = is_late(current_time)
    approval_status = determine_approval_status(confidence, late)

    return {
        "employee_id": employee_id,
        "name": name,
        "date": date_str,
        "time": time_str,
        "status": "Present",
        "approval_status": approval_status,
        "confidence": round(confidence, 4),
        "late": late,
    }


def build_approval_doc(attendance_id: str, employee_id: str) -> dict:
    """Build the approval_requests MongoDB document linked to an attendance record."""
    return {
        "attendance_id": str(attendance_id),
        "employee_id": employee_id,
        "status": "Pending",
        "approved_by": None,
        "reason": None,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
