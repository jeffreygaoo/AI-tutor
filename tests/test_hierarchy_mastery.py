import unittest

from tutor_engine.curriculum import CurriculumPlanner, DependencyEngine
from tutor_engine.graph import Concept, ConceptGraph, Relation
from tutor_engine.learner import Learner
from tutor_engine.mastery import HierarchyMasteryEvaluator


class HierarchyMasteryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = ConceptGraph(
            "cloud",
            concepts=[
                Concept(
                    "distributed_training",
                    "分布式训练",
                    metadata={"expandable": True, "expansion_status": "expanded"},
                ),
                Concept("data_parallel", "数据并行", importance=1.0),
                Concept("all_reduce", "AllReduce", importance=0.5),
                Concept("advanced_training", "高级训练", importance=1.0),
            ],
            relations=[
                Relation("data_part", "data_parallel", "distributed_training", "part_of"),
                Relation("all_reduce_part", "all_reduce", "distributed_training", "part_of"),
                Relation(
                    "topic_to_advanced",
                    "distributed_training",
                    "advanced_training",
                    "prerequisite",
                    threshold=0.8,
                ),
            ],
        )
        self.learner = Learner("default")

    def test_aggregates_weighted_child_mastery_and_unlocks_dependent(self) -> None:
        for concept_id in ("data_parallel", "all_reduce"):
            state = self.learner.get_or_create_concept(concept_id)
            state.status = "mastered"
            state.mastery.score = 0.9
            state.mastery.confidence = 0.8
            state.mastery.updated_at = "2026-08-25T00:00:00+00:00"
        DependencyEngine(self.graph, self.learner).refresh()
        progress = HierarchyMasteryEvaluator().update(self.graph, self.learner)
        DependencyEngine(self.graph, self.learner).refresh()

        parent = self.learner.get_or_create_concept("distributed_training")
        self.assertEqual(parent.status, "mastered")
        self.assertEqual(parent.mastery.score, 0.9)
        self.assertEqual(progress["distributed_training"].mastered_children, 2)
        self.assertEqual(
            self.learner.get_or_create_concept("advanced_training").status,
            "available",
        )

    def test_partial_children_keep_topic_in_progress(self) -> None:
        state = self.learner.get_or_create_concept("data_parallel")
        state.status = "mastered"
        state.mastery.score = 0.9
        state.mastery.confidence = 0.8
        state.mastery.updated_at = "2026-08-25T00:00:00+00:00"
        progress = HierarchyMasteryEvaluator().update(self.graph, self.learner)
        parent = self.learner.get_or_create_concept("distributed_training")
        self.assertNotEqual(parent.status, "mastered")
        self.assertEqual(progress["distributed_training"].mastered_children, 1)
        self.assertEqual(progress["distributed_training"].total_children, 2)

    def test_planner_never_selects_expanded_topic(self) -> None:
        selection = CurriculumPlanner(self.graph, self.learner).next_concept()
        self.assertNotEqual(selection.concept, "distributed_training")
        self.assertIn(selection.concept, {"data_parallel", "all_reduce"})


if __name__ == "__main__":
    unittest.main()
