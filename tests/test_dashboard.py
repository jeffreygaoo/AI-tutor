import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

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
            with urlopen(base + "/app.js", timeout=3) as response:
                javascript = response.read().decode("utf-8")
            with urlopen(base + "/api/state", timeout=3) as response:
                value = json.loads(response.read().decode("utf-8"))
            with urlopen(base + "/api/subjects", timeout=3) as response:
                catalog = json.loads(response.read().decode("utf-8"))
            with urlopen(base + "/api/state?subject=python", timeout=3) as response:
                pending = json.loads(response.read().decode("utf-8"))
            self.assertIn("AI Tutor · 学习看板", html)
            self.assertIn('id="conceptDrawer"', html)
            self.assertIn('id="manageDialog"', html)
            self.assertIn('data-concept=', javascript)
            self.assertIn('data-drill=', javascript)
            self.assertIn("reset-progress", javascript)
            self.assertIn("delete-subject", javascript)
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

    def test_http_api_resets_progress_and_deletes_subject(self) -> None:
        server = create_server(self.data_dir, "ml", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"

            def post(path: str, value: dict) -> dict:
                request = Request(
                    base + path,
                    data=json.dumps(value).encode("utf-8"),
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "X-AI-Tutor-Action": "true",
                    },
                )
                with urlopen(request, timeout=3) as response:
                    return json.loads(response.read().decode("utf-8"))

            reset = post("/api/reset-progress", {
                "subject": "ml", "confirmation": "ml",
            })
            self.assertEqual(reset["operation"], "reset-progress")
            self.assertTrue(self.service.repository.subject_exists("ml"))

            deleted = post("/api/delete-subject", {
                "subject": "python", "confirmation": "python",
            })
            self.assertTrue(deleted["deleted"])
            self.assertEqual(
                {item["id"] for item in deleted["catalog"]["subjects"]},
                {"ml"},
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_localization_updates_display_text_without_changing_graph_ids(self) -> None:
        before = self.service.graph_view("ml")
        result = self.service.localize_subject("ml", {
            "goal": "构建表格分类项目",
            "concepts": {"problem_framing": {"name": "问题定义"}},
            "sections": {"orientation": {"name": "学习导向"}},
        })
        after = self.service.graph_view("ml")
        blueprint = self.service.blueprint_view("ml")
        self.assertEqual(result["revision"], 2)
        self.assertEqual(
            {item["id"] for item in before["concepts"]},
            {item["id"] for item in after["concepts"]},
        )
        self.assertEqual(blueprint["scope"]["goal"], "构建表格分类项目")
        self.assertEqual(blueprint["landscape"][0]["name"], "学习导向")
        self.assertEqual(blueprint["landscape"][0]["concepts"][0]["name"], "问题定义")


if __name__ == "__main__":
    unittest.main()
