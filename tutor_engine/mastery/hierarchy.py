"""Aggregate mastery from teachable child concepts into expanded topic nodes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from tutor_engine.graph import ConceptGraph
from tutor_engine.learner import Learner
from tutor_engine.mastery.evaluator import MasteryEvaluator


@dataclass(frozen=True, slots=True)
class TopicProgress:
    concept_id: str
    mastered_children: int
    total_children: int
    mastered_required_children: int
    required_children: int
    score: float
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HierarchyMasteryEvaluator:
    """Use ``child part_of -> parent`` edges as the objective topic hierarchy."""

    def children(self, graph: ConceptGraph) -> dict[str, tuple[str, ...]]:
        values: dict[str, list[str]] = {}
        for relation in graph.relations:
            # The Subject root is a graph anchor, never a teachable hierarchy child.
            # Ignore legacy root -> first-concept taxonomy edges as well.
            if relation.type == "part_of" and relation.source != graph.subject_id:
                values.setdefault(relation.target, []).append(relation.source)
        return {
            parent: tuple(sorted(set(child_ids)))
            for parent, child_ids in values.items()
        }

    def update(self, graph: ConceptGraph, learner: Learner) -> dict[str, TopicProgress]:
        children = self.children(graph)
        concept_map = {item.id: item for item in graph.concepts}
        summaries: dict[str, TopicProgress] = {}
        visiting: set[str] = set()

        def aggregate(parent_id: str) -> None:
            if parent_id in summaries:
                return
            if parent_id in visiting:
                raise ValueError("part_of relations must be acyclic for mastery aggregation")
            visiting.add(parent_id)
            child_ids = children.get(parent_id, ())
            for child_id in child_ids:
                if child_id in children:
                    aggregate(child_id)

            parent = concept_map[parent_id]
            should_aggregate = bool(child_ids) and (
                parent.metadata.get("node_type") == "topic"
                or parent.metadata.get("expansion_status") == "expanded"
                or (
                    parent.id != graph.subject_id
                    and parent.metadata.get("expandable", False)
                )
            )
            if should_aggregate:
                child_concepts = [concept_map[item] for item in child_ids]
                weights = [
                    float(item.metadata.get("mastery_weight", item.importance))
                    for item in child_concepts
                ]
                weights = [item if item > 0 else 1.0 for item in weights]
                states = [learner.get_or_create_concept(item.id) for item in child_concepts]
                total_weight = sum(weights)
                score = round(
                    sum(state.mastery.score * weight for state, weight in zip(states, weights))
                    / total_weight,
                    6,
                )
                confidence = round(
                    sum(state.mastery.confidence * weight for state, weight in zip(states, weights))
                    / total_weight,
                    6,
                )
                required = [
                    state
                    for item, state in zip(child_concepts, states)
                    if item.metadata.get("required", True)
                ]
                state = learner.get_or_create_concept(parent_id)
                has_evidence = any(
                    item.mastery.updated_at is not None or item.attempt_count > 0
                    for item in states
                )
                state.mastery.score = score
                state.mastery.confidence = confidence
                state.mastery.updated_at = max(
                    (item.mastery.updated_at for item in states if item.mastery.updated_at),
                    default=None,
                )
                if required and all(item.status == "mastered" for item in required) \
                        and score >= 0.8 and confidence >= 0.6:
                    state.status = "mastered"
                elif has_evidence:
                    state.status = MasteryEvaluator.status_for(score, confidence)
                summaries[parent_id] = TopicProgress(
                    concept_id=parent_id,
                    mastered_children=sum(item.status == "mastered" for item in states),
                    total_children=len(states),
                    mastered_required_children=sum(item.status == "mastered" for item in required),
                    required_children=len(required),
                    score=score,
                    confidence=confidence,
                )
            visiting.remove(parent_id)

        for parent_id in children:
            aggregate(parent_id)
        return summaries
