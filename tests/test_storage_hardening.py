import json
import tempfile
import unittest
from pathlib import Path

from tutor_engine.graph import Concept, ConceptGraph
from tutor_engine.learner import Learner
from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository, SCHEMA_VERSION, SchemaError
from tutor_engine.storage.migrations import migrate_payload


class StorageHardeningTests(unittest.TestCase):
    def test_models_persist_current_schema_version(self) -> None:
        self.assertEqual(ConceptGraph("ml").to_dict()["schema_version"], SCHEMA_VERSION)
        self.assertEqual(Learner("default").to_dict()["schema_version"], SCHEMA_VERSION)

    def test_migrates_legacy_learner_defaults(self) -> None:
        migrated = migrate_payload(
            {
                "learner_id": "default",
                "concepts": {
                    "probability": {
                        "concept_id": "probability",
                        "status": "learning",
                        "mastery": {"score": 0.5, "confidence": 0.4},
                    }
                },
            },
            "learner",
        )
        self.assertEqual(migrated["schema_version"], SCHEMA_VERSION)
        self.assertIsNone(migrated["active_session_id"])
        self.assertEqual(migrated["concepts"]["probability"]["review"]["stage"], 0)

    def test_rejects_future_schema(self) -> None:
        with self.assertRaisesRegex(SchemaError, "newer"):
            migrate_payload({"schema_version": SCHEMA_VERSION + 1}, "graph")

    def test_corrupt_primary_recovers_previous_valid_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary)
            repository = JsonRepository(data_dir)
            graph = ConceptGraph("ml", concepts=[Concept("ml", "ML")])
            repository.save_graph(graph)
            graph.add_concept(Concept("probability", "Probability"))
            repository.save_graph(graph)
            path = data_dir / "subjects" / "ml.json"
            path.write_text("{broken", encoding="utf-8")

            recovered = repository.load_graph("ml")
            self.assertEqual([item.id for item in recovered.concepts], ["ml"])
            self.assertEqual(repository.recoveries, [str(path)])

    def test_doctor_validates_persisted_subject(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = TutorService(JsonRepository(Path(temporary)))
            service.create_subject("ml", "Machine Learning")
            result = service.doctor("ml")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["schema_version"], SCHEMA_VERSION)
