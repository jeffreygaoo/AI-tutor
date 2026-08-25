"""JSON command-line client for Tutor Engine V0.1."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tutor_engine.service import TutorService  # noqa: E402
from tutor_engine.presentation import render_markdown  # noqa: E402
from tutor_engine.storage import JsonRepository  # noqa: E402
from tutor_engine.version import __version__  # noqa: E402
from tutor_engine.dashboard import serve_dashboard  # noqa: E402


def configure_utf8_streams() -> None:
    """Make the JSON protocol encoding deterministic across Windows consoles."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-tutor")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("AI_TUTOR_DATA_DIR", PROJECT_ROOT / "data")),
    )
    parser.add_argument("--learner", default="default")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="output format; markdown is supported by blueprint, roadmap, and directions",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create")
    create.add_argument("subject")
    create.add_argument("--name", required=True)

    for command in ("status", "graph", "next", "review", "session-start", "session-end", "history", "progress", "doctor", "blueprint", "roadmap", "directions"):
        child = commands.add_parser(command)
        child.add_argument("subject")

    learn = commands.add_parser("learn")
    learn.add_argument("subject")
    learn.add_argument("--concept")

    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("subject")
    evaluate.add_argument("--concept", required=True)
    for option in (
        "concept_quiz", "practice", "application", "transfer", "delayed_review"
    ):
        evaluate.add_argument(f"--{option.replace('_', '-')}", type=float)

    expand = commands.add_parser("expand")
    expand.add_argument("subject")
    expand.add_argument("--anchor", required=True)
    expand.add_argument("--input", required=True)

    blueprint_create = commands.add_parser("blueprint-create")
    blueprint_create.add_argument("subject")
    blueprint_create.add_argument("--input", required=True)

    dashboard = commands.add_parser("dashboard")
    dashboard.add_argument("subject", nargs="?")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8765)
    dashboard.add_argument("--no-open", action="store_true")

    register = commands.add_parser("quiz-register")
    register.add_argument("--input", required=True)

    submit = commands.add_parser("quiz-submit")
    submit.add_argument("subject")
    submit.add_argument("--quiz", required=True)
    submit.add_argument("--input", required=True)
    return parser


def read_json_object(source: str) -> dict:
    if source == "-":
        value = json.load(sys.stdin)
    else:
        with Path(source).open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {source}")
    return value


def run(argv: Sequence[str] | None = None) -> dict:
    args = build_parser().parse_args(argv)
    service = TutorService(JsonRepository(args.data_dir))
    if args.command == "create":
        return service.create_subject(args.subject, args.name, args.learner)
    if args.command == "status":
        return service.status(args.subject, args.learner)
    if args.command == "graph":
        return service.graph_view(args.subject, args.learner)
    if args.command == "next":
        return service.next_concept(args.subject, args.learner)
    if args.command == "learn":
        return service.learn(args.subject, args.learner, args.concept)
    if args.command == "review":
        return service.review(args.subject, args.learner)
    if args.command == "session-start":
        return service.start_session(args.subject, args.learner)
    if args.command == "session-end":
        return service.end_session(args.subject, args.learner)
    if args.command == "history":
        return service.session_history(args.subject, args.learner)
    if args.command == "progress":
        return service.progress_report(args.subject, args.learner)
    if args.command == "doctor":
        return service.doctor(args.subject, args.learner)
    if args.command == "blueprint":
        return service.blueprint_view(args.subject, args.learner)
    if args.command == "roadmap":
        return service.roadmap(args.subject, args.learner)
    if args.command == "directions":
        return service.directions(args.subject, args.learner)
    if args.command == "blueprint-create":
        return service.create_blueprint(
            args.subject, read_json_object(args.input), args.learner
        )
    if args.command == "expand":
        return service.expand_subject(
            args.subject, args.anchor, read_json_object(args.input), args.learner
        )
    if args.command == "quiz-register":
        return service.register_quiz(read_json_object(args.input), args.learner)
    if args.command == "quiz-submit":
        payload = read_json_object(args.input)
        return service.submit_quiz(
            args.subject,
            args.quiz,
            payload.get("answers", {}),
            payload.get("assessments", []),
            args.learner,
        )
    evidence = {
        key: getattr(args, key)
        for key in (
            "concept_quiz", "practice", "application", "transfer", "delayed_review"
        )
        if getattr(args, key) is not None
    }
    return service.evaluate(
        args.subject, args.concept, evidence, learner_id=args.learner
    )


def main(argv: Sequence[str] | None = None) -> int:
    configure_utf8_streams()
    parsed_argv = list(argv) if argv is not None else sys.argv[1:]
    args = build_parser().parse_args(parsed_argv)
    if args.command == "dashboard":
        try:
            serve_dashboard(
                args.data_dir,
                args.subject,
                args.learner,
                args.host,
                args.port,
                not args.no_open,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
            return 1
        return 0
    markdown_commands = {"blueprint", "roadmap", "directions"}
    if args.format == "markdown" and args.command not in markdown_commands:
        print(
            json.dumps(
                {"error": f"Markdown output is not supported for command: {args.command}"},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    try:
        result = run(parsed_argv)
    except (KeyError, RuntimeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    if args.format == "markdown":
        print(render_markdown(args.command, result), end="")
        return 0
    compact = "--compact" in parsed_argv
    print(json.dumps(result, ensure_ascii=False, indent=None if compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
