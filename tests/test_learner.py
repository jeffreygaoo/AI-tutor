import json
import unittest

from tutor_engine.learner import Learner, Misconception


class LearnerTests(unittest.TestCase):
    def test_state_json_round_trip(self) -> None:
        learner = Learner("default", preferences={"explanation_style": "example_first"})
        state = learner.get_or_create_concept("probability")
        state.mastery.score = 0.65
        state.mastery.confidence = 0.4
        state.status = "familiar"
        state.misconceptions.append(
            Misconception("m1", "Independent means mutually exclusive", severity=0.8)
        )

        restored = Learner.from_dict(json.loads(json.dumps(learner.to_dict())))
        self.assertEqual(restored.to_dict(), learner.to_dict())

    def test_resolve_misconception(self) -> None:
        misconception = Misconception("m1", "A mistaken belief")
        misconception.resolve("2026-08-25T00:00:00+00:00")
        self.assertTrue(misconception.resolved)
        self.assertEqual(misconception.resolved_at, "2026-08-25T00:00:00+00:00")
