"""Validated, rollback-safe progressive graph expansion."""

from __future__ import annotations

from collections.abc import Sequence

from tutor_engine.graph.model import Concept, ConceptGraph, GraphValidationError, Relation


def expand_graph(
    graph: ConceptGraph,
    anchor_concept_id: str,
    concepts: Sequence[Concept],
    relations: Sequence[Relation],
    *,
    max_new_concepts: int = 20,
) -> ConceptGraph:
    """Return an expanded copy; leave the original unchanged on any failure."""
    graph.get_concept(anchor_concept_id)
    if not concepts:
        raise GraphValidationError("expansion must add at least one concept")
    if len(concepts) > max_new_concepts:
        raise GraphValidationError(
            f"expansion exceeds the {max_new_concepts}-concept batch limit"
        )
    existing_ids = {item.id for item in graph.concepts}
    new_ids = {item.id for item in concepts}
    if len(new_ids) != len(concepts):
        raise GraphValidationError("expansion concept ids must be unique")
    overlap = existing_ids & new_ids
    if overlap:
        raise GraphValidationError(f"expansion duplicates concepts: {sorted(overlap)}")

    candidate = ConceptGraph.from_dict(graph.to_dict())
    for concept in concepts:
        candidate.add_concept(concept)
    for relation in relations:
        candidate.add_relation(relation)

    reachable = {anchor_concept_id}
    changed = True
    while changed:
        changed = False
        for relation in candidate.relations:
            if relation.source in reachable and relation.target not in reachable:
                reachable.add(relation.target)
                changed = True
            if relation.target in reachable and relation.source not in reachable:
                reachable.add(relation.source)
                changed = True
    disconnected = new_ids - reachable
    if disconnected:
        raise GraphValidationError(
            f"expanded concepts must connect to anchor {anchor_concept_id}: "
            f"{sorted(disconnected)}"
        )
    candidate.validate_graph()
    return candidate
