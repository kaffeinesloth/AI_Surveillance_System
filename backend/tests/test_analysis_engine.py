import unittest

import numpy as np

from backend.ai.analysis_engine import FrameAnalysisEngine, annotate_frame
from backend.ai.contracts import (
    BoundingBox,
    FaceObservation,
    TrackedPerson,
)
from backend.ai.person_tracker import YoloByteTracker
from backend.app.models import DetectionStatus


class FakePersonTracker:
    def __init__(self, tracks):
        self.tracks = tracks
        self.reset_called = False

    def track_frame(self, frame_bgr):
        return list(self.tracks)

    def reset(self):
        self.reset_called = True


class FakeFaceRecognizer:
    def __init__(self, observations):
        self.observations = list(observations)
        self.crops = []

    def observe(self, person_crop_bgr):
        self.crops.append(person_crop_bgr.copy())
        return self.observations.pop(0)


def tracked_person(
    track_id=1,
    bounding_box=BoundingBox(10, 10, 80, 90),
    confidence=0.91,
):
    return TrackedPerson(
        track_id=track_id,
        bounding_box=bounding_box,
        confidence=confidence,
    )


class FrameAnalysisEngineTestCase(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((100, 120, 3), dtype=np.uint8)

    def test_known_person_result_uses_buffered_similarity(self):
        tracker = FakePersonTracker([tracked_person()])
        recognizer = FakeFaceRecognizer(
            [
                FaceObservation(
                    face_detected=True,
                    candidate_member_id=7,
                    similarity=0.78,
                    face_confidence=0.93,
                )
            ]
        )
        engine = FrameAnalysisEngine(
            tracker,
            recognizer,
            match_threshold=0.35,
            recognition_buffer_size=10,
        )

        result = engine.analyze_frame(
            self.frame,
            frame_index=4,
            timestamp_seconds=0.4,
        )

        self.assertEqual(result.frame_index, 4)
        self.assertEqual(result.width, 120)
        self.assertEqual(result.height, 100)
        self.assertEqual(len(result.tracks), 1)
        analysis = result.tracks[0]
        self.assertEqual(analysis.status, DetectionStatus.KNOWN)
        self.assertEqual(analysis.member_id, 7)
        self.assertAlmostEqual(analysis.similarity, 0.78)
        self.assertEqual(recognizer.crops[0].shape, (80, 70, 3))

    def test_low_similarity_is_unknown(self):
        engine = FrameAnalysisEngine(
            FakePersonTracker([tracked_person()]),
            FakeFaceRecognizer(
                [
                    FaceObservation(
                        face_detected=True,
                        candidate_member_id=7,
                        similarity=0.20,
                        face_confidence=0.88,
                    )
                ]
            ),
            match_threshold=0.35,
        )

        result = engine.analyze_frame(
            self.frame,
            frame_index=0,
            timestamp_seconds=0.0,
        )

        self.assertEqual(result.tracks[0].status, DetectionStatus.UNKNOWN)
        self.assertIsNone(result.tracks[0].member_id)

    def test_missing_face_is_low_quality_without_becoming_unknown(self):
        engine = FrameAnalysisEngine(
            FakePersonTracker([tracked_person()]),
            FakeFaceRecognizer(
                [
                    FaceObservation(
                        face_detected=False,
                        candidate_member_id=None,
                        similarity=None,
                        face_confidence=None,
                    )
                ]
            ),
        )

        result = engine.analyze_frame(
            self.frame,
            frame_index=0,
            timestamp_seconds=0.0,
        )

        self.assertEqual(result.tracks[0].status, DetectionStatus.LOW_QUALITY)

    def test_known_identity_is_inherited_when_face_temporarily_disappears(self):
        tracker = FakePersonTracker([tracked_person()])
        recognizer = FakeFaceRecognizer(
            [
                FaceObservation(True, 7, 0.80, 0.95),
                FaceObservation(False, None, None, None),
            ]
        )
        engine = FrameAnalysisEngine(tracker, recognizer)

        first = engine.analyze_frame(
            self.frame,
            frame_index=0,
            timestamp_seconds=0.0,
        )
        second = engine.analyze_frame(
            self.frame,
            frame_index=1,
            timestamp_seconds=0.1,
        )

        self.assertEqual(first.tracks[0].status, DetectionStatus.KNOWN)
        self.assertEqual(second.tracks[0].status, DetectionStatus.KNOWN)
        self.assertEqual(second.tracks[0].member_id, 7)

    def test_bounding_box_is_clamped_and_invalid_box_is_ignored(self):
        tracker = FakePersonTracker(
            [
                tracked_person(
                    track_id=1,
                    bounding_box=BoundingBox(-20, -10, 140, 110),
                ),
                tracked_person(
                    track_id=2,
                    bounding_box=BoundingBox(200, 200, 210, 220),
                ),
            ]
        )
        recognizer = FakeFaceRecognizer(
            [FaceObservation(False, None, None, None)]
        )
        engine = FrameAnalysisEngine(tracker, recognizer)

        result = engine.analyze_frame(
            self.frame,
            frame_index=0,
            timestamp_seconds=0.0,
        )

        self.assertEqual(len(result.tracks), 1)
        self.assertEqual(
            result.tracks[0].bounding_box,
            BoundingBox(0, 0, 120, 100),
        )

    def test_empty_or_non_bgr_frame_is_rejected(self):
        engine = FrameAnalysisEngine(
            FakePersonTracker([]),
            FakeFaceRecognizer([]),
        )

        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            engine.analyze_frame(
                np.array([], dtype=np.uint8),
                frame_index=0,
                timestamp_seconds=0,
            )
        with self.assertRaisesRegex(ValueError, "three channels"):
            engine.analyze_frame(
                np.zeros((10, 10), dtype=np.uint8),
                frame_index=0,
                timestamp_seconds=0,
            )

    def test_reset_clears_identity_and_resets_tracker(self):
        tracker = FakePersonTracker([tracked_person()])
        recognizer = FakeFaceRecognizer(
            [
                FaceObservation(True, 7, 0.80, 0.95),
                FaceObservation(False, None, None, None),
            ]
        )
        engine = FrameAnalysisEngine(tracker, recognizer)
        engine.analyze_frame(
            self.frame,
            frame_index=0,
            timestamp_seconds=0,
        )

        engine.reset()
        after_reset = engine.analyze_frame(
            self.frame,
            frame_index=1,
            timestamp_seconds=0.1,
        )

        self.assertTrue(tracker.reset_called)
        self.assertEqual(
            after_reset.tracks[0].status,
            DetectionStatus.LOW_QUALITY,
        )

    def test_annotation_returns_a_copy_with_overlay(self):
        engine = FrameAnalysisEngine(
            FakePersonTracker([tracked_person()]),
            FakeFaceRecognizer([FaceObservation(True, 7, 0.80, 0.95)]),
        )
        result = engine.analyze_frame(
            self.frame,
            frame_index=0,
            timestamp_seconds=0,
        )

        annotated = annotate_frame(
            self.frame,
            result,
            member_names={7: "Known Member"},
        )

        self.assertFalse(np.shares_memory(self.frame, annotated))
        self.assertGreater(int(annotated.sum()), 0)
        self.assertEqual(int(self.frame.sum()), 0)

    def test_yolo_adapter_is_lazy(self):
        tracker = YoloByteTracker(model_path="does-not-load-during-construction.pt")

        self.assertIsNone(tracker._model)


if __name__ == "__main__":
    unittest.main()
