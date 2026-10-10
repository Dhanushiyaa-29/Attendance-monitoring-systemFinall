"""
Employee Pydantic Models.
"""
from pydantic import BaseModel
from typing import Optional


class EmployeeResponse(BaseModel):
    employee_id: str
    name: str
    created_at: str

    class Config:
        from_attributes = True
