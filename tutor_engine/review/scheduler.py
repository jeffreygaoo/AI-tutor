"""Simple explainable 1/3/7/14/30-day review schedule for V0.1."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tutor_engine.learner import Learner, LearnerConcept


INTERVAL_DAYS = (1, 3, 7, 14, 30)


def _utc(value: datetime | None = None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ValueError("review timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


class ReviewScheduler:
    def schedule_after_mastery(
        self, state: LearnerConcept, *, now: datetime | None = None
    ) -> None:
        if state.review.next_review is not None:
            return
        current = _utc(now)
        state.review.stage = 0
        state.review.next_review = (current + timedelta(days=INTERVAL_DAYS[0])).isoformat()

    def record_review(
        self,
        state: LearnerConcept,
        score: float,
        *,
        now: datetime | None = None,
        pass_score: float = 0.70,
    ) -> None:
        if not 0.0 <= score <= 1.0:
            raise ValueError("review score must be between 0.0 and 1.0")
        current = _utc(now)
        state.review.last_review = current.isoformat()
        if score >= pass_score:
            state.review.stage = min(state.review.stage + 1, len(INTERVAL_DAYS) - 1)
        else:
            state.review.stage = max(0, state.review.stage - 1)
        days = INTERVAL_DAYS[state.review.stage]
        state.review.next_review = (current + timedelta(days=days)).isoformat()

    def due_concepts(
        self, learner: Learner, *, now: datetime | None = None
    ) -> tuple[LearnerConcept, ...]:
        current = _utc(now)
        due = []
        for state in learner.concepts.values():
            if state.review.next_review is None:
                continue
            scheduled = datetime.fromisoformat(state.review.next_review)
            if scheduled.tzinfo is None:
                raise ValueError("persisted review timestamp must be timezone-aware")
            if scheduled.astimezone(timezone.utc) <= current:
                due.append(state)
        return tuple(sorted(due, key=lambda item: (item.review.next_review or "", item.concept_id)))
