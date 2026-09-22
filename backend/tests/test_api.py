import io
import numpy as np
import cv2
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app


def _make_test_image_bytes(name: str = "test.jpg") -> bytes:
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    img[50:150, 50:150] = [200, 100, 50]
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_image_bytes():
    return _make_test_image_bytes()


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_shape(self, client):
        data = client.get("/api/health").json()
        assert "status" in data
        assert "embeddings_loaded" in data
        assert "threshold" in data
        assert "ai_provider" in data
        assert data["status"] == "ok"


class TestRecognizeImageEndpoint:
    @patch("app.routes.recognize.recognize_faces")
    @patch("app.routes.recognize.describe_people", return_value={})
    def test_recognize_image_returns_200(self, mock_desc, mock_rec, client, sample_image_bytes):
        mock_rec.return_value = []
        resp = client.post(
            "/api/recognize",
            files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200

    @patch("app.routes.recognize.recognize_faces")
    @patch("app.routes.recognize.describe_people", return_value={})
    def test_recognize_image_shape(self, mock_desc, mock_rec, client, sample_image_bytes):
        mock_rec.return_value = []
        data = client.post(
            "/api/recognize",
            files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
        ).json()
        assert data["type"] == "image"
        assert "people" in data
        assert "sentence" in data
        assert "filename" in data

    def test_rejects_unsupported_type(self, client):
        resp = client.post(
            "/api/recognize",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400

    @patch("app.routes.recognize.recognize_faces")
    @patch("app.routes.recognize.describe_people", return_value={})
    def test_recognize_with_known_face(self, mock_desc, mock_rec, client, sample_image_bytes):
        from app.services.recognition import RecognizedFace
        mock_rec.return_value = [
            RecognizedFace(name="Alice", score=0.9, box=[10, 10, 50, 50])
        ]
        data = client.post(
            "/api/recognize",
            files={"file": ("test.jpg", sample_image_bytes, "image/jpeg")},
        ).json()
        assert len(data["people"]) == 1
        assert data["people"][0]["name"] == "Alice"
        assert "Alice" in data["sentence"]


class TestRecognizeFrameEndpoint:
    @patch("app.routes.recognize.recognize_faces")
    @patch("app.routes.recognize.describe_people", return_value={})
    def test_frame_returns_type_frame(self, mock_desc, mock_rec, client, sample_image_bytes):
        mock_rec.return_value = []
        resp = client.post(
            "/api/recognize/frame",
            files={"file": ("frame.jpg", sample_image_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "frame"
        assert "people" in data
        assert "sentence" in data

    def test_frame_rejects_non_image(self, client):
        resp = client.post(
            "/api/recognize/frame",
            files={"file": ("video.mp4", b"not-a-video", "video/mp4")},
        )
        assert resp.status_code == 400
