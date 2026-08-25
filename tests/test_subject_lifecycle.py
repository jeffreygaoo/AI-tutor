import json
import tempfile
import unittest
from pathlib import Path

from scripts.tutor_cli import run
from tests.test_blueprint import blueprint_payload
from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository


class SubjectLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary.name)
        self.repository = JsonRepository(self.data_dir)
        self.service = TutorService(self.repository)
        self.service.create_subject("ml", "Machine Learning")
        self.service.create_blueprint("ml", blueprint_payload())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_reset_progress_preserves_curriculum_and_archives_learner_data(self) -> None:
        graph_ids = {item.id for item in self.repository.load_graph("ml").concepts}
        self.service.start_session("ml")
        self.service.evaluate(
            "ml",
            "problem_framing",
            {
                "concept_quiz": 1.0,
                "practice": 1.0,
                "application": 1.0,
                "transfer": 1.0,
                "delayed_review": 1.0,
            },
        )

        result = self.service.reset_subject_progress(
            "ml", confirmation="ml"
        )

        self.assertEqual(result["operation"], "reset-progress")
        self.assertTrue(result["preserved"]["graph"])
        self.assertTrue(result["preserved"]["blueprint"])
        self.assertEqual(
            {item.id for item in self.repository.load_graph("ml").concepts},
            graph_ids,
        )
        self.assertTrue(self.repository.blueprint_exists("ml"))
        self.assertEqual(self.service.session_history("ml")["sessions"], [])
        self.assertEqual(self.service.progress_report("ml")["mastered"], 0)
        self.assertIsNone(self.service.status("ml")["active_session"])
        archive = self.data_dir / result["archive"]
        self.assertTrue((archive / "manifest.json").is_file())
        manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["operation"], "reset-progress")

    def test_confirmation_mismatch_does_not_change_data(self) -> None:
        subject_path = self.data_dir / "subjects" / "ml.json"
        before = subject_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "confirmation must exactly match"):
            self.service.delete_subject("ml", confirmation="wrong")
        self.assertEqual(subject_path.read_bytes(), before)
        self.assertTrue(self.repository.subject_exists("ml"))

    def test_delete_subject_archives_all_learners_and_keeps_other_subjects(self) -> None:
        self.service.create_subject("python", "Python")
        self.service.graph_view("ml", "alice")
        self.service.start_session("ml", "alice")

        result = self.service.delete_subject("ml", confirmation="ml")

        self.assertTrue(result["deleted"])
        self.assertFalse(self.repository.subject_exists("ml"))
        self.assertFalse(self.repository.blueprint_exists("ml"))
        self.assertTrue(self.repository.subject_exists("python"))
        self.assertFalse((self.data_dir / "learners" / "default" / "ml.json").exists())
        self.assertFalse((self.data_dir / "learners" / "alice" / "ml.json").exists())
        self.assertFalse((self.data_dir / "sessions" / "alice" / "ml").exists())
        self.assertTrue((self.data_dir / result["archive"] / "manifest.json").is_file())

    def test_cli_supports_reset_and_delete_with_confirmation(self) -> None:
        reset = run([
            "--data-dir", str(self.data_dir),
            "reset-progress", "ml", "--confirm", "ml",
        ])
        self.assertEqual(reset["operation"], "reset-progress")
        deleted = run([
            "--data-dir", str(self.data_dir),
            "delete-subject", "ml", "--confirm", "ml",
        ])
        self.assertTrue(deleted["deleted"])


if __name__ == "__main__":
    unittest.main()
