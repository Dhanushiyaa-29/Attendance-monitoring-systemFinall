"""
Local MongoDB connection and collection references.
"""
from pymongo import MongoClient, ASCENDING
from backend.config import MONGODB_URI, DATABASE_NAME

client = None
db     = None

# Keep the server importable when MongoDB is unavailable; routes can report
# that the database is not connected.
try:
    client = MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
    )
    # Light connectivity check — will raise if URI is invalid or unreachable
    client.admin.command("ping")
    db = client[DATABASE_NAME]
    print(f"[DB] Connected to MongoDB — database: {DATABASE_NAME}")
except Exception as e:
    print(
        f"[DB] WARNING: Could not connect to real MongoDB on 27017: {type(e).__name__}: {e}\n"
        "     Falling back to in-memory mongomock database."
    )
    try:
        import mongomock
        client = mongomock.MongoClient()
        db = client[DATABASE_NAME]
        print(f"[DB] Connected to in-memory mongomock database: {DATABASE_NAME}")
    except Exception as mock_err:
        print(f"[DB] mongomock error: {mock_err}")
        client = None
        db     = None

# Collections (None when not connected — routes will return 503)
employees_collection = db["employees"]       if db is not None else None
attendance_collection = db["attendance"]      if db is not None else None
approval_collection   = db["approval_requests"] if db is not None else None

# Create indexes only when connected
if db is not None:
    try:
        employees_collection.create_index(
            [("employee_id", ASCENDING)], unique=True, name="employee_id_unique"
        )
        attendance_collection.create_index(
            [("employee_id", ASCENDING), ("date", ASCENDING)],
            unique=True,
            name="attendance_unique_per_day",
        )
        approval_collection.create_index(
            [("attendance_id", ASCENDING)], name="approval_attendance_id"
        )
        print("[DB] Indexes ensured.")
    except Exception as idx_err:
        print(f"[DB] Index note: {idx_err}")
