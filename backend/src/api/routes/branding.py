"""
Branding API routes for background music and outro video management.
"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import re
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

from ...config import get_config
from ...database import get_db
from ...auth_headers import resolve_authenticated_user_id
from ...models import User
from ...media.branding import ffprobe_media_duration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/branding", tags=["branding"])

SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
MAX_OUTRO_DURATION_SECONDS = 5.05  # 5 seconds with small tolerance for container rounding
MAX_AUDIO_SIZE_BYTES = 50 * 1024 * 1024  # 50MB max for bgm
MAX_OUTRO_SIZE_BYTES = 100 * 1024 * 1024  # 100MB max for 5s outro


def _sanitize_user_id(user_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", user_id).strip("-")
    return safe or "user"


def get_user_assets_dir(user_id: str) -> Path:
    assets_dir = Path(get_config().temp_dir) / "assets" / _sanitize_user_id(user_id)
    assets_dir.mkdir(parents=True, exist_ok=True)
    return assets_dir


async def _get_user_settings(db: AsyncSession, user_id: str) -> Tuple[User, dict]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    settings = dict(user.create_settings or {})
    return user, settings


@router.get("")
@router.get("/")
async def get_branding_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get current user's background music and outro video settings."""
    user_id = await resolve_authenticated_user_id(request, db, get_config())
    _, settings = await _get_user_settings(db, user_id)
    return {
        "backgroundMusic": settings.get("backgroundMusic") or settings.get("background_music"),
        "outroVideo": settings.get("outroVideo") or settings.get("outro_video"),
    }


