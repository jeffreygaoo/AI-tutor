import tempfile
import unittest
from pathlib import Path

from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository


class SessionAnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repository = JsonRepository(Path(self.temporary.name))
        self.service = TutorService(self.repository)
        self.service.create_subject("ml", "Machine Learning")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_session_records_learning_events_and_survives_restart(self) -> None:
        started = self.service.start_session("ml")
        self.service.learn("ml", concept_id="ml")
        self.service.evaluate(
            "ml",
            "ml",
            {
                "concept_quiz": 0.9,
                "practice": 0.9,
                "application": 0.9,
                "transfer": 0.9,
                "delayed_review": 0.9,
            },
        )
        ended = self.service.end_session("ml")
        self.assertEqual(ended["id"], started["id"])
        self.assertIsNotNone(ended["ended_at"])
        self.assertEqual(
            [event["type"] for event in ended["events"]],
            ["session_started", "concept_started", "mastery_updated", "session_ended"],
        )

        resumed = TutorService(JsonRepository(Path(self.temporary.name)))
        history = resumed.session_history("ml")
        self.assertEqual(history["sessions"][0]["id"], started["id"])
        self.assertIsNone(resumed.status("ml")["active_session"])

    def test_prevents_two_active_sessions(self) -> None:
        self.service.start_session("ml")
        with self.assertRaisesRegex(ValueError, "already active"):
            self.service.start_session("ml")

    def test_progress_report_uses_persisted_evidence(self) -> None:
        self.service.start_session("ml")
        self.service.learn("ml")
        self.service.evaluate(
            "ml",
            "ml",
            {
                "concept_quiz": 0.85,
                "practice": 0.85,
                "application": 0.85,
                "transfer": 0.85,
                "delayed_review": 0.85,
            },
        )
        self.service.end_session("ml")
        report = self.service.progress_report("ml")
        self.assertEqual(report["progress"], 1.0)
        self.assertEqual(report["attempts"], 1)
        self.assertEqual(report["sessions"], 1)
        self.assertEqual(report["completed_sessions"], 1)
        self.assertEqual(report["mastered_per_completed_session"], 1.0)
