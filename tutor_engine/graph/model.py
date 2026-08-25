"""JSON-friendly models for the shared concept graph.

The graph contains objective concept metadata and relations only. Learner-specific
mastery and learning state belong to the learner model introduced later.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Literal, Mapping, get_args


RelationType = Literal[
    "prerequisite",
    "related_to",
    "part_of",
    "applied_in",
    "extends",
    "contrasts_with",
]
RELATION_TYPES = frozenset(get_args(RelationType))


class GraphValidationError(ValueError):
    """Raised when a graph mutation would leave the graph invalid."""


def _require_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise GraphValidationError(f"{field_name} must be a non-empty string")


def _require_unit_interval(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GraphValidationError(f"{field_name} must be a number")
    if not 0.0 <= float(value) <= 1.0:
        raise GraphValidationError(f"{field_name} must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class Concept:
    id: str
    name: str
    description: str = ""
    difficulty: int = 1
    importance: float = 0.5
    depth: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_identifier(self.id, "concept.id")
        _require_identifier(self.name, "concept.name")
        if isinstance(self.difficulty, bool) or not isinstance(self.difficulty, int):
            raise GraphValidationError("concept.difficulty must be an integer")
        if not 1 <= self.difficulty <= 5:
            raise GraphValidationError("concept.difficulty must be between 1 and 5")
        _require_unit_interval(self.importance, "concept.importance")
        if isinstance(self.depth, bool) or not isinstance(self.depth, int) or self.depth < 0:
            raise GraphValidationError("concept.depth must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Concept:
        return cls(**dict(data))


@dataclass(frozen=True, slots=True)
class Relation:
    id: str
    source: str
    target: str
    type: RelationType
    strength: float = 1.0
    threshold: float = 0.8
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_identifier(self.id, "relation.id")
        _require_identifier(self.source, "relation.source")
        _require_identifier(self.target, "relation.target")
        if self.source == self.target:
            raise GraphValidationError("a relation cannot reference the same concept")
        if self.type not in RELATION_TYPES:
            raise GraphValidationError(f"unsupported relation type: {self.type!r}")
        _require_unit_interval(self.strength, "relation.strength")
        _require_unit_interval(self.threshold, "relation.threshold")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Relation:
        return cls(**dict(data))


class ConceptGraph:
    """Validated in-memory graph with JSON-compatible serialization."""

    def __init__(
        self,
        subject_id: str,
        concepts: Iterable[Concept] = (),
        relations: Iterable[Relation] = (),
    ) -> None:
        _require_identifier(subject_id, "subject_id")
        self.subject_id = subject_id
        self._concepts: dict[str, Concept] = {}
        self._relations: dict[str, Relation] = {}
        for concept in concepts:
            self.add_concept(concept)
        for relation in relations:
            self.add_relation(relation)
        self.validate_graph()

    @property
    def concepts(self) -> tuple[Concept, ...]:
        return tuple(self._concepts.values())

    @property
    def relations(self) -> tuple[Relation, ...]:
        return tuple(self._relations.values())

    def add_concept(self, concept: Concept) -> None:
        if concept.id in self._concepts:
            raise GraphValidationError(f"duplicate concept id: {concept.id}")
        self._concepts[concept.id] = concept

    def add_relation(self, relation: Relation) -> None:
        if relation.id in self._relations:
            raise GraphValidationError(f"duplicate relation id: {relation.id}")
        if relation.source not in self._concepts:
            raise GraphValidationError(f"unknown relation source: {relation.source}")
        if relation.target not in self._concepts:
            raise GraphValidationError(f"unknown relation target: {relation.target}")
        self._relations[relation.id] = relation
        try:
            self.validate_graph()
        except GraphValidationError:
            del self._relations[relation.id]
            raise

    def get_concept(self, concept_id: str) -> Concept:
        try:
            return self._concepts[concept_id]
        except KeyError as exc:
            raise KeyError(f"unknown concept: {concept_id}") from exc

    def get_prerequisites(self, concept_id: str) -> tuple[Concept, ...]:
        self.get_concept(concept_id)
        ids = {
            relation.source
            for relation in self._relations.values()
            if relation.type == "prerequisite" and relation.target == concept_id
        }
        return tuple(concept for key, concept in self._concepts.items() if key in ids)

    def get_dependents(self, concept_id: str) -> tuple[Concept, ...]:
        self.get_concept(concept_id)
        ids = {
            relation.target
            for relation in self._relations.values()
            if relation.type == "prerequisite" and relation.source == concept_id
        }
        return tuple(concept for key, concept in self._concepts.items() if key in ids)

    def validate_graph(self) -> None:
        for relation in self._relations.values():
            if relation.source not in self._concepts or relation.target not in self._concepts:
                raise GraphValidationError(
                    f"relation {relation.id} references an unknown concept"
                )
        self._validate_prerequisite_acyclic()

    def _validate_prerequisite_acyclic(self) -> None:
        adjacency: dict[str, list[str]] = {key: [] for key in self._concepts}
        for relation in self._relations.values():
            if relation.type == "prerequisite":
                adjacency[relation.source].append(relation.target)

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise GraphValidationError("prerequisite relations must be acyclic")
            if node in visited:
                return
            visiting.add(node)
            for target in adjacency[node]:
                visit(target)
            visiting.remove(node)
            visited.add(node)

        for concept_id in adjacency:
            visit(concept_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "subject_id": self.subject_id,
            "concepts": [concept.to_dict() for concept in self.concepts],
            "relations": [relation.to_dict() for relation in self.relations],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ConceptGraph:
        return cls(
            subject_id=data["subject_id"],
            concepts=(Concept.from_dict(item) for item in data.get("concepts", [])),
            relations=(Relation.from_dict(item) for item in data.get("relations", [])),
        )
