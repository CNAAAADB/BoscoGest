from fastapi import APIRouter, Depends
from app.models.user_model import User
from app.utils.auth import get_current_active_user
from app.services.storage import get_storage_service

download_router = APIRouter(prefix="/downloads", tags=["Downloads"])

APK_S3_KEY = "apks/boscogest.apk"
APK_FILENAME = "BoscoGest.apk"


@download_router.get("/apk")
def download_apk(
    current_user: User = Depends(get_current_active_user),
):
    storage = get_storage_service()
    url = storage.get_presigned_url(
        APK_S3_KEY, expires_in=900, filename=APK_FILENAME
    )
    return {"url": url}
