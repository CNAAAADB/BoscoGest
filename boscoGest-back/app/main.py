from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from app import config
from app.api.v1 import routers
from app.services.notification_manager import notification_manager
from app.services.chat_manager import chat_manager
from app.services.fee_scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await notification_manager.start()
    await chat_manager.start()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="BoscoGest",
    description="TFG URJC Carlos Sevilla Lozano",
    version="2.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

# CORS configuration — explicit allow-list, validated at import time in
# app.config (no wildcard fallback alongside allow_credentials).
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "API alive"}


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Readiness probe used by the container healthcheck.

    `/` only proves the process is accepting connections. A container whose
    database connection has gone stale still answers it, so `restart: always`
    never notices. This actually touches the database.
    """
    from sqlalchemy import text

    from app.database.database import sync_engine

    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": str(exc)[:200]},
        )
    return {"status": "ok", "database": "ok"}

# Register routers
for router in routers:
    app.include_router(router)

# Mount static files only for local storage (development)
if config.STORAGE_BACKEND == "local":
    UPLOAD_DIR = config.UPLOAD_DIR
    os.makedirs(f"{UPLOAD_DIR}/activities", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
