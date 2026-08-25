"""JSON models for a goal-bounded subject blueprint."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


class BlueprintValidationError(ValueError):
    """Raised when a blueprint is incomplete or inconsistent."""


def _text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise BlueprintValidationError(f"{field_name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class SubjectScope:
    goal: str
    target_level: str
    included: tuple[str, ...]
    excluded: tuple[str, ...] = ()
    weekly_hours: float | None = None
    goal_id: str | None = None
    orientation: str = "general"
    target_months: float | None = None

    def __post_init__(self) -> None:
        _text(self.goal, "scope.goal")
        _text(self.target_level, "scope.target_level")
        if not self.included:
            raise BlueprintValidationError("scope.included must not be empty")
        overlap = set(self.included) & set(self.excluded)
        if overlap:
            raise BlueprintValidationError(
                f"scope cannot include and exclude the same areas: {sorted(overlap)}"
            )
        if self.weekly_hours is not None and self.weekly_hours <= 0:
            raise BlueprintValidationError("scope.weekly_hours must be positive")
        if self.target_months is not None and self.target_months <= 0:
            raise BlueprintValidationError("scope.target_months must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SubjectScope:
        budget = data.get("time_budget", {})
        return cls(
            goal=data.get("goal", data.get("description")),
            target_level=data["target_level"],
            included=tuple(data.get("included", [])),
            excluded=tuple(data.get("excluded", [])),
            weekly_hours=data.get("weekly_hours", budget.get("hours_per_week")),
            goal_id=data.get("goal_id", data.get("id")),
            orientation=data.get("orientation", "general"),
            target_months=data.get("target_months", budget.get("target_months")),
        )


@dataclass(frozen=True, slots=True)
class LandscapeSection:
    id: str
    name: str
    description: str
    concept_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.id, "landscape_section.id")
        _text(self.name, "landscape_section.name")
        if not self.concept_ids:
            raise BlueprintValidationError("landscape section must contain concepts")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LandscapeSection:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            concept_ids=tuple(data.get("concept_ids", [])),
        )


@dataclass(frozen=True, slots=True)
class BackboneConcept:
    concept_id: str
    leverage_score: float
    downstream_reach: float
    path_betweenness: float
    goal_relevance: float
    transfer_value: float
    mental_model_value: float
    learning_cost: float
    stage: int
    importance_score: float = 0.0
    core_score: float = 0.0
    direct_dependents: int = 0
    indirect_dependents: int = 0
    topological_layer: int = 0
    inclusion_type: str = "core"
    selection_reason: str = "legacy backbone selection"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BackboneConcept:
        value = dict(data)
        value.setdefault("importance_score", value.get("goal_relevance", 0.0))
        value.setdefault("core_score", value.get("leverage_score", 0.0))
        value.setdefault("direct_dependents", 0)
        value.setdefault("indirect_dependents", 0)
        value.setdefault("topological_layer", max(0, int(value.get("stage", 1)) - 1))
        value.setdefault("inclusion_type", "core")
        value.setdefault("selection_reason", "legacy backbone selection")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class AdvancementDirection:
    id: str
    name: str
    description: str
    entry_concept_ids: tuple[str, ...]
    in_scope: bool = False

    def __post_init__(self) -> None:
        _text(self.id, "direction.id")
        _text(self.name, "direction.name")
        if not self.entry_concept_ids:
            raise BlueprintValidationError("direction must define entry concepts")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AdvancementDirection:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            entry_concept_ids=tuple(data.get("entry_concept_ids", [])),
            in_scope=bool(data.get("in_scope", False)),
        )


@dataclass(frozen=True, slots=True)
class SubjectBlueprint:
    subject_id: str
    scope: SubjectScope
    landscape: tuple[LandscapeSection, ...]
    core_backbone: tuple[BackboneConcept, ...]
    advanced_directions: tuple[AdvancementDirection, ...]
    revision: int
    created_at: str
    updated_at: str
    selection_config: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "subject_id": self.subject_id,
            "scope": self.scope.to_dict(),
            "landscape": [item.to_dict() for item in self.landscape],
            "core_backbone": [item.to_dict() for item in self.core_backbone],
            "advanced_directions": [
                item.to_dict() for item in self.advanced_directions
            ],
            "revision": self.revision,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "selection_config": dict(self.selection_config or {}),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SubjectBlueprint:
        return cls(
            subject_id=data["subject_id"],
            scope=SubjectScope.from_dict(data["scope"]),
            landscape=tuple(
                LandscapeSection.from_dict(item) for item in data.get("landscape", [])
            ),
            core_backbone=tuple(
                BackboneConcept.from_dict(item)
                for item in data.get("core_backbone", [])
            ),
            advanced_directions=tuple(
                AdvancementDirection.from_dict(item)
                for item in data.get("advanced_directions", [])
            ),
            revision=data.get("revision", 1),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            selection_config=dict(data.get("selection_config", {})),
        )

    @staticmethod
    def timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