@router.post("/background-music")
async def upload_background_music(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload background music that will be mixed into all clips."""
    user_id = await resolve_authenticated_user_id(request, db, get_config())
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Allowed: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}",
        )

    assets_dir = get_user_assets_dir(user_id)
    # Remove previous bgm files for this user
    for old_file in assets_dir.glob("bgm_*"):
        try:
            old_file.unlink(missing_ok=True)
        except Exception:
            pass

    unique_name = f"bgm_{uuid.uuid4().hex[:8]}{ext}"
    target_path = assets_dir / unique_name

    # Write file to disk
    total_bytes = 0
    with open(target_path, "wb") as out_f:
        while chunk := await file.read(65536):
            total_bytes += len(chunk)
            if total_bytes > MAX_AUDIO_SIZE_BYTES:
                target_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Audio file exceeds 50MB limit")
            out_f.write(chunk)

    user, settings = await _get_user_settings(db, user_id)
    bgm_info = {
        "enabled": True,
        "path": str(target_path),
        "filename": file.filename,
        "volume": 0.15,
        "url": "/api/branding/file?type=bgm",
    }
    settings["backgroundMusic"] = bgm_info
    user.create_settings = settings
    await db.commit()

    return {"success": True, "backgroundMusic": bgm_info}


@router.delete("/background-music")
async def delete_background_music(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Remove background music."""
    user_id = await resolve_authenticated_user_id(request, db, get_config())
    user, settings = await _get_user_settings(db, user_id)

    bgm = settings.get("backgroundMusic") or settings.get("background_music")
    if bgm and isinstance(bgm, dict) and bgm.get("path"):
        try:
            Path(bgm["path"]).unlink(missing_ok=True)
        except Exception as exc:
            logger.warning(f"Failed to delete bgm file: {exc}")

    settings.pop("backgroundMusic", None)
    settings.pop("background_music", None)
    user.create_settings = settings
    await db.commit()

    return {"success": True}


@router.post("/outro-video")
async def upload_outro_video(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload an outro video (max 5 seconds) to be appended to all clips."""
    user_id = await resolve_authenticated_user_id(request, db, get_config())
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format. Allowed: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}",
        )

    assets_dir = get_user_assets_dir(user_id)
    unique_name = f"outro_{uuid.uuid4().hex[:8]}{ext}"
    target_path = assets_dir / unique_name

    # Write file to disk
    total_bytes = 0
    with open(target_path, "wb") as out_f:
        while chunk := await file.read(65536):
            total_bytes += len(chunk)
            if total_bytes > MAX_OUTRO_SIZE_BYTES:
                target_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Video file exceeds 100MB limit")
            out_f.write(chunk)

    # Check duration strictly
    duration = ffprobe_media_duration(target_path)
    if duration <= 0:
        target_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Invalid video file or could not read duration")

    if duration > MAX_OUTRO_DURATION_SECONDS:
        target_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=f"Outro video must be 5 seconds or less (uploaded video is {duration:.1f}s)",
        )

    # Remove older outro files for this user
    for old_file in assets_dir.glob("outro_*"):
        if old_file != target_path:
            try:
                old_file.unlink(missing_ok=True)
            except Exception:
                pass

    user, settings = await _get_user_settings(db, user_id)
    outro_info = {
        "enabled": True,
        "path": str(target_path),
        "filename": file.filename,
        "duration": round(duration, 2),
        "url": "/api/branding/file?type=outro",
    }
    settings["outroVideo"] = outro_info
    user.create_settings = settings
    await db.commit()

    return {"success": True, "outroVideo": outro_info}


@router.delete("/outro-video")
async def delete_outro_video(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Remove outro video."""
    user_id = await resolve_authenticated_user_id(request, db, get_config())
    user, settings = await _get_user_settings(db, user_id)

    outro = settings.get("outroVideo") or settings.get("outro_video")
    if outro and isinstance(outro, dict) and outro.get("path"):
        try:
            Path(outro["path"]).unlink(missing_ok=True)
        except Exception as exc:
            logger.warning(f"Failed to delete outro file: {exc}")

    settings.pop("outroVideo", None)
    settings.pop("outro_video", None)
    user.create_settings = settings
    await db.commit()

    return {"success": True}


@router.get("/file")
async def get_branding_file(
    request: Request,
    type: str,
    db: AsyncSession = Depends(get_db),
):
    """Stream user's background music or outro video for browser preview."""
    user_id = await resolve_authenticated_user_id(request, db, get_config())
    _, settings = await _get_user_settings(db, user_id)

    if type == "bgm":
        asset = settings.get("backgroundMusic") or settings.get("background_music")
        media_type = "audio/mpeg"
    elif type == "outro":
        asset = settings.get("outroVideo") or settings.get("outro_video")
        media_type = "video/mp4"
    else:
        raise HTTPException(status_code=400, detail="Invalid asset type (must be bgm or outro)")

    if not asset or not isinstance(asset, dict) or not asset.get("path"):
        raise HTTPException(status_code=404, detail="Asset not found")

    file_path = Path(asset["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Asset file missing on disk")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=asset.get("filename", file_path.name),
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.patch("/settings")
async def update_branding_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update enabled flags or volume for branding assets without re-uploading."""
    user_id = await resolve_authenticated_user_id(request, db, get_config())
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected a JSON object")

    user, settings = await _get_user_settings(db, user_id)

    if "backgroundMusic" in payload and isinstance(payload["backgroundMusic"], dict):
        current_bgm = settings.get("backgroundMusic") or settings.get("background_music") or {}
        if current_bgm:
            if "enabled" in payload["backgroundMusic"]:
                current_bgm["enabled"] = bool(payload["backgroundMusic"]["enabled"])
            if "volume" in payload["backgroundMusic"]:
                vol = float(payload["backgroundMusic"]["volume"])
                current_bgm["volume"] = max(0.0, min(1.0, vol))
            settings["backgroundMusic"] = current_bgm

    if "outroVideo" in payload and isinstance(payload["outroVideo"], dict):
        current_outro = settings.get("outroVideo") or settings.get("outro_video") or {}
        if current_outro:
            if "enabled" in payload["outroVideo"]:
                current_outro["enabled"] = bool(payload["outroVideo"]["enabled"])
            settings["outroVideo"] = current_outro

    user.create_settings = settings
    await db.commit()

    return {
        "success": True,
        "backgroundMusic": settings.get("backgroundMusic"),
        "outroVideo": settings.get("outroVideo"),
    }
