import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import settings
from backend.app.core.database import check_database_connection, run_advisory_lock_migration
from backend.app.api.auth import router as auth_router
from backend.app.api.candidate import router as candidate_router
from backend.app.api.admin_device import router as admin_router
from backend.app.api.proctor import router as proctor_router
from backend.app.api.monitor import router as monitor_router
from backend.app.api.admin import router as admin_api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    # Startup: Check database connection and run safe advisory lock migration
    db_ok = check_database_connection(retries=3, backoff=1.5)
    if db_ok:
        run_advisory_lock_migration()
        # Ensure Ashtapradhan questions and roster are seeded
        try:
            from scripts.import_ashtapradhan_questions import load_ashtapradhan_questions, seed_ashtapradhan_into_db
            csv_path = os.path.join("data", "ashtapradhan_questions.csv")
            if os.path.exists(csv_path):
                ash_qs = load_ashtapradhan_questions(csv_path)
                seed_ashtapradhan_into_db(ash_qs)
        except Exception as e:
            print("[Lifespan] Ashtapradhan questions notice:", e)
        try:
            from scripts.seed_ashtapradhan_roster import seed_ashtapradhan_roster
            seed_ashtapradhan_roster()
        except Exception as e:
            print("[Lifespan] Ashtapradhan roster notice:", e)
        # Initialize Google Sheet structure & formatting safely
        try:
            from backend.app.services.sheets_service import ensure_sheet_tabs_and_headers
            ensure_sheet_tabs_and_headers()
        except Exception:
            pass

    # Background task to drain pending sheet writes every 30 seconds
    async def sheet_drain_loop():
        while True:
            try:
                from backend.app.core.database import SessionLocal
                from backend.app.services.sheets_service import process_pending_sheet_writes
                with SessionLocal() as session:
                    process_pending_sheet_writes(session)
            except Exception:
                pass
            await asyncio.sleep(30)

    drain_task = asyncio.create_task(sheet_drain_loop())
    yield
    drain_task.cancel()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Secure Online Proctored Assessment Portal",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth_router, prefix="/api")
app.include_router(candidate_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(proctor_router, prefix="/api")
app.include_router(admin_api_router, prefix="/api")
app.include_router(monitor_router)


@app.get("/healthz", tags=["System"])
def health_check():
    """Cheap, unauthenticated health check that verifies DB connectivity and wakes free-tier instances."""
    db_healthy = check_database_connection(retries=1)
    status_code = status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if db_healthy else "degraded",
            "database": "connected" if db_healthy else "disconnected",
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0"
        }
    )


# Static files mount (Serves built React frontend if dist exists)
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
