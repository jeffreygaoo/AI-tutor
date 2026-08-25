import tempfile
import unittest
from pathlib import Path

from tutor_engine.graph import GraphValidationError
from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository


class ProgressiveExpansionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repository = JsonRepository(Path(self.temporary.name))
        self.service = TutorService(self.repository)
        self.service.create_subject("ml", "Machine Learning")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_expands_a_small_connected_batch(self) -> None:
        result = self.service.expand_subject(
            "ml",
            "ml",
            {
                "concepts": [
                    {"id": "statistics", "name": "Statistics", "depth": 1},
                    {"id": "regression", "name": "Regression", "depth": 2},
                ],
                "relations": [
                    {"id": "statistics_to_ml", "source": "statistics", "target": "ml", "type": "part_of"},
                    {"id": "statistics_to_regression", "source": "statistics", "target": "regression", "type": "prerequisite"},
                ],
            },
        )
        self.assertEqual(result["total_concepts"], 3)
        self.assertEqual(len(self.repository.load_graph("ml").concepts), 3)

    def test_disconnected_expansion_rolls_back(self) -> None:
        with self.assertRaisesRegex(GraphValidationError, "connect to anchor"):
            self.service.expand_subject(
                "ml",
                "ml",
                {
                    "concepts": [{"id": "orphan", "name": "Orphan"}],
                    "relations": [],
                },
            )
        self.assertEqual(
            [concept.id for concept in self.repository.load_graph("ml").concepts],
            ["ml"],
        )

    def test_expansion_batch_is_bounded(self) -> None:
        with self.assertRaisesRegex(GraphValidationError, "batch limit"):
            self.service.expand_subject(
                "ml",
                "ml",
                {
                    "concepts": [
                        {"id": f"c{number}", "name": f"C {number}"}
                        for number in range(21)
                    ],
                    "relations": [],
                },
            )
