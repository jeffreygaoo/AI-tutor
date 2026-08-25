"""Deterministic prerequisite and unlock decisions."""

from __future__ import annotations

from tutor_engine.graph import Concept, ConceptGraph
from tutor_engine.learner import Learner


class DependencyEngine:
    def __init__(self, graph: ConceptGraph, learner: Learner) -> None:
        self.graph = graph
        self.learner = learner

    def _prerequisite_relations(self, concept_id: str):
        self.graph.get_concept(concept_id)
        return tuple(
            relation
            for relation in self.graph.relations
            if relation.type == "prerequisite" and relation.target == concept_id
        )

    def is_available(self, concept_id: str) -> bool:
        return all(
            self.learner.get_mastery(relation.source).score >= relation.threshold
            for relation in self._prerequisite_relations(concept_id)
        )

    def is_locked(self, concept_id: str) -> bool:
        return not self.is_available(concept_id)

    def unlock(self, concept_id: str) -> bool:
        state = self.learner.get_or_create_concept(concept_id)
        # Unlock refreshes must never erase demonstrated mastery. A weakened
        # prerequisite can create a review need, but it does not rewrite history.
        if state.status == "mastered":
            return True
        if not self.is_available(concept_id):
            state.status = "locked"
            return False
        if state.status == "locked":
            state.status = "available"
        return True

    def refresh(self) -> None:
        for concept in self.graph.concepts:
            self.unlock(concept.id)

    def get_available_concepts(self) -> tuple[Concept, ...]:
        self.refresh()
        return tuple(
            concept
            for concept in self.graph.concepts
            if self.learner.get_or_create_concept(concept.id).status
            in {"available", "learning", "weak", "familiar"}
        )
