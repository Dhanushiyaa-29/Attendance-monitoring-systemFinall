"""
Main FastAPI Application Entry Point.
Attendance Monitoring System — Smart Approval Based Face Attendance.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.config import API_TITLE, API_DESCRIPTION, API_VERSION
from backend.routes import employee as employee_router
from backend.routes import attendance as attendance_router

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — allow frontend served on same host ─────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(employee_router.router)
app.include_router(attendance_router.router)

# ── Serve frontend static files ───────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{page}.html", include_in_schema=False)
    async def serve_page(page: str):
        path = os.path.join(FRONTEND_DIR, f"{page}.html")
        if os.path.isfile(path):
            return FileResponse(path)
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Page not found")

# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    from backend.database import client
    db_connected = False
    if client:
        try:
            client.admin.command("ping")
            db_connected = True
        except Exception:
            pass
    return {
        "status": "running",
        "api": API_TITLE,
        "version": API_VERSION,
        "database_connected": db_connected,
    }


@app.get("/api", tags=["System"])
async def api_info():
    return {
        "message": f"{API_TITLE} API Running",
        "version": API_VERSION,
        "docs": "/docs",
        "endpoints": {
            "register_employee": "POST /employee/register",
            "list_employees": "GET /employee/",
            "verify_attendance": "POST /attendance/verify",
            "get_attendance": "GET /attendance/{employee_id}",
            "all_attendance": "GET /attendance/",
            "get_result": "GET /attendance/result/{attendance_id}",
            "approve_reject": "POST /attendance/approval/{attendance_id}",
        },
    }
