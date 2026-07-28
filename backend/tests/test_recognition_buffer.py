import unittest

from backend.ai.recognition_buffer import TrackRecognitionBuffer
from backend.app.models import DetectionStatus


class TrackRecognitionBufferTestCase(unittest.TestCase):
    def test_buffers_are_isolated_by_track_id(self):
        buffer = TrackRecognitionBuffer(size=3, match_threshold=0.35)

        known = buffer.add(1, 10, 0.80)
        unknown = buffer.add(2, 20, 0.10)

        self.assertEqual(known.status, DetectionStatus.KNOWN)
        self.assertEqual(known.member_id, 10)
        self.assertEqual(unknown.status, DetectionStatus.UNKNOWN)
        self.assertIsNone(unknown.member_id)

    def test_majority_identity_wins_and_uses_its_own_average(self):
        buffer = TrackRecognitionBuffer(size=4, match_threshold=0.35)
        buffer.add(1, 10, 0.70)
        buffer.add(1, 20, 0.90)
        buffer.add(1, 10, 0.50)
        decision = buffer.add(1, 10, 0.60)

        self.assertEqual(decision.status, DetectionStatus.KNOWN)
        self.assertEqual(decision.member_id, 10)
        self.assertAlmostEqual(decision.similarity, 0.60)

    def test_buffer_keeps_only_most_recent_samples(self):
        buffer = TrackRecognitionBuffer(size=2, match_threshold=0.35)
        buffer.add(1, 10, 0.90)
        buffer.add(1, 10, 0.80)
        buffer.add(1, 20, 0.70)
        decision = buffer.add(1, 20, 0.60)

        self.assertEqual(decision.member_id, 20)
        self.assertAlmostEqual(decision.similarity, 0.65)

    def test_clear_and_reset_remove_history(self):
        buffer = TrackRecognitionBuffer(size=3, match_threshold=0.35)
        buffer.add(1, 10, 0.80)
        buffer.add(2, 20, 0.70)

        buffer.clear_track(1)
        self.assertEqual(
            buffer.decision(1).status,
            DetectionStatus.LOW_QUALITY,
        )
        self.assertEqual(buffer.decision(2).status, DetectionStatus.KNOWN)

        buffer.reset()
        self.assertEqual(
            buffer.decision(2).status,
            DetectionStatus.LOW_QUALITY,
        )

    def test_invalid_size_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be positive"):
            TrackRecognitionBuffer(size=0, match_threshold=0.35)


if __name__ == "__main__":
    unittest.main()
