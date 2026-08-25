"""JSON-friendly learner state kept separately from the objective graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping


LearningStatus = Literal["locked", "available", "learning", "weak", "familiar", "mastered"]


class LearnerValidationError(ValueError):
    """Raised when learner state is invalid."""


def _identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise LearnerValidationError(f"{field_name} must be a non-empty string")


def _unit_interval(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LearnerValidationError(f"{field_name} must be a number")
    if not 0.0 <= float(value) <= 1.0:
        raise LearnerValidationError(f"{field_name} must be between 0.0 and 1.0")


@dataclass(slots=True)
class Mastery:
    score: float = 0.0
    confidence: float = 0.0
    updated_at: str | None = None

    def __post_init__(self) -> None:
        _unit_interval(self.score, "mastery.score")
        _unit_interval(self.confidence, "mastery.confidence")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Mastery:
        return cls(**dict(data))


@dataclass(slots=True)
class ReviewState:
    stage: int = 0
    last_review: str | None = None
    next_review: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.stage, bool) or not isinstance(self.stage, int) or self.stage < 0:
            raise LearnerValidationError("review.stage must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReviewState:
        return cls(**dict(data))


@dataclass(slots=True)
class Misconception:
    id: str
    description: str
    severity: float = 0.5
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    resolved: bool = False
    resolved_at: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.id, "misconception.id")
        _identifier(self.description, "misconception.description")
        _unit_interval(self.severity, "misconception.severity")
        if self.resolved and not self.resolved_at:
            raise LearnerValidationError("resolved misconception requires resolved_at")

    def resolve(self, at: str | None = None) -> None:
        self.resolved = True
        self.resolved_at = at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Misconception:
        return cls(**dict(data))


@dataclass(slots=True)
class LearnerConcept:
    concept_id: str
    status: LearningStatus = "locked"
    mastery: Mastery = field(default_factory=Mastery)
    attempt_count: int = 0
    last_learned: str | None = None
    misconceptions: list[Misconception] = field(default_factory=list)
    review: ReviewState = field(default_factory=ReviewState)

    def __post_init__(self) -> None:
        _identifier(self.concept_id, "learner_concept.concept_id")
        if self.status not in {
            "locked", "available", "learning", "weak", "familiar", "mastered"
        }:
            raise LearnerValidationError(f"unsupported learning status: {self.status!r}")
        if (
            isinstance(self.attempt_count, bool)
            or not isinstance(self.attempt_count, int)
            or self.attempt_count < 0
        ):
            raise LearnerValidationError("attempt_count must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "status": self.status,
            "mastery": self.mastery.to_dict(),
            "attempt_count": self.attempt_count,
            "last_learned": self.last_learned,
            "misconceptions": [item.to_dict() for item in self.misconceptions],
            "review": self.review.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LearnerConcept:
        return cls(
            concept_id=data["concept_id"],
            status=data.get("status", "locked"),
            mastery=Mastery.from_dict(data.get("mastery", {})),
            attempt_count=data.get("attempt_count", 0),
            last_learned=data.get("last_learned"),
            misconceptions=[
                Misconception.from_dict(item) for item in data.get("misconceptions", [])
            ],
            review=ReviewState.from_dict(data.get("review", {})),
        )


@dataclass(slots=True)
class Learner:
    learner_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
    concepts: dict[str, LearnerConcept] = field(default_factory=dict)
    active_session_id: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.learner_id, "learner.learner_id")

    def get_or_create_concept(self, concept_id: str) -> LearnerConcept:
        _identifier(concept_id, "concept_id")
        if concept_id not in self.concepts:
            self.concepts[concept_id] = LearnerConcept(concept_id)
        return self.concepts[concept_id]

    def get_mastery(self, concept_id: str) -> Mastery:
        return self.get_or_create_concept(concept_id).mastery

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "learner_id": self.learner_id,
            "preferences": self.preferences,
            "concepts": {
                concept_id: state.to_dict()
                for concept_id, state in self.concepts.items()
            },
            "active_session_id": self.active_session_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Learner:
        return cls(
            learner_id=data["learner_id"],
            preferences=dict(data.get("preferences", {})),
            concepts={
                concept_id: LearnerConcept.from_dict(state)
                for concept_id, state in data.get("concepts", {}).items()
            },
            active_session_id=data.get("active_session_id"),
        )
