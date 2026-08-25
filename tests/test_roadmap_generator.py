import unittest

from tutor_engine.graph import Concept, ConceptGraph, Relation
from tutor_engine.roadmap import RoadmapConfig, analyze_roadmap


class RoadmapGeneratorTests(unittest.TestCase):
    def chain_graph(self) -> ConceptGraph:
        return ConceptGraph(
            "ml",
            concepts=[
                Concept("ml", "Machine Learning", importance=1.0),
                Concept("calculus", "Calculus", importance=0.0, metadata={"goal_relevance": 0.0}),
                Concept("gradient_descent", "Gradient Descent", importance=0.0, metadata={"goal_relevance": 0.0}),
                Concept("neural_network", "Neural Network", importance=1.0, metadata={"goal_relevance": 1.0}),
            ],
            relations=[
                Relation("calc_gd", "calculus", "gradient_descent", "prerequisite"),
                Relation("gd_nn", "gradient_descent", "neural_network", "prerequisite"),
            ],
        )

    def test_core_score_uses_configured_40_30_30_formula(self) -> None:
        analysis = analyze_roadmap(self.chain_graph(), RoadmapConfig())
        neural_network = next(item for item in analysis.concepts if item.concept_id == "neural_network")
        self.assertEqual(neural_network.core_score, 0.7)
        self.assertEqual(neural_network.inclusion_type, "core")

    def test_prerequisite_closure_adds_low_scoring_ancestors(self) -> None:
        analysis = analyze_roadmap(self.chain_graph(), RoadmapConfig())
        self.assertEqual(analysis.mvlg_ids, {"calculus", "gradient_descent", "neural_network"})
        by_id = {item.concept_id: item for item in analysis.concepts}
        self.assertEqual(by_id["calculus"].inclusion_type, "prerequisite")
        self.assertEqual(by_id["gradient_descent"].inclusion_type, "prerequisite")
        self.assertIn("required prerequisite", by_id["calculus"].selection_reason)

    def test_topological_layers_allow_parallel_branches_and_merge(self) -> None:
        graph = ConceptGraph(
            "subject",
            concepts=[
                Concept("subject", "Subject", importance=1.0),
                Concept("a", "A", importance=0.0, metadata={"goal_relevance": 0.0}),
                Concept("b", "B", importance=0.0, metadata={"goal_relevance": 0.0}),
                Concept("c", "C", importance=1.0, metadata={"goal_relevance": 1.0}),
            ],
            relations=[
                Relation("a_c", "a", "c", "prerequisite"),
                Relation("b_c", "b", "c", "prerequisite"),
            ],
        )
        analysis = analyze_roadmap(graph, RoadmapConfig())
        layers = {item.concept_id: item.topological_layer for item in analysis.concepts}
        self.assertEqual(layers, {"a": 0, "b": 0, "c": 1})

    def test_invalid_weight_configuration_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "sum to 1.0"):
            RoadmapConfig(goal_weight=0.5, importance_weight=0.5, leverage_weight=0.5)


if __name__ == "__main__":
    unittest.main()
