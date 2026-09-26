import logging
import re
import uuid
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
from sqlalchemy import text
from app.config import settings
from app.database import SessionLocal, ensure_person
from app.services.face_service import detect_and_embed, embedding_to_bytes
from app.services.enrollment import check_quality
from app.services import recognition as recognition_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/enroll", tags=["enroll"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/webp"}
MAX_NAME_LEN = 100

# Letters, digits, spaces, dots, apostrophes and hyphens.
NAME_RE = re.compile(r"^[A-Za-z0-9 .'-]+$")


def normalize_name(raw: str) -> str | None:
    """Trim/collapse whitespace and validate. Returns None for bad input."""
    name = " ".join((raw or "").split())
    if not name or len(name) > MAX_NAME_LEN or not NAME_RE.match(name):
        return None
    return name


def decode_image(image_bytes: bytes) -> np.ndarray:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


async def _read_checked_image(file: UploadFile) -> tuple[str, bytes]:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Accepted: image/jpeg, image/png, image/bmp, image/webp.",
        )
    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )
    return file.content_type, contents


def _person_id_case_insensitive(db, name: str):
    return db.execute(
        text("SELECT Id, Name FROM Person WHERE LOWER(Name) = LOWER(:n)"),
        {"n": name},
    ).fetchone()


@router.post("/validate")
async def validate_enroll(file: UploadFile = File(...)):
    """Pre-flight check: report how many faces a photo contains without saving."""
    _, contents = await _read_checked_image(file)
    img_rgb = decode_image(contents)
    faces = detect_and_embed(img_rgb)
    count = len(faces)

    if count == 0:
        return {
            "ok": False,
            "face_count": 0,
            "message": "No face detected. Use a photo with one clear, well-lit face.",
        }
    if count > 1:
        return {
            "ok": False,
            "face_count": count,
            "message": f"Multiple faces detected ({count}). Use a photo with exactly one person.",
        }
    return {
        "ok": True,
        "face_count": 1,
        "message": "One face detected. Ready to enroll.",
    }


@router.post("")
async def enroll(
    file: UploadFile = File(...),
    name: str = Form(...),
):
    """Enroll a photo of a person. Registers the person + embedding and refreshes
    the in-memory matching cache. Appends to an existing person when the name
    already matches (case-insensitive), otherwise creates a new one."""
    person_name = normalize_name(name)
    if person_name is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid name. Use only letters, digits, spaces, dots, "
                f"apostrophes and hyphens (max {MAX_NAME_LEN} chars)."
            ),
        )

    _, contents = await _read_checked_image(file)
    img_rgb = decode_image(contents)
    faces = detect_and_embed(img_rgb)

    if len(faces) == 0:
        raise HTTPException(
            status_code=400,
            detail="No face detected. Use a photo with one clear, well-lit face.",
        )
    if len(faces) > 1:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Multiple faces detected ({len(faces)}). "
                "Use a photo with exactly one person."
            ),
        )

    face = faces[0]
    if not check_quality(face["box"], img_rgb.shape, settings.FACE_MIN_SIZE):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Face is too small or out of bounds (box={face['box']}). "
                "Move closer to the camera and retry."
            ),
        )

    db = SessionLocal()
    try:
        existing = _person_id_case_insensitive(db, person_name)
        if existing:
            stored_name = existing[1]
            person_id = existing[0]
            is_new = False
        else:
            stored_name = person_name
            person_id = ensure_person(stored_name)
            is_new = True
        db.commit()

        folder_path = Path(settings.DATASET_DIR) / stored_name
        folder_path.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}.jpg"
        ok, buf = cv2.imencode(
            ".jpg",
            cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR),
            [cv2.IMWRITE_JPEG_QUALITY, 95],
        )
        if not ok:
            raise HTTPException(status_code=500, detail="Could not encode image")
        (folder_path / filename).write_bytes(buf.tobytes())

        db.execute(
            text(
                "INSERT INTO FaceEmbedding (PersonId, Embedding, SourceRef, Quality) "
                "VALUES (:pid, :emb, :src, :q)"
            ),
            {
                "pid": person_id,
                "emb": embedding_to_bytes(face["embedding"]),
                "src": filename,
                "q": float(face["confidence"]),
            },
        )
        db.commit()
    finally:
        db.close()

    recognition_service.refresh_embeddings()
    total = (
        len(recognition_service.embeddings)
        if recognition_service.embeddings is not None
        else 0
    )

    if is_new:
        message = f"Enrolled new person: {stored_name}."
    else:
        message = f"Added a new photo for {stored_name}."

    return {
        "ok": True,
        "person": stored_name,
        "person_id": person_id,
        "is_new": is_new,
        "embeddings_total": total,
        "message": message,
    }