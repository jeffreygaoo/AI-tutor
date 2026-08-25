import json
import tempfile
import unittest
from pathlib import Path

from scripts.tutor_cli import run
from tutor_engine.graph import Concept, Relation
from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository, StorageError


class PersistenceEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_create_learn_evaluate_and_resume(self) -> None:
        service = TutorService(JsonRepository(self.data_dir))
        service.create_subject("machine_learning", "Machine Learning")
        self.assertEqual(service.next_concept("machine_learning")["concept"], "machine_learning")
        self.assertEqual(service.learn("machine_learning")["status"], "learning")
        evaluated = service.evaluate(
            "machine_learning",
            "machine_learning",
            {
                "concept_quiz": 0.9,
                "practice": 0.9,
                "application": 0.9,
                "transfer": 0.9,
                "delayed_review": 0.9,
            },
        )
        self.assertEqual(evaluated["status"], "mastered")

        # Simulate a fresh process by rebuilding repository and service instances.
        resumed = TutorService(JsonRepository(self.data_dir))
        status = resumed.status("machine_learning")
        self.assertEqual(status["progress"], 1.0)
        self.assertIsNone(status["next"])
        self.assertEqual(
            resumed.graph_view("machine_learning")["concepts"][0]["learner"]["attempt_count"],
            1,
        )

    def test_atomic_files_are_valid_json(self) -> None:
        service = TutorService(JsonRepository(self.data_dir))
        service.create_subject("ml", "Machine Learning")
        for path in self.data_dir.rglob("*.json"):
            with path.open(encoding="utf-8") as handle:
                self.assertIsInstance(json.load(handle), dict)
        self.assertEqual(list(self.data_dir.rglob("*.tmp")), [])

    def test_rejects_path_traversal_identifier(self) -> None:
        repository = JsonRepository(self.data_dir)
        with self.assertRaises(StorageError):
            repository.load_graph("../outside")

    def test_cli_protocol_uses_json_and_persists(self) -> None:
        created = run(
            ["--data-dir", str(self.data_dir), "create", "ml", "--name", "ML"]
        )
        self.assertEqual(created["subject"], "ml")
        learned = run(["--data-dir", str(self.data_dir), "learn", "ml"])
        self.assertEqual(learned["concept"], "ml")
        status = run(["--data-dir", str(self.data_dir), "status", "ml"])
        self.assertEqual(status["current"], "ml")

    def test_graph_can_expand_and_persist(self) -> None:
        repository = JsonRepository(self.data_dir)
        TutorService(repository).create_subject("ml", "ML")
        graph = repository.load_graph("ml")
        graph.add_concept(Concept("statistics", "Statistics"))
        graph.add_relation(Relation("s_to_ml", "statistics", "ml", "prerequisite"))
        repository.save_graph(graph)
        restored = repository.load_graph("ml")
        self.assertEqual(restored.get_prerequisites("ml")[0].id, "statistics")
