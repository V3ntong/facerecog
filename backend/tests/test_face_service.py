import numpy as np
import pytest
from app.services.face_service import cosine_similarity, embedding_to_bytes, bytes_to_embedding


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self):
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([-1.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(-1.0, abs=1e-6)

    def test_parallel_scaled_vectors(self):
        a = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        b = np.array([2.0, 4.0, 6.0], dtype=np.float32)
        assert cosine_similarity(a, b) == pytest.approx(1.0, abs=1e-6)

    def test_zero_vector_returns_zero(self):
        a = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, b) == 0.0
        assert cosine_similarity(b, a) == 0.0

    def test_512d_random_vectors(self):
        rng = np.random.default_rng(42)
        a = rng.standard_normal(512).astype(np.float32)
        b = rng.standard_normal(512).astype(np.float32)
        score = cosine_similarity(a, b)
        assert -1.0 <= score <= 1.0

    def test_symmetry(self):
        rng = np.random.default_rng(7)
        a = rng.standard_normal(512).astype(np.float32)
        b = rng.standard_normal(512).astype(np.float32)
        assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a), abs=1e-6)


class TestEmbeddingBytesRoundtrip:
    def test_roundtrip(self):
        original = np.array([0.1, -0.5, 0.99, 0.0], dtype=np.float32)
        data = embedding_to_bytes(original)
        recovered = bytes_to_embedding(data)
        np.testing.assert_array_almost_equal(original, recovered, decimal=6)

    def test_512d_roundtrip(self):
        rng = np.random.default_rng(99)
        original = rng.standard_normal(512).astype(np.float32)
        data = embedding_to_bytes(original)
        recovered = bytes_to_embedding(data)
        assert len(recovered) == 512
        np.testing.assert_array_almost_equal(original, recovered, decimal=6)
