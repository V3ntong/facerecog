import cv2
import numpy as np
import logging
import time
from typing import Optional
from dataclasses import dataclass, field
from sqlalchemy import text
from app.database import SessionLocal
from app.services.face_service import (
    detect_and_embed,
    bytes_to_embedding,
    cosine_similarity,
)
from app.config import settings

logger = logging.getLogger(__name__)

embeddings: np.ndarray = None
person_ids: list[int] = []
person_names: list[str] = []
embedding_sources: list[str] = []


def load_embeddings():
    global embeddings, person_ids, person_names, embedding_sources
    db = SessionLocal()
    rows = db.execute(
        text(
            "SELECT fe.Id, fe.PersonId, fe.Embedding, fe.SourceRef, p.Name "
            "FROM FaceEmbedding fe "
            "JOIN Person p ON fe.PersonId = p.Id"
        )
    ).fetchall()
    db.close()

    if not rows:
        logger.warning("No embeddings found in database. Run enrollment first.")
        embeddings = np.empty((0, 512), dtype=np.float32)
        person_ids = []
        person_names = []
        embedding_sources = []
        return

    embs = []
    pids = []
    pnames = []
    srcs = []
    for row in rows:
        emb = bytes_to_embedding(row[2])
        embs.append(emb)
        pids.append(row[1])
        pnames.append(row[4])
        srcs.append(row[3] or "")

    embeddings = np.array(embs, dtype=np.float32)
    person_ids = pids
    person_names = pnames
    embedding_sources = srcs
    logger.info("Loaded %d embeddings for %d persons", len(embs), len(set(pnames)))


def refresh_embeddings():
    load_embeddings()


@dataclass
class RecognizedFace:
    name: str
    score: float
    box: list[int]
    doing: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": round(self.score, 4),
            "box": self.box,
            "doing": self.doing,
        }


def recognize_faces(image_rgb: np.ndarray, threshold: float = None) -> list[RecognizedFace]:
    """Detect and recognize all faces in an image."""
    if threshold is None:
        threshold = settings.RECOGNITION_THRESHOLD

    if embeddings is None or len(embeddings) == 0:
        logger.warning("No embeddings loaded")
        faces = detect_and_embed(image_rgb)
        return [
            RecognizedFace(name="unknown", score=0.0, box=f["box"])
            for f in faces
        ]

    detected = detect_and_embed(image_rgb)
    results = []

    for face in detected:
        emb = face["embedding"]
        scores = {}
        for pname in set(person_names):
            indices = [i for i, n in enumerate(person_names) if n == pname]
            person_embs = embeddings[indices]
            sims = [cosine_similarity(emb, pe) for pe in person_embs]
            sims.sort(reverse=True)
            top_k = min(3, len(sims))
            mean_score = np.mean(sims[:top_k]) if top_k > 0 else 0.0
            scores[pname] = float(mean_score)

        best_name = max(scores, key=scores.get)
        best_score = scores[best_name]

        if best_score >= threshold:
            results.append(
                RecognizedFace(name=best_name, score=best_score, box=face["box"])
            )
        else:
            results.append(
                RecognizedFace(name="unknown", score=best_score, box=face["box"])
            )

    return results


def calibrate_threshold(
    dataset_dir: str = None, threshold_range=None
) -> tuple[float, dict]:
    """Leave-one-out calibration: for each embedding, check if the correct
    person gets the highest mean-cosine score above threshold."""
    if threshold_range is None:
        threshold_range = np.arange(0.20, 0.80, 0.01)

    if embeddings is None or len(embeddings) == 0:
        load_embeddings()
    if embeddings is None or len(embeddings) == 0:
        return settings.RECOGNITION_THRESHOLD, {"error": "No embeddings loaded"}

    n = len(embeddings)
    if n == 0:
        return settings.RECOGNITION_THRESHOLD, {"error": "No embeddings"}

    best_threshold = settings.RECOGNITION_THRESHOLD
    best_accuracy = 0.0
    results_per_threshold = {}

    for t in threshold_range:
        correct = 0
        total = 0
        false_positives = 0
        unknown_count = 0

        for i in range(n):
            test_emb = embeddings[i]
            test_name = person_names[i]

            remaining_mask = np.arange(n) != i
            remaining_embs = embeddings[remaining_mask]
            remaining_names = [person_names[j] for j in range(n) if j != i]

            if len(remaining_embs) == 0:
                continue

            sims = np.array([cosine_similarity(test_emb, re) for re in remaining_embs])

            person_scores = {}
            for pname in set(remaining_names):
                indices = [j for j, n2 in enumerate(remaining_names) if n2 == pname]
                person_mean = float(np.mean(np.sort(sims[indices])[::-1][:3]))
                person_scores[pname] = person_mean

            total += 1
            if not person_scores:
                unknown_count += 1
                continue

            best_pred = max(person_scores, key=person_scores.get)
            best_pred_score = person_scores[best_pred]

            if best_pred_score >= t:
                if best_pred == test_name:
                    correct += 1
                else:
                    false_positives += 1
            else:
                unknown_count += 1

        accuracy = correct / total if total > 0 else 0.0
        results_per_threshold[round(float(t), 2)] = {
            "accuracy": round(accuracy, 4),
            "correct": correct,
            "total": total,
            "false_positives": false_positives,
            "unknowns": unknown_count,
        }

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = round(float(t), 2)

    report = {
        "best_threshold": best_threshold,
        "best_accuracy": round(best_accuracy, 4),
        "total_embeddings": n,
        "thresholds": results_per_threshold,
    }

    logger.info(
        "Calibration: best threshold=%.2f accuracy=%.2f%%",
        best_threshold,
        best_accuracy * 100,
    )
    return best_threshold, report


