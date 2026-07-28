import unittest

import numpy as np

from backend.ai.face_recognizer import (
    InMemoryFaceGallery,
    InsightFaceTrackRecognizer,
)


class InMemoryFaceGalleryTestCase(unittest.TestCase):
    def test_match_uses_cosine_similarity_across_member_embeddings(self):
        gallery = InMemoryFaceGallery()
        gallery.replace(
            {
                1: [
                    np.array([1.0, 0.0], dtype=np.float32),
                    np.array([0.9, 0.1], dtype=np.float32),
                ],
                2: [np.array([0.0, 1.0], dtype=np.float32)],
            }
        )

        member_id, similarity = gallery.match(
            np.array([0.95, 0.05], dtype=np.float32)
        )

        self.assertEqual(member_id, 1)
        self.assertGreater(similarity, 0.99)

    def test_empty_gallery_returns_unknown_candidate(self):
        gallery = InMemoryFaceGallery()

        member_id, similarity = gallery.match(
            np.array([1.0, 0.0], dtype=np.float32)
        )

        self.assertIsNone(member_id)
        self.assertEqual(similarity, -1.0)

    def test_add_and_remove_update_gallery(self):
        gallery = InMemoryFaceGallery()
        gallery.add(4, np.array([1.0, 0.0], dtype=np.float32))
        self.assertEqual(
            gallery.match(np.array([1.0, 0.0], dtype=np.float32))[0],
            4,
        )

        gallery.remove(4)

        self.assertIsNone(
            gallery.match(np.array([1.0, 0.0], dtype=np.float32))[0]
        )

    def test_zero_length_or_zero_norm_embedding_is_rejected(self):
        gallery = InMemoryFaceGallery()

        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            gallery.add(1, np.array([], dtype=np.float32))
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            gallery.add(1, np.zeros(3, dtype=np.float32))

    def test_insightface_adapter_uses_injected_lazy_manager(self):
        class FakeEmbeddingManager:
            def __init__(self):
                self.padding_ratio = None

            def extract_best_embedding_from_bgr(
                self,
                image_bgr,
                *,
                padding_ratio,
            ):
                self.padding_ratio = padding_ratio
                return np.array([1.0, 0.0], dtype=np.float32), 0.94

        gallery = InMemoryFaceGallery()
        gallery.add(8, np.array([1.0, 0.0], dtype=np.float32))
        manager = FakeEmbeddingManager()
        recognizer = InsightFaceTrackRecognizer(
            gallery,
            embedding_manager=manager,
            padding_ratio=0.4,
        )

        observation = recognizer.observe(
            np.zeros((20, 20, 3), dtype=np.uint8)
        )

        self.assertTrue(observation.face_detected)
        self.assertEqual(observation.candidate_member_id, 8)
        self.assertAlmostEqual(observation.similarity, 1.0)
        self.assertEqual(manager.padding_ratio, 0.4)


if __name__ == "__main__":
    unittest.main()
