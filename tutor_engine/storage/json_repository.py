"""Atomic JSON persistence for graphs and learner state."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from tutor_engine.graph import ConceptGraph
from tutor_engine.blueprint import SubjectBlueprint
from tutor_engine.learner import Learner
from tutor_engine.quiz import Quiz, QuizAttempt
from tutor_engine.session import LearningSession
from tutor_engine.storage.migrations import SchemaError, migrate_payload


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


class StorageError(RuntimeError):
    """Raised for missing, conflicting, or unsafe persisted resources."""


class JsonRepository:
    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        self.subjects_dir = self.data_dir / "subjects"
        self.learners_dir = self.data_dir / "learners"
        self.sessions_dir = self.data_dir / "sessions"
        self.blueprints_dir = self.data_dir / "blueprints"
        self.recoveries: list[str] = []

    @staticmethod
    def validate_id(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
            raise StorageError(
                f"{field_name} must contain only letters, numbers, '_' or '-'"
            )
        return value

    def subject_exists(self, subject_id: str) -> bool:
        return self._subject_path(subject_id).is_file()

    def blueprint_exists(self, subject_id: str) -> bool:
        return self._blueprint_path(subject_id).is_file()

    def list_subject_ids(self) -> tuple[str, ...]:
        if not self.subjects_dir.is_dir():
            return ()
        values = []
        for path in self.subjects_dir.glob("*.json"):
            if path.name.endswith(".json.bak"):
                continue
            subject_id = path.stem
            if SAFE_ID.fullmatch(subject_id):
                values.append(subject_id)
        return tuple(sorted(values))

    def save_graph(self, graph: ConceptGraph, *, overwrite: bool = True) -> None:
        path = self._subject_path(graph.subject_id)
        if path.exists() and not overwrite:
            raise StorageError(f"subject already exists: {graph.subject_id}")
        graph.validate_graph()
        self._atomic_write(path, graph.to_dict())

    def save_blueprint(
        self, blueprint: SubjectBlueprint, *, overwrite: bool = False
    ) -> None:
        path = self._blueprint_path(blueprint.subject_id)
        if path.exists() and not overwrite:
            raise StorageError(f"blueprint already exists: {blueprint.subject_id}")
        self._atomic_write(path, blueprint.to_dict())

    def load_blueprint(self, subject_id: str) -> SubjectBlueprint:
        path = self._blueprint_path(subject_id)
        if not path.is_file():
            raise StorageError(f"blueprint not found: {subject_id}")
        return SubjectBlueprint.from_dict(self._read(path, "blueprint"))

    def load_graph(self, subject_id: str) -> ConceptGraph:
        path = self._subject_path(subject_id)
        if not path.is_file():
            raise StorageError(f"subject not found: {subject_id}")
        return ConceptGraph.from_dict(self._read(path, "graph"))

    def save_learner(self, subject_id: str, learner: Learner) -> None:
        self.validate_id(subject_id, "subject_id")
        path = self._learner_path(learner.learner_id, subject_id)
        self._atomic_write(path, learner.to_dict())

    def load_learner(self, subject_id: str, learner_id: str = "default") -> Learner:
        path = self._learner_path(learner_id, subject_id)
        if not path.is_file():
            return Learner(learner_id)
        return Learner.from_dict(self._read(path, "learner"))

    def save_quiz(self, quiz: Quiz, learner_id: str = "default") -> None:
        path = self._session_path(
            learner_id, quiz.subject_id, "quizzes", quiz.id
        )
        if path.exists():
            raise StorageError(f"quiz already exists: {quiz.id}")
        self._atomic_write(path, quiz.to_dict())

    def load_quiz(
        self, subject_id: str, quiz_id: str, learner_id: str = "default"
    ) -> Quiz:
        path = self._session_path(learner_id, subject_id, "quizzes", quiz_id)
        if not path.is_file():
            raise StorageError(f"quiz not found: {quiz_id}")
        return Quiz.from_dict(self._read(path, "quiz"))

    def save_attempt(self, attempt: QuizAttempt) -> None:
        path = self._session_path(
            attempt.learner_id, attempt.subject_id, "attempts", attempt.id
        )
        if path.exists():
            raise StorageError(f"attempt already exists: {attempt.id}")
        self._atomic_write(path, attempt.to_dict())

    def save_learning_session(self, session: LearningSession) -> None:
        path = self._session_path(
            session.learner_id, session.subject_id, "learning_sessions", session.id
        )
        self._atomic_write(path, session.to_dict())

    def load_learning_session(
        self, subject_id: str, session_id: str, learner_id: str = "default"
    ) -> LearningSession:
        path = self._session_path(
            learner_id, subject_id, "learning_sessions", session_id
        )
        if not path.is_file():
            raise StorageError(f"learning session not found: {session_id}")
        return LearningSession.from_dict(self._read(path, "session"))

    def list_learning_sessions(
        self, subject_id: str, learner_id: str = "default"
    ) -> tuple[LearningSession, ...]:
        directory = self._session_path(
            learner_id, subject_id, "learning_sessions", "placeholder"
        ).parent
        if not directory.is_dir():
            return ()
        sessions = [
            LearningSession.from_dict(self._read(path, "session"))
            for path in directory.glob("*.json")
        ]
        return tuple(sorted(sessions, key=lambda item: (item.started_at, item.id)))

    def list_attempts(
        self, subject_id: str, learner_id: str = "default"
    ) -> tuple[Mapping[str, Any], ...]:
        directory = self._session_path(
            learner_id, subject_id, "attempts", "placeholder"
        ).parent
        if not directory.is_dir():
            return ()
        attempts = [self._read(path, "attempt") for path in directory.glob("*.json")]
        return tuple(sorted(attempts, key=lambda item: (item.get("created_at", ""), item.get("id", ""))))

    def _subject_path(self, subject_id: str) -> Path:
        self.validate_id(subject_id, "subject_id")
        return self.subjects_dir / f"{subject_id}.json"

    def _blueprint_path(self, subject_id: str) -> Path:
        self.validate_id(subject_id, "subject_id")
        return self.blueprints_dir / f"{subject_id}.json"

    def _learner_path(self, learner_id: str, subject_id: str) -> Path:
        self.validate_id(learner_id, "learner_id")
        self.validate_id(subject_id, "subject_id")
        return self.learners_dir / learner_id / f"{subject_id}.json"

    def _session_path(
        self, learner_id: str, subject_id: str, category: str, item_id: str
    ) -> Path:
        self.validate_id(learner_id, "learner_id")
        self.validate_id(subject_id, "subject_id")
        self.validate_id(category, "category")
        self.validate_id(item_id, "item_id")
        return self.sessions_dir / learner_id / subject_id / category / f"{item_id}.json"

    def _read(self, path: Path, kind: str) -> Mapping[str, Any]:
        primary_error: Exception | None = None
        try:
            return self._read_one(path, kind)
        except (OSError, json.JSONDecodeError, SchemaError, StorageError) as exc:
            primary_error = exc
        backup = path.with_suffix(path.suffix + ".bak")
        if backup.is_file():
            try:
                value = self._read_one(backup, kind)
                recovered = str(path)
                if recovered not in self.recoveries:
                    self.recoveries.append(recovered)
                return value
            except (OSError, json.JSONDecodeError, SchemaError, StorageError):
                pass
        raise StorageError(f"cannot read valid {kind} JSON from {path}") from primary_error

    @staticmethod
    def _read_one(path: Path, kind: str) -> Mapping[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise StorageError(f"expected a JSON object in {path}")
        return migrate_payload(value, kind)

    @staticmethod
    def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = handle.name
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            if path.is_file():
                shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
            os.replace(temporary, path)
        except OSError as exc:
            raise StorageError(f"cannot write {path}") from exc
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
