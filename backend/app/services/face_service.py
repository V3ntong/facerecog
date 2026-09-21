import numpy as np
import logging
import struct
from typing import Optional

logger = logging.getLogger(__name__)

_face_analyzer = None


def get_face_analyzer():
    global _face_analyzer
    if _face_analyzer is not None:
        return _face_analyzer

    try:
        from insightface.app import FaceAnalysis
        logger.info("Using InsightFace buffalo_l")
        app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
            allowed_modules=["detection", "recognition"],
        )
        app.prepare(ctx_id=0, det_size=(640, 640))
        _face_analyzer = ("insightface", app)
        return _face_analyzer
    except ImportError:
        logger.warning("insightface not available, falling back to DeepFace")
    except Exception as e:
        logger.warning("insightface init failed: %s, falling back to DeepFace", e)

    try:
        from deepface import DeepFace
        logger.info("Using DeepFace (RetinaFace + ArcFace)")
        _face_analyzer = ("deepface", DeepFace)
        return _face_analyzer
    except ImportError:
        raise RuntimeError(
            "Neither insightface nor deepface is installed. "
            "Install one: pip install insightface onnxruntime  OR  pip install deepface"
        )


def detect_and_embed(image_rgb: np.ndarray) -> list[dict]:
    """Detect faces and extract 512-d embeddings.
    Returns list of {"box": [x1,y1,x2,y2], "embedding": np.ndarray, "confidence": float}
    """
    backend, analyzer = get_face_analyzer()

    if backend == "insightface":
        faces = analyzer.get(image_rgb)
        results = []
        for face in faces:
            bbox = face.bbox.astype(int).tolist()
            results.append({
                "box": bbox,
                "embedding": face.normed_embedding,
                "confidence": float(face.det_score),
            })
        return results

    elif backend == "deepface":
        try:
            dfs = analyzer.represent(
                img_path=image_rgb,
                model_name="ArcFace",
                detector_backend="retinaface",
                enforce_detection=False,
                normalization="base",
            )
        except Exception:
            return []

        results = []
        for df in dfs:
            emb = np.array(df["embedding"], dtype=np.float32)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            region = df.get("facial_area", {})
            x = region.get("x", 0)
            y = region.get("y", 0)
            w = region.get("w", 0)
            h = region.get("h", 0)
            confidence = df.get("face_confidence", 0.0)
            results.append({
                "box": [x, y, x + w, y + h],
                "embedding": emb,
                "confidence": float(confidence),
            })
        return results

    return []


def embedding_to_bytes(emb: np.ndarray) -> bytes:
    return emb.astype(np.float32).tobytes()


def bytes_to_embedding(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))
