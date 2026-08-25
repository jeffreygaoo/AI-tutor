import unittest

from tutor_engine.learner import Learner
from tutor_engine.mastery import MasteryEvaluator


class MasteryEvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = MasteryEvaluator()
        self.learner = Learner("default")

    def test_evaluation_is_weighted_and_explainable(self) -> None:
        result = self.evaluator.evaluate({"concept_quiz": 1.0, "transfer": 0.0})
        self.assertAlmostEqual(result.score, 2 / 3)
        self.assertIn("coverage", result.explanation)
        self.assertLess(result.confidence, result.score)

    def test_update_changes_mastery_attempt_and_status(self) -> None:
        self.evaluator.update_mastery(
            self.learner,
            "statistics",
            {
                "concept_quiz": 0.9,
                "practice": 0.9,
                "application": 0.8,
                "transfer": 0.8,
                "delayed_review": 0.8,
            },
        )
        state = self.learner.concepts["statistics"]
        self.assertEqual(state.attempt_count, 1)
        self.assertEqual(state.status, "mastered")
        self.assertGreater(state.mastery.confidence, 0.7)

    def test_low_evidence_is_reported_as_weak(self) -> None:
        self.evaluator.update_mastery(self.learner, "statistics", {"practice": 0.2})
        self.assertEqual(self.learner.concepts["statistics"].status, "weak")
        self.assertEqual(
            [item.concept_id for item in self.evaluator.get_weak_concepts(self.learner)],
            ["statistics"],
        )

    def test_high_score_with_low_confidence_is_not_mastered(self) -> None:
        self.evaluator.update_mastery(
            self.learner, "statistics", {"delayed_review": 1.0}
        )
        state = self.learner.concepts["statistics"]
        self.assertEqual(state.mastery.score, 1.0)
        self.assertLess(state.mastery.confidence, 0.60)
        self.assertEqual(state.status, "familiar")

    def test_rejects_unknown_dimension(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown evidence"):
            self.evaluator.evaluate({"memory": 0.8})
