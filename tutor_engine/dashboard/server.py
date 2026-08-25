"""Standard-library HTTP server for the local AI Tutor dashboard."""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository


STATIC_DIR = Path(__file__).with_name("static")
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}


def build_dashboard_state(
    service: TutorService, subject_id: str, learner_id: str = "default"
) -> dict[str, Any]:
    """Build one consistent, JSON-friendly read model through TutorService."""
    base = {
        "subject": subject_id,
        "learner": learner_id,
        "status": service.status(subject_id, learner_id),
        "progress": service.progress_report(subject_id, learner_id),
        "next": service.next_concept(subject_id, learner_id),
        "review": service.review(subject_id, learner_id),
        "history": service.session_history(subject_id, learner_id),
        "graph": service.graph_view(subject_id, learner_id),
    }
    if not service.repository.blueprint_exists(subject_id):
        return {**base, "ready": False, "blueprint": None, "roadmap": None, "directions": {"subject": subject_id, "directions": []}}
    return {
        **base,
        "ready": True,
        "blueprint": service.blueprint_view(subject_id, learner_id),
        "roadmap": service.roadmap(subject_id, learner_id),
        "directions": service.directions(subject_id, learner_id),
    }


def build_subject_catalog(
    repository: JsonRepository, learner_id: str = "default"
) -> dict[str, Any]:
    service = TutorService(repository)
    subjects = []
    for subject_id in repository.list_subject_ids():
        graph = repository.load_graph(subject_id)
        root = graph.get_concept(subject_id)
        progress = service.progress_report(subject_id, learner_id)
        next_item = service.next_concept(subject_id, learner_id)
        item: dict[str, Any] = {
            "id": subject_id,
            "name": root.name,
            "has_blueprint": repository.blueprint_exists(subject_id),
            "progress": progress["progress"],
            "mastered": progress["mastered"],
            "concepts": progress["concepts"],
            "current": service.status(subject_id, learner_id)["current"],
            "next": next_item["concept"],
        }
        if item["has_blueprint"]:
            blueprint = repository.load_blueprint(subject_id)
            item["goal"] = blueprint.scope.goal
            item["target_level"] = blueprint.scope.target_level
        else:
            item["goal"] = "尚未创建 Subject Blueprint"
            item["target_level"] = None
        subjects.append(item)
    return {"learner": learner_id, "subjects": subjects}


def _handler(repository: JsonRepository, default_subject: str | None, learner_id: str):
    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "AITutorDashboard/0.1"

        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/subjects":
                self._json_response(build_subject_catalog(repository, learner_id))
                return
            if path == "/api/state":
                requested = parse_qs(parsed.query).get("subject", [default_subject])[0]
                self._api_state(requested)
                return
            filename = "index.html" if path in {"/", "/index.html"} else path.lstrip("/")
            target = (STATIC_DIR / filename).resolve()
            if STATIC_DIR.resolve() not in target.parents and target != STATIC_DIR.resolve():
                self.send_error(404)
                return
            if not target.is_file():
                self.send_error(404)
                return
            content = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPES.get(target.suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def _api_state(self, requested_subject: str | None) -> None:
            try:
                if requested_subject is None:
                    raise ValueError("no subjects are available")
                repository.load_graph(requested_subject)
                value = build_dashboard_state(
                    TutorService(repository), requested_subject, learner_id
                )
                self._json_response(value)
                return
            except (KeyError, RuntimeError, ValueError) as exc:
                self._json_response({"error": str(exc)}, 404)

        def _json_response(self, value: Any, status: int = 200) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

    return DashboardHandler


def create_server(
    data_dir: str | Path,
    subject_id: str | None = None,
    learner_id: str = "default",
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    repository = JsonRepository(data_dir)
    available = repository.list_subject_ids()
    if subject_id is not None:
        repository.load_graph(subject_id)
    elif available:
        subject_id = next(
            (item for item in available if repository.blueprint_exists(item)),
            available[0],
        )
    return ThreadingHTTPServer((host, port), _handler(repository, subject_id, learner_id))


def serve_dashboard(
    data_dir: str | Path,
    subject_id: str | None = None,
    learner_id: str = "default",
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    server = create_server(data_dir, subject_id, learner_id, host, port)
    url = f"http://{host}:{server.server_port}/"
    if subject_id:
        url += f"?subject={quote(subject_id)}"
    print(json.dumps({"dashboard": url, "subject": subject_id, "mode": "workspace"}, ensure_ascii=False))
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