@dataclass
class VideoTrack:
    track_id: int
    name: str = "unknown"
    boxes: list = field(default_factory=list)
    scores: list = field(default_factory=list)
    first_seen: float = 0.0
    last_seen: float = 0.0
    name_votes: dict = field(default_factory=dict)

    def vote(self, name: str, score: float):
        self.name_votes[name] = self.name_votes.get(name, 0) + 1
        self.scores.append(score)
        if len(self.boxes) > 30:
            self.boxes = self.boxes[-30:]
            self.scores = self.scores[-30:]

    def final_name(self) -> str:
        if not self.name_votes:
            return "unknown"
        return max(self.name_votes, key=self.name_votes.get)


def recognize_video_frames(
    frames: list[tuple[np.ndarray, float]],
    threshold: float = None,
) -> list[dict]:
    """Recognize faces across video frames with simple tracking."""
    if threshold is None:
        threshold = settings.RECOGNITION_THRESHOLD

    tracks: list[VideoTrack] = []
    next_track_id = 0

    for frame_rgb, timestamp in frames:
        detected_faces = recognize_faces(frame_rgb, threshold)

        for face in detected_faces:
            cx = (face.box[0] + face.box[2]) / 2
            cy = (face.box[1] + face.box[3]) / 2

            matched_track = None
            for track in tracks:
                if not track.boxes:
                    continue
                last_box = track.boxes[-1]
                lcx = (last_box[0] + last_box[2]) / 2
                lcy = (last_box[1] + last_box[3]) / 2
                dist = ((cx - lcx) ** 2 + (cy - lcy) ** 2) ** 0.5
                if dist < 150:
                    matched_track = track
                    break

            if matched_track is None:
                matched_track = VideoTrack(track_id=next_track_id, first_seen=timestamp)
                tracks.append(matched_track)
                next_track_id += 1

            matched_track.boxes.append(face.box)
            matched_track.vote(face.name, face.score)
            matched_track.last_seen = timestamp

    timeline = []
    for track in tracks:
        final_name = track.final_name()
        timeline.append({
            "person": final_name,
            "first_seen": round(track.first_seen, 2),
            "last_seen": round(track.last_seen, 2),
            "confidence": round(
                float(np.mean(track.scores)) if track.scores else 0.0, 4
            ),
        })

    timeline.sort(key=lambda x: x["first_seen"])
    return timeline


def sample_segment_frames(
    frames: list[tuple[np.ndarray, float]],
    first_seen: float,
    last_seen: float,
    budget: int,
) -> list[tuple[np.ndarray, float]]:
    """Evenly sample up to `budget` frames within a person's [first_seen, last_seen]
    segment. Frames are kept in chronological order. Used to bound the number of
    images sent to the vision LLM per timeline entry (controls token cost)."""
    window = [(f, t) for f, t in frames if first_seen <= t <= last_seen]
    if not window:
        return []
    if len(window) <= budget:
        return window
    idx = np.linspace(0, len(window) - 1, budget, dtype=int)
    return [window[i] for i in idx]


def encode_frame_jpeg(frame_rgb: np.ndarray, max_dim: int = 512) -> bytes:
    """Downscale a frame to at most `max_dim` px on the longest side and JPEG-encode
    it (quality 85). Caps Gemini image tokens while keeping enough detail to
    describe activity."""
    h, w = frame_rgb.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    if scale < 1.0:
        frame_rgb = cv2.resize(frame_rgb, (int(w * scale), int(h * scale)))
    ok, buf = cv2.imencode(
        ".jpg",
        cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR),
        [cv2.IMWRITE_JPEG_QUALITY, 85],
    )
    return buf.tobytes()


def build_sentence(names: list[str], doing_parts: list[str]) -> str:
    """Build the final output sentence from recognized names and actions."""
    unique_names = list(dict.fromkeys(n for n in names if n != "unknown"))
    doing_texts = [d for d in doing_parts if d]

    if not unique_names:
        unknown_count = sum(1 for n in names if n == "unknown")
        if unknown_count:
            return f"{unknown_count} unknown person{'s' if unknown_count > 1 else ''}."
        return "No people detected."

    if len(unique_names) == 1:
        name_str = unique_names[0]
    else:
        name_str = ", ".join(unique_names[:-1]) + " and " + unique_names[-1]

    doing_str = ""
    if doing_texts:
        combined = list(dict.fromkeys(doing_texts))
        short = [d for d in combined if len(d.split()) <= 4]
        long_asides = [d for d in combined if len(d.split()) > 4]

        body = " and ".join(short)
        if long_asides:
            body = (body + " " if body else "") + " ".join(long_asides)

        if body:
            doing_str = f"{name_str} spotted. {body}".rstrip()
            if not doing_str.endswith("."):
                doing_str += "."
            return doing_str

    return f"{name_str} spotted."


def build_summary(
    recognized_names: list[str],
    enrolled_names: list[str],
    medium: str = "photo",
) -> Optional[str]:
    """Group summary shown to the user when 2+ distinct enrolled people are
    recognized. Returns None for 0/1 recognized people or an empty roster.

    enrolled_names is the raw per-embedding name list loaded in memory
    (duplicates possible); the unique count is what "N of M" refers to.
    """
    enrolled = set(enrolled_names)
    if not enrolled:
        return None

    recognized = list(
        dict.fromkeys(n for n in recognized_names if n in enrolled)
    )
    total = len(enrolled)

    if len(recognized) < 2:
        return None
    if len(recognized) == total:
        return f"All {total} enrolled people are in this {medium}."

    return (
        f"{len(recognized)} of {total} enrolled people are in this "
        f"{medium}: {', '.join(recognized)}."
    )
