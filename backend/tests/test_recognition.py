import numpy as np
import pytest
from unittest.mock import patch
from app.services.recognition import build_sentence, recognize_faces


class TestBuildSentence:
    def test_no_people(self):
        assert build_sentence([], []) == "No people detected."

    def test_single_name_no_action(self):
        assert build_sentence(["Alice"], [""]) == "Alice spotted."

    def test_single_name_with_action(self):
        assert build_sentence(["Alice"], ["waving"]) == "Alice spotted waving."

    def test_two_names(self):
        result = build_sentence(["Alice", "Bob"], ["", ""])
        assert result == "Alice and Bob spotted."

    def test_two_names_with_actions(self):
        result = build_sentence(["Alice", "Bob"], ["waving", "smiling"])
        assert result == "Alice and Bob spotted waving and smiling."

    def test_three_names(self):
        result = build_sentence(["Alice", "Bob", "Charlie"], ["", "", ""])
        assert result == "Alice, Bob and Charlie spotted."

    def test_unknown_only(self):
        result = build_sentence(["unknown"], [""])
        assert result == "1 unknown person."

    def test_multiple_unknowns(self):
        result = build_sentence(["unknown", "unknown"], ["", ""])
        assert result == "2 unknown persons."

    def test_mixed_known_and_unknown(self):
        result = build_sentence(["Alice", "unknown"], ["waving", ""])
        assert result == "Alice spotted waving."

    def test_duplicates_removed(self):
        result = build_sentence(["Alice", "Alice"], ["waving", "waving"])
        assert result == "Alice spotted waving."

    def test_empty_action_strings_filtered(self):
        result = build_sentence(["Alice", "Bob"], ["", ""])
        assert result == "Alice and Bob spotted."


class TestThresholdLogic:
    def test_above_threshold_recognized(self):
        rng = np.random.default_rng(1)
        emb = rng.standard_normal(512).astype(np.float32)
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch("app.services.recognition.detect_and_embed") as mock_detect, \
             patch("app.services.recognition.embeddings", np.array([emb])), \
             patch("app.services.recognition.person_names", ["Alice"]), \
             patch("app.services.recognition.person_ids", [1]):
            mock_detect.return_value = [{"box": [0, 0, 100, 100], "embedding": emb, "confidence": 0.9}]
            results = recognize_faces(dummy_img, threshold=0.3)
            assert results[0].name == "Alice"

    def test_below_threshold_unknown(self):
        rng = np.random.default_rng(2)
        emb = rng.standard_normal(512).astype(np.float32)
        diff_emb = rng.standard_normal(512).astype(np.float32)
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch("app.services.recognition.detect_and_embed") as mock_detect, \
             patch("app.services.recognition.embeddings", np.array([emb])), \
             patch("app.services.recognition.person_names", ["Alice"]), \
             patch("app.services.recognition.person_ids", [1]):
            mock_detect.return_value = [{"box": [0, 0, 100, 100], "embedding": diff_emb, "confidence": 0.9}]
            results = recognize_faces(dummy_img, threshold=0.99)
            assert results[0].name == "unknown"

    def test_no_embeddings_loads_returns_unknowns(self):
        rng = np.random.default_rng(3)
        dummy = rng.standard_normal((64, 64, 3)).astype(np.uint8)

        with patch("app.services.recognition.detect_and_embed") as mock_detect, \
             patch("app.services.recognition.embeddings", None):
            mock_detect.return_value = [{"box": [0, 0, 50, 50], "embedding": rng.standard_normal(512).astype(np.float32), "confidence": 0.8}]
            results = recognize_faces(dummy, threshold=0.5)
            assert results[0].name == "unknown"
