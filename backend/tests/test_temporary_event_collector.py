import unittest

from backend.ai.contracts import (
    BoundingBox,
    FrameAnalysis,
    TrackAnalysis,
)
from backend.app.models import DetectionStatus
from backend.services.temporary_event_collector import TemporaryEventCollector


def analysis(frame_index, timestamp, status, member_id=None):
    return FrameAnalysis(
        frame_index=frame_index,
        timestamp_seconds=timestamp,
        width=20,
        height=20,
        tracks=(
            TrackAnalysis(
                track_id=1,
                bounding_box=BoundingBox(1, 1, 10, 10),
                person_confidence=0.9,
                status=status,
                member_id=member_id,
                similarity=0.75 if member_id else 0.2,
                face_confidence=0.9,
            ),
        ),
    )


class TemporaryEventCollectorTestCase(unittest.TestCase):
    def test_known_event_is_deduplicated_and_named(self):
        collector = TemporaryEventCollector(
            member_names={7: "Known Member"},
            unknown_confirmation_frames=2,
        )

        first = collector.process(
            analysis(0, 0.0, DetectionStatus.KNOWN, 7)
        )
        duplicate = collector.process(
            analysis(1, 0.1, DetectionStatus.KNOWN, 7)
        )

        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["member_name"], "Known Member")
        self.assertEqual(duplicate, [])
        self.assertEqual(collector.total_known_events, 1)

    def test_unknown_confirmation_and_cooldown_are_temporary(self):
        collector = TemporaryEventCollector(
            member_names={},
            unknown_confirmation_frames=2,
            unknown_cooldown_seconds=5,
        )

        self.assertEqual(
            collector.process(analysis(0, 0.0, DetectionStatus.UNKNOWN)),
            [],
        )
        first = collector.process(
            analysis(1, 1.0, DetectionStatus.UNKNOWN)
        )
        within_cooldown = collector.process(
            analysis(2, 3.0, DetectionStatus.UNKNOWN)
        )
        second = collector.process(
            analysis(3, 6.0, DetectionStatus.UNKNOWN)
        )

        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["event_type"], "unknown_person")
        self.assertEqual(within_cooldown, [])
        self.assertEqual(len(second), 1)
        self.assertEqual(collector.total_unknown_events, 2)

    def test_event_list_is_bounded(self):
        collector = TemporaryEventCollector(
            member_names={},
            unknown_confirmation_frames=1,
            unknown_cooldown_seconds=0,
            max_events=2,
        )

        for index in range(4):
            collector.process(
                analysis(index, float(index), DetectionStatus.UNKNOWN)
            )

        self.assertEqual(len(collector.events), 2)
        self.assertTrue(collector.events_truncated)
        self.assertEqual(collector.total_unknown_events, 4)


if __name__ == "__main__":
    unittest.main()
