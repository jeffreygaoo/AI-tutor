import json
import unittest

from tutor_engine.graph import Concept, ConceptGraph, GraphValidationError, Relation


class ConceptGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = ConceptGraph("machine_learning")
        for concept in (
            Concept("probability", "Probability", difficulty=2, importance=0.9),
            Concept("statistics", "Statistics", difficulty=2, importance=0.9),
            Concept("regression", "Regression", difficulty=3, importance=0.9),
        ):
            self.graph.add_concept(concept)
        self.graph.add_relation(
            Relation("probability_to_statistics", "probability", "statistics", "prerequisite")
        )
        self.graph.add_relation(
            Relation("statistics_to_regression", "statistics", "regression", "prerequisite")
        )

    def test_queries_prerequisites_and_dependents(self) -> None:
        self.assertEqual(
            [concept.id for concept in self.graph.get_prerequisites("regression")],
            ["statistics"],
        )
        self.assertEqual(
            [concept.id for concept in self.graph.get_dependents("probability")],
            ["statistics"],
        )

    def test_rejects_unknown_relation_endpoint_without_mutating_graph(self) -> None:
        with self.assertRaisesRegex(GraphValidationError, "unknown relation target"):
            self.graph.add_relation(
                Relation("bad", "statistics", "missing", "prerequisite")
            )
        self.assertEqual(len(self.graph.relations), 2)

    def test_rejects_prerequisite_cycle_and_rolls_back(self) -> None:
        with self.assertRaisesRegex(GraphValidationError, "acyclic"):
            self.graph.add_relation(
                Relation("regression_to_probability", "regression", "probability", "prerequisite")
            )
        self.assertEqual(len(self.graph.relations), 2)
        self.graph.validate_graph()

    def test_json_round_trip(self) -> None:
        encoded = json.dumps(self.graph.to_dict())
        restored = ConceptGraph.from_dict(json.loads(encoded))
        self.assertEqual(restored.to_dict(), self.graph.to_dict())

    def test_validates_concept_ranges(self) -> None:
        with self.assertRaisesRegex(GraphValidationError, "difficulty"):
            Concept("bad", "Bad", difficulty=6)
        with self.assertRaisesRegex(GraphValidationError, "importance"):
            Concept("bad", "Bad", importance=1.1)


if __name__ == "__main__":
    unittest.main()
