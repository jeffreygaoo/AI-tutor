import unittest
from datetime import datetime, timedelta, timezone

from tutor_engine.learner import Learner
from tutor_engine.review import ReviewScheduler


class ReviewSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scheduler = ReviewScheduler()
        self.state = Learner("default").get_or_create_concept("probability")
        self.now = datetime(2026, 8, 25, tzinfo=timezone.utc)

    def test_schedules_first_review_one_day_after_mastery(self) -> None:
        self.scheduler.schedule_after_mastery(self.state, now=self.now)
        self.assertEqual(
            self.state.review.next_review,
            (self.now + timedelta(days=1)).isoformat(),
        )

    def test_pass_advances_and_failure_shortens_interval(self) -> None:
        self.scheduler.schedule_after_mastery(self.state, now=self.now)
        self.scheduler.record_review(self.state, 0.9, now=self.now)
        self.assertEqual(self.state.review.stage, 1)
        self.assertEqual(
            self.state.review.next_review,
            (self.now + timedelta(days=3)).isoformat(),
        )
        self.scheduler.record_review(self.state, 0.3, now=self.now)
        self.assertEqual(self.state.review.stage, 0)
        self.assertEqual(
            self.state.review.next_review,
            (self.now + timedelta(days=1)).isoformat(),
        )

    def test_lists_only_due_reviews(self) -> None:
        learner = Learner("default")
        due = learner.get_or_create_concept("due")
        later = learner.get_or_create_concept("later")
        due.review.next_review = (self.now - timedelta(minutes=1)).isoformat()
        later.review.next_review = (self.now + timedelta(days=1)).isoformat()
        self.assertEqual(
            [item.concept_id for item in self.scheduler.due_concepts(learner, now=self.now)],
            ["due"],
        )
