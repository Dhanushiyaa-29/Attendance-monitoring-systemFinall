"""
Attendance Pydantic Models.
"""
from pydantic import BaseModel
from typing import Optional


class ApprovalAction(BaseModel):
    action: str  # 'approve' or 'reject'
    manager_id: Optional[str] = "ADMIN"
    reason: Optional[str] = None


class AttendanceRecord(BaseModel):
    employee_id: str
    name: str
    date: str
    time: str
    status: str
    approval_status: str
    confidence: float
    late: bool
