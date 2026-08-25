import unittest

from tutor_engine.curriculum import DependencyEngine
from tutor_engine.graph import Concept, ConceptGraph, Relation
from tutor_engine.learner import Learner


class DependencyEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = ConceptGraph(
            "ml",
            concepts=[Concept("statistics", "Statistics"), Concept("regression", "Regression")],
            relations=[
                Relation(
                    "statistics_to_regression",
                    "statistics",
                    "regression",
                    "prerequisite",
                    threshold=0.75,
                )
            ],
        )
        self.learner = Learner("default")
        self.engine = DependencyEngine(self.graph, self.learner)

    def test_root_is_available_and_dependent_starts_locked(self) -> None:
        self.assertTrue(self.engine.unlock("statistics"))
        self.assertFalse(self.engine.unlock("regression"))
        self.assertEqual(self.learner.concepts["statistics"].status, "available")
        self.assertEqual(self.learner.concepts["regression"].status, "locked")

    def test_unlocks_when_threshold_is_met(self) -> None:
        self.learner.get_mastery("statistics").score = 0.75
        self.assertTrue(self.engine.unlock("regression"))
        self.assertEqual(self.learner.concepts["regression"].status, "available")

    def test_get_available_excludes_mastered(self) -> None:
        self.engine.refresh()
        self.learner.concepts["statistics"].status = "mastered"
        self.assertEqual(self.engine.get_available_concepts(), ())

    def test_refresh_does_not_erase_mastered_status(self) -> None:
        state = self.learner.get_or_create_concept("regression")
        state.status = "mastered"
        self.engine.refresh()
        self.assertEqual(state.status, "mastered")
