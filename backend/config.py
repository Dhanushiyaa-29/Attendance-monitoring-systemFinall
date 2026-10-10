"""
Configuration settings for the Attendance Monitoring System.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "attendance-monitoring-system")

# Face Recognition Configuration
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.55"))  # Lower = stricter
FACE_CONFIDENCE_THRESHOLD = float(os.getenv("FACE_CONFIDENCE_THRESHOLD", "0.85"))

# Attendance Rules
WORK_START_HOUR = int(os.getenv("WORK_START_HOUR", "9"))    # 9:00 AM
WORK_START_MINUTE = int(os.getenv("WORK_START_MINUTE", "0"))
LATE_THRESHOLD_MINUTES = int(os.getenv("LATE_THRESHOLD_MINUTES", "30"))  # 30 min grace

# API Configuration
API_TITLE = "Attendance Monitoring System"
API_DESCRIPTION = "Smart Approval Based Face Attendance System"
API_VERSION = "1.0.0"
