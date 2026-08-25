"""Deterministic next-concept selection for the learning graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from tutor_engine.curriculum.unlock import DependencyEngine
from tutor_engine.graph import Concept, ConceptGraph
from tutor_engine.learner import Learner


@dataclass(frozen=True, slots=True)
class ConceptSelection:
    concept: str | None
    reason: str
    priority: float | None = None
    factors: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CurriculumPlanner:
    """Rank available concepts with a compact, explainable V0.1 rule."""

    def __init__(self, graph: ConceptGraph, learner: Learner) -> None:
        self.graph = graph
        self.learner = learner
        self.dependencies = DependencyEngine(graph, learner)

    def next_concept(
        self, allowed_concept_ids: set[str] | None = None
    ) -> ConceptSelection:
        candidates = self.dependencies.get_available_concepts()
        if allowed_concept_ids is not None:
            candidates = tuple(
                concept for concept in candidates if concept.id in allowed_concept_ids
            )
        if not candidates:
            return ConceptSelection(
                concept=None,
                reason="No unlocked, unmastered concept is currently available.",
            )

        ranked = [(self._priority(concept), concept) for concept in candidates]
        # Stable deterministic tie-break: priority, shallower depth, then concept id.
        factors, selected = min(
            ranked,
            key=lambda item: (-item[0]["priority"], item[1].depth, item[1].id),
        )
        reason = (
            f"Selected {selected.name}: goal relevance={factors['goal_relevance']:.2f}, "
            f"importance={factors['importance']:.2f}, prerequisite value="
            f"{factors['prerequisite_value']:.2f}, weakness={factors['weakness']:.2f}, "
            f"readiness={factors['readiness']:.2f}."
        )
        return ConceptSelection(
            concept=selected.id,
            reason=reason,
            priority=factors["priority"],
            factors=factors,
        )

    def _priority(self, concept: Concept) -> dict[str, float]:
        raw_relevance = concept.metadata.get("goal_relevance", concept.importance)
        if isinstance(raw_relevance, bool) or not isinstance(raw_relevance, (int, float)):
            raise ValueError(f"goal_relevance for {concept.id} must be a number")
        goal_relevance = max(0.0, min(1.0, float(raw_relevance)))
        def descendant_count(source: str) -> int:
            seen: set[str] = set()
            stack = [item.id for item in self.graph.get_dependents(source)]
            while stack:
                node = stack.pop()
                if node not in seen:
                    seen.add(node)
                    stack.extend(item.id for item in self.graph.get_dependents(node))
            return len(seen)

        counts = {item.id: descendant_count(item.id) for item in self.graph.concepts}
        maximum = max(counts.values(), default=0)
        prerequisite_value = counts[concept.id] / maximum if maximum else 0.0
        state = self.learner.get_or_create_concept(concept.id)
        weakness = 1.0 - state.mastery.score
        readiness = 1.0
        priority = (
            goal_relevance * 0.30
            + concept.importance * 0.20
            + prerequisite_value * 0.25
            + weakness * 0.15
            + readiness * 0.10
        )
        return {
            "priority": round(priority, 6),
            "goal_relevance": goal_relevance,
            "importance": float(concept.importance),
            "prerequisite_value": prerequisite_value,
            "weakness": weakness,
            "readiness": readiness,
        }
