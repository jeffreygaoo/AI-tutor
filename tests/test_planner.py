import unittest

from tutor_engine.curriculum import CurriculumPlanner
from tutor_engine.graph import Concept, ConceptGraph, Relation
from tutor_engine.learner import Learner


class CurriculumPlannerTests(unittest.TestCase):
    def test_selects_high_value_available_concept_with_reason(self) -> None:
        graph = ConceptGraph(
            "ml",
            concepts=[
                Concept(
                    "probability",
                    "Probability",
                    importance=0.9,
                    metadata={"goal_relevance": 0.8},
                ),
                Concept(
                    "linear_algebra",
                    "Linear Algebra",
                    difficulty=3,
                    importance=0.7,
                    metadata={"goal_relevance": 0.7},
                ),
                Concept("statistics", "Statistics", importance=0.9),
            ],
            relations=[
                Relation("p_to_s", "probability", "statistics", "prerequisite")
            ],
        )
        selection = CurriculumPlanner(graph, Learner("default")).next_concept()
        self.assertEqual(selection.concept, "probability")
        self.assertIsNotNone(selection.priority)
        self.assertIn("前置价值", selection.reason)

    def test_does_not_select_locked_or_mastered_concepts(self) -> None:
        graph = ConceptGraph(
            "ml",
            concepts=[Concept("a", "A"), Concept("b", "B")],
            relations=[Relation("a_to_b", "a", "b", "prerequisite")],
        )
        learner = Learner("default")
        learner.get_or_create_concept("a").status = "mastered"
        learner.get_mastery("a").score = 0.7  # Below the default 0.8 threshold.
        selection = CurriculumPlanner(graph, learner).next_concept()
        self.assertIsNone(selection.concept)

    def test_returns_empty_selection_after_all_concepts_mastered(self) -> None:
        graph = ConceptGraph("ml", concepts=[Concept("a", "A")])
        learner = Learner("default")
        learner.get_or_create_concept("a").status = "mastered"
        selection = CurriculumPlanner(graph, learner).next_concept()
        self.assertEqual(
            selection.to_dict(),
            {
                "concept": None,
                "reason": "当前没有已解锁且尚未掌握的可学习知识点。",
                "priority": None,
                "factors": None,
            },
        )
