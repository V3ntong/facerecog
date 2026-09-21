import numpy as np
import logging
from typing import Optional
from app.services.face_service import (
    detect_and_embed,
    embedding_to_bytes,
    bytes_to_embedding,
    cosine_similarity,
)
from app.database import ensure_person, SessionLocal
from app.config import settings
from sqlalchemy import text
import os
from pathlib import Path
from PIL import Image
import cv2
import io

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 512

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}


def load_dataset_images(dataset_dir: str) -> dict[str, list[str]]:
    """Scan dataset dir for person subfolders and image files."""
    dataset_path = Path(dataset_dir)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    persons = {}
    for entry in sorted(dataset_path.iterdir()):
        if entry.is_dir():
            images = [
                str(f)
                for f in entry.iterdir()
                if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
            ]
            if images:
                persons[entry.name] = sorted(images)
    return persons


def read_image_rgb(path: str) -> Optional[np.ndarray]:
    """Read image file and convert to RGB numpy array."""
    try:
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("Could not read image: %s", path)
            return None
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    except Exception as e:
        logger.warning("Error reading %s: %s", path, e)
        return None


def check_quality(box: list[int], image_shape: tuple, min_size: int) -> bool:
    """Check face is large enough and within image bounds."""
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    if w < min_size or h < min_size:
        return False
    img_h, img_w = image_shape[:2]
    if x1 < 0 or y1 < 0 or x2 > img_w or y2 > img_h:
        return False
    return True


def enroll_all(dataset_dir: str = None) -> dict:
    """Run enrollment on all persons in the dataset directory."""
    if dataset_dir is None:
        dataset_dir = settings.DATASET_DIR

    persons = load_dataset_images(dataset_dir)
    if not persons:
        logger.error("No person folders with images found in %s", dataset_dir)
        return {}

    db = SessionLocal()
    summary = {}
    total_used = 0
    total_skipped = 0

    for person_name, image_paths in persons.items():
        person_id = ensure_person(person_name)
        used = 0
        skipped = 0

        existing = db.execute(
            text("SELECT COUNT(*) FROM FaceEmbedding WHERE PersonId=:pid"),
            {"pid": person_id},
        ).scalar()
        if existing > 0:
            logger.info(
                "%s already has %d embeddings, skipping (idempotent)", person_name, existing
            )
            summary[person_name] = {
                "images": len(image_paths),
                "used": 0,
                "skipped": 0,
                "already_enrolled": existing,
            }
            continue

        for img_path in image_paths:
            img_rgb = read_image_rgb(img_path)
            if img_rgb is None:
                skipped += 1
                logger.info("SKIP %s/%s: could not read", person_name, os.path.basename(img_path))
                continue

            faces = detect_and_embed(img_rgb)
            if len(faces) == 0:
                skipped += 1
                logger.info("SKIP %s/%s: no face detected", person_name, os.path.basename(img_path))
                continue
            if len(faces) > 1:
                skipped += 1
                logger.info(
                    "SKIP %s/%s: %d faces (expected 1)",
                    person_name,
                    os.path.basename(img_path),
                    len(faces),
                )
                continue

            face = faces[0]
            if not check_quality(face["box"], img_rgb.shape, settings.FACE_MIN_SIZE):
                skipped += 1
                logger.info(
                    "SKIP %s/%s: face too small or out of bounds (box=%s)",
                    person_name,
                    os.path.basename(img_path),
                    face["box"],
                )
                continue

            emb_bytes = embedding_to_bytes(face["embedding"])
            db.execute(
                text(
                    "INSERT INTO FaceEmbedding (PersonId, Embedding, SourceRef, Quality) "
                    "VALUES (:pid, :emb, :src, :q)"
                ),
                {
                    "pid": person_id,
                    "emb": emb_bytes,
                    "src": os.path.basename(img_path),
                    "q": float(face["confidence"]),
                },
            )
            db.commit()
            used += 1
            logger.info(
                "ENROLLED %s/%s (confidence=%.3f)",
                person_name,
                os.path.basename(img_path),
                face["confidence"],
            )

        summary[person_name] = {"images": len(image_paths), "used": used, "skipped": skipped}
        total_used += used
        total_skipped += skipped
        logger.info(
            "%s: %d/%d images enrolled, %d skipped",
            person_name,
            used,
            len(image_paths),
            skipped,
        )

    db.close()
    summary["__total__"] = {"used": total_used, "skipped": total_skipped}
    return summary


def import_images_to_db(dataset_dir: str = None) -> dict:
    """Import all images from dataset into Person + PersonImage tables as VARBINARY."""
    if dataset_dir is None:
        dataset_dir = settings.DATASET_DIR

    persons = load_dataset_images(dataset_dir)
    db = SessionLocal()
    summary = {}

    db.execute(text("""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name='PersonImage')
        BEGIN
            CREATE TABLE PersonImage (
                Id INT IDENTITY(1,1) PRIMARY KEY,
                PersonId INT NOT NULL,
                ImageName NVARCHAR(255) NOT NULL,
                ImageData VARBINARY(MAX) NOT NULL,
                CreatedAt DATETIME2 DEFAULT GETDATE(),
                CONSTRAINT FK_PersonImage_Person FOREIGN KEY (PersonId) REFERENCES Person(Id)
            );
        END
    """))
    db.commit()

    for person_name, image_paths in persons.items():
        person_id = ensure_person(person_name)
        count = 0
        for img_path in image_paths:
            existing = db.execute(
                text("SELECT 1 FROM PersonImage WHERE PersonId=:pid AND ImageName=:name"),
                {"pid": person_id, "name": os.path.basename(img_path)},
            ).fetchone()
            if existing:
                continue
            with open(img_path, "rb") as f:
                img_bytes = f.read()
            db.execute(
                text(
                    "INSERT INTO PersonImage (PersonId, ImageName, ImageData) "
                    "VALUES (:pid, :name, :data)"
                ),
                {"pid": person_id, "name": os.path.basename(img_path), "data": img_bytes},
            )
            db.commit()
            count += 1
        summary[person_name] = count
        logger.info("Imported %d new images for %s", count, person_name)

    db.close()
    return summary
