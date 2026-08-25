"""Policy for deciding when a coarse concept should be expanded before teaching."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from tutor_engine.graph.model import Concept, ConceptGraph


@dataclass(frozen=True, slots=True)
class ExpansionDecision:
    action: str
    anchor: str
    reason: str
    suggested_child_count: int
    max_child_count: int = 20

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExpansionPolicy:
    """Identify expandable concepts that have not received a detailed batch yet."""

    DEFAULT_CHILD_COUNT = 8
    MAX_CHILD_COUNT = 20

    @staticmethod
    def is_expanded(graph: ConceptGraph, concept: Concept) -> bool:
        return concept.metadata.get("expansion_status") == "expanded" or any(
            relation.type == "part_of"
            and relation.source != graph.subject_id
            and relation.target == concept.id
            for relation in graph.relations
        )

    def evaluate(self, graph: ConceptGraph, concept: Concept) -> ExpansionDecision | None:
        metadata = concept.metadata
        if concept.id == graph.subject_id:
            return None
        if not metadata.get("expandable", False):
            return None
        if metadata.get("leaf_teachable", False):
            return None
        if self.is_expanded(graph, concept):
            return None

        requested = metadata.get("suggested_child_count", self.DEFAULT_CHILD_COUNT)
        if isinstance(requested, bool) or not isinstance(requested, int):
            requested = self.DEFAULT_CHILD_COUNT
        requested = max(1, min(self.MAX_CHILD_COUNT, requested))
        explicit = metadata.get("expansion_required", False)
        action = "expansion_required" if explicit else "expansion_recommended"
        qualifier = "需要" if explicit else "建议"
        return ExpansionDecision(
            action=action,
            anchor=concept.id,
            reason=(
                f"“{concept.name}”仍是可展开的粗粒度主题，{qualifier}先生成下一层可教学、"
                "可评估的知识点，再进入正式学习。"
            ),
            suggested_child_count=requested,
        )
