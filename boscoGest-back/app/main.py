from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.v1 import routers
from app.services.notification_manager import notification_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await notification_manager.start()
    yield


app = FastAPI(
    title="BoscoGest",
    description="TFG URJC Carlos Sevilla Lozano",
    version="2.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "API alive"}

# Register routers
for router in routers:
    app.include_router(router)

# Mount static files only for local storage (development)
if os.getenv("STORAGE_BACKEND", "s3") == "local":
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    os.makedirs(f"{UPLOAD_DIR}/activities", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
