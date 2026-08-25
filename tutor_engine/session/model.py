"""Persistent learning sessions and their deterministic event history."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class SessionEvent:
    type: str
    at: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.type, str) or not self.type.strip():
            raise ValueError("event.type must be a non-empty string")
        parsed = datetime.fromisoformat(self.at)
        if parsed.tzinfo is None:
            raise ValueError("event.at must be timezone-aware")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SessionEvent:
        return cls(type=data["type"], at=data["at"], data=dict(data.get("data", {})))


@dataclass(slots=True)
class LearningSession:
    id: str
    subject_id: str
    learner_id: str
    started_at: str
    ended_at: str | None = None
    events: list[SessionEvent] = field(default_factory=list)

    def add_event(
        self, event_type: str, data: Mapping[str, Any] | None = None, *, at: str | None = None
    ) -> None:
        if self.ended_at is not None:
            raise ValueError("cannot append to an ended learning session")
        self.events.append(SessionEvent(event_type, at or utc_now(), dict(data or {})))

    def end(self, *, at: str | None = None) -> None:
        if self.ended_at is not None:
            raise ValueError("learning session has already ended")
        ended_at = at or utc_now()
        self.add_event("session_ended", at=ended_at)
        self.ended_at = ended_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "id": self.id,
            "subject_id": self.subject_id,
            "learner_id": self.learner_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LearningSession:
        return cls(
            id=data["id"],
            subject_id=data["subject_id"],
            learner_id=data["learner_id"],
            started_at=data["started_at"],
            ended_at=data.get("ended_at"),
            events=[SessionEvent.from_dict(item) for item in data.get("events", [])],
        )
