import io
import os
import time
import logging
import tempfile
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.config import settings
from app.services.recognition import (
    recognize_faces,
    recognize_video_frames,
    build_sentence,
    refresh_embeddings,
    embeddings,
)
from app.services.description import describe_people

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["recognize"])

# Simple in-memory rate limiter
_rate_limits: dict[str, list[float]] = {}


def _check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    window = 60.0
    if client_ip not in _rate_limits:
        _rate_limits[client_ip] = []
    _rate_limits[client_ip] = [
        t for t in _rate_limits[client_ip] if now - t < window
    ]
    if len(_rate_limits[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
        return False
    _rate_limits[client_ip].append(now)
    return True


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}


@router.get("/health")
async def health():
    emb_count = len(embeddings) if embeddings is not None else 0
    return {
        "status": "ok",
        "embeddings_loaded": emb_count,
        "threshold": settings.RECOGNITION_THRESHOLD,
        "ai_provider": settings.AI_PROVIDER,
    }


@router.post("/recognize")
async def recognize(file: UploadFile = File(...), request: Request = None):
    client_ip = request.client.host if request else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    if file.content_type not in ALLOWED_IMAGE_TYPES and file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
            f"Accepted: images ({', '.join(ALLOWED_IMAGE_TYPES)}), "
            f"videos ({', '.join(ALLOWED_VIDEO_TYPES)})",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    is_video = file.content_type in ALLOWED_VIDEO_TYPES

    if is_video:
        return await _process_video(contents, file.filename)
    else:
        return await _process_image(contents, file.filename)


async def _process_image(
    image_bytes: bytes, filename: str = ""
) -> dict:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = recognize_faces(img_rgb)
    names = [f.name for f in faces]
    boxes = [f.box for f in faces]

    descriptions = {}
    recognized_names = [n for n in names if n != "unknown"]
    if recognized_names:
        try:
            descriptions = await describe_people(
                [image_bytes], recognized_names,
                [b for b, n in zip(boxes, names) if n != "unknown"],
            )
        except Exception as e:
            logger.warning("Description failed: %s", e)

    people = []
    doing_parts = []
    for face in faces:
        doing = descriptions.get(face.name, "") if face.name != "unknown" else ""
        face.doing = doing
        people.append(face.to_dict())
        if doing and face.name != "unknown":
            doing_parts.append(doing)

    recognized = [f.name for f in faces if f.name != "unknown"]
    sentence = build_sentence(
        [f.name for f in faces], doing_parts
    )

    return {
        "type": "image",
        "people": people,
        "sentence": sentence,
        "filename": filename,
    }


async def _process_video(
    video_bytes: bytes, filename: str = ""
) -> dict:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".mp4", delete=False
        ) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = total_frames / fps if fps > 0 else 0
        max_duration = 60.0
        if duration > max_duration:
            logger.warning("Video %.1fs exceeds %ds, will sample first %ds", duration, max_duration, max_duration)

        sample_interval = max(1, int(fps / 2))  # ~2 fps
        frames = []
        frame_idx = 0
        max_frames = int(max_duration * 2)  # 2 fps * 60s = 120 frames max

        while len(frames) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_interval == 0:
                timestamp = frame_idx / fps
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append((frame_rgb, timestamp))
            frame_idx += 1

        cap.release()

        if not frames:
            raise HTTPException(status_code=400, detail="No frames extracted from video")

        timeline = recognize_video_frames(frames)
        all_names = [t["person"] for t in timeline if t["person"] != "unknown"]
        doing_parts = [t.get("doing", "") for t in timeline if t.get("doing")]

        sentence = build_sentence(all_names, doing_parts)

        return {
            "type": "video",
            "people": [{"name": t["person"], "score": t["confidence"]} for t in timeline],
            "sentence": sentence,
            "timeline": timeline,
            "filename": filename,
        }

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/recognize/frame")
async def recognize_frame(
    file: UploadFile = File(...),
    describe: bool = False,
    request: Request = None,
):
    client_ip = request.client.host if request else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Frame must be an image.")

    contents = await file.read()
    max_bytes = 2 * 1024 * 1024  # 2MB for frames
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail="Frame too large (max 2MB).")

    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode frame")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = recognize_faces(img_rgb)
    names = [f.name for f in faces]
    boxes = [f.box for f in faces]

    descriptions = {}
    recognized_names = [n for n in names if n != "unknown"]
    if describe and recognized_names:
        try:
            descriptions = await describe_people(
                [contents], recognized_names,
                [b for b, n in zip(boxes, names) if n != "unknown"],
            )
        except Exception as e:
            logger.warning("Description failed: %s", e)

    people = []
    doing_parts = []
    for face in faces:
        doing = descriptions.get(face.name, "") if face.name != "unknown" else ""
        face.doing = doing
        people.append(face.to_dict())
        if doing and face.name != "unknown":
            doing_parts.append(doing)

    sentence = build_sentence(names, doing_parts)

    return {
        "type": "frame",
        "people": people,
        "sentence": sentence,
    }
