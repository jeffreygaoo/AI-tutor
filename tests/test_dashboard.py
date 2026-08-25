import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

from scripts.tutor_cli import build_parser
from tests.test_blueprint import blueprint_payload
from tutor_engine.dashboard import build_dashboard_state
from tutor_engine.dashboard.server import build_subject_catalog, create_server
from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository


class DashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary.name)
        self.service = TutorService(JsonRepository(self.data_dir))
        self.service.create_subject("ml", "Machine Learning")
        self.service.create_blueprint("ml", blueprint_payload())
        self.service.create_subject("python", "Python")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_builds_read_model_through_service(self) -> None:
        value = build_dashboard_state(self.service, "ml")
        self.assertEqual(value["subject"], "ml")
        self.assertEqual(value["blueprint"]["scope"]["goal"], "Build a tabular classification project")
        self.assertEqual(value["roadmap"]["mvlg_concept_count"], 3)
        self.assertIn("status_distribution", value["progress"])
        self.assertIn("concept", value["next"])

    def test_catalog_includes_blueprinted_and_uninitialized_subjects(self) -> None:
        value = build_subject_catalog(JsonRepository(self.data_dir))
        by_id = {item["id"]: item for item in value["subjects"]}
        self.assertTrue(by_id["ml"]["has_blueprint"])
        self.assertFalse(by_id["python"]["has_blueprint"])
        self.assertEqual(by_id["python"]["goal"], "尚未创建 Subject Blueprint")

    def test_http_server_exposes_ui_and_utf8_json(self) -> None:
        server = create_server(self.data_dir, "ml", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(base + "/", timeout=3) as response:
                html = response.read().decode("utf-8")
            with urlopen(base + "/api/state", timeout=3) as response:
                value = json.loads(response.read().decode("utf-8"))
            with urlopen(base + "/api/subjects", timeout=3) as response:
                catalog = json.loads(response.read().decode("utf-8"))
            with urlopen(base + "/api/state?subject=python", timeout=3) as response:
                pending = json.loads(response.read().decode("utf-8"))
            self.assertIn("AI Tutor · Learning Dashboard", html)
            self.assertEqual(value["subject"], "ml")
            self.assertEqual(value["blueprint"]["landscape"][0]["name"], "Orientation")
            self.assertEqual({item["id"] for item in catalog["subjects"]}, {"ml", "python"})
            self.assertFalse(pending["ready"])
            self.assertIsNone(pending["blueprint"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_cli_accepts_dashboard_launch_options(self) -> None:
        args = build_parser().parse_args([
            "--data-dir", str(self.data_dir), "dashboard", "ml",
            "--host", "127.0.0.1", "--port", "9000", "--no-open",
        ])
        self.assertEqual(args.command, "dashboard")
        self.assertEqual(args.port, 9000)
        self.assertTrue(args.no_open)

    def test_cli_allows_workspace_dashboard_without_subject(self) -> None:
        args = build_parser().parse_args(["dashboard", "--no-open"])
        self.assertIsNone(args.subject)


if __name__ == "__main__":
    unittest.main()
