from collections import Counter, defaultdict, deque
from dataclasses import dataclass

from backend.app.models import DetectionStatus


@dataclass(frozen=True)
class RecognitionDecision:
    status: DetectionStatus
    member_id: int | None
    similarity: float | None


class TrackRecognitionBuffer:
    def __init__(self, *, size: int, match_threshold: float) -> None:
        if size <= 0:
            raise ValueError("Recognition buffer size must be positive")
        self.size = size
        self.match_threshold = match_threshold
        self._samples: dict[int, deque[tuple[int | None, float]]] = defaultdict(
            lambda: deque(maxlen=self.size)
        )

    def add(
        self,
        track_id: int,
        candidate_member_id: int | None,
        similarity: float,
    ) -> RecognitionDecision:
        samples = self._samples[track_id]
        samples.append((candidate_member_id, similarity))
        return self.decision(track_id)

    def decision(self, track_id: int) -> RecognitionDecision:
        samples = self._samples.get(track_id)
        if not samples:
            return RecognitionDecision(
                status=DetectionStatus.LOW_QUALITY,
                member_id=None,
                similarity=None,
            )

        identified = [
            (member_id, score)
            for member_id, score in samples
            if member_id is not None
        ]
        if not identified:
            average = sum(score for _, score in samples) / len(samples)
            return RecognitionDecision(
                status=DetectionStatus.UNKNOWN,
                member_id=None,
                similarity=float(average),
            )

        counts = Counter(member_id for member_id, _ in identified)
        scores_by_member: dict[int, list[float]] = defaultdict(list)
        for member_id, score in identified:
            scores_by_member[member_id].append(score)

        winner = max(
            counts,
            key=lambda member_id: (
                counts[member_id],
                sum(scores_by_member[member_id])
                / len(scores_by_member[member_id]),
                -member_id,
            ),
        )
        winner_score = sum(scores_by_member[winner]) / len(scores_by_member[winner])
        if winner_score >= self.match_threshold:
            return RecognitionDecision(
                status=DetectionStatus.KNOWN,
                member_id=winner,
                similarity=float(winner_score),
            )
        return RecognitionDecision(
            status=DetectionStatus.UNKNOWN,
            member_id=None,
            similarity=float(winner_score),
        )

    def clear_track(self, track_id: int) -> None:
        self._samples.pop(track_id, None)

    def reset(self) -> None:
        self._samples.clear()
