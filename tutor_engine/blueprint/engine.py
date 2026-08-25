"""Build a validated landscape and select high-leverage backbone concepts."""

from __future__ import annotations

from typing import Any, Mapping

from tutor_engine.blueprint.model import (
    AdvancementDirection,
    BackboneConcept,
    BlueprintValidationError,
    LandscapeSection,
    SubjectBlueprint,
    SubjectScope,
)
from tutor_engine.graph import Concept, ConceptGraph, Relation, expand_graph
from tutor_engine.roadmap import RoadmapConfig, analyze_roadmap


def _unit(value: Any, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(0.0, min(1.0, float(value)))


def build_blueprint(
    graph: ConceptGraph, payload: Mapping[str, Any]
) -> tuple[ConceptGraph, SubjectBlueprint]:
    scope_data = dict(payload.get("scope", {}))
    goal_data = payload.get("goal")
    if goal_data is not None:
        if not isinstance(goal_data, Mapping):
            raise BlueprintValidationError("goal must be an object")
        scope_data.update(goal_data)
        if "description" in goal_data:
            scope_data["goal"] = goal_data["description"]
        if "id" in goal_data:
            scope_data["goal_id"] = goal_data["id"]
        if isinstance(goal_data.get("time_budget"), Mapping):
            budget = goal_data["time_budget"]
            if "hours_per_week" in budget:
                scope_data["weekly_hours"] = budget["hours_per_week"]
            if "target_months" in budget:
                scope_data["target_months"] = budget["target_months"]
    if not scope_data:
        raise BlueprintValidationError("blueprint requires scope or goal")
    scope = SubjectScope.from_dict(scope_data)
    landscape_data = payload.get("landscape", {})
    new_concepts = [
        Concept.from_dict(item) for item in landscape_data.get("concepts", [])
    ]
    for concept in new_concepts:
        tags = concept.metadata.get("scope_tags")
        if not isinstance(tags, (list, tuple)) or not tags:
            raise BlueprintValidationError(
                f"landscape concept {concept.id} requires non-empty metadata.scope_tags"
            )
        excluded = set(tags) & set(scope.excluded)
        if excluded:
            raise BlueprintValidationError(
                f"concept {concept.id} violates excluded scope: {sorted(excluded)}"
            )
    relations = [
        Relation.from_dict(item) for item in landscape_data.get("relations", [])
    ]
    expanded = expand_graph(
        graph,
        graph.subject_id,
        new_concepts,
        relations,
        max_new_concepts=60,
    )
    graph_ids = {concept.id for concept in expanded.concepts}
    sections = tuple(
        LandscapeSection.from_dict(item)
        for item in landscape_data.get("sections", [])
    )
    if not sections:
        raise BlueprintValidationError("landscape must define sections")
    for section in sections:
        unknown = set(section.concept_ids) - graph_ids
        if unknown:
            raise BlueprintValidationError(
                f"section {section.id} references unknown concepts: {sorted(unknown)}"
            )
    directions = tuple(
        AdvancementDirection.from_dict(item)
        for item in payload.get("advanced_directions", [])
    )
    for direction in directions:
        unknown = set(direction.entry_concept_ids) - graph_ids
        if unknown:
            raise BlueprintValidationError(
                f"direction {direction.id} references unknown entry concepts: {sorted(unknown)}"
            )

    try:
        config = RoadmapConfig.from_payload(payload)
        analysis = analyze_roadmap(expanded, config)
    except (TypeError, ValueError) as exc:
        raise BlueprintValidationError(str(exc)) from exc
    concept_map = {concept.id: concept for concept in expanded.concepts}
    selected = tuple(
        BackboneConcept(
            concept_id=item.concept_id,
            leverage_score=item.leverage_score,
            downstream_reach=item.downstream_reach,
            path_betweenness=0.0,
            goal_relevance=item.goal_relevance,
            transfer_value=_unit(concept_map[item.concept_id].metadata.get("transfer_value"), 0.5),
            mental_model_value=_unit(concept_map[item.concept_id].metadata.get("mental_model_value"), 0.5),
            learning_cost=(concept_map[item.concept_id].difficulty - 1) / 4,
            stage=item.topological_layer + 1,
            importance_score=item.importance_score,
            core_score=item.core_score,
            direct_dependents=item.direct_dependents,
            indirect_dependents=item.indirect_dependents,
            topological_layer=item.topological_layer,
            inclusion_type=item.inclusion_type,
            selection_reason=item.selection_reason,
        )
        for item in analysis.concepts
    )
    now = SubjectBlueprint.timestamp()
    blueprint = SubjectBlueprint(
        subject_id=graph.subject_id,
        scope=scope,
        landscape=sections,
        core_backbone=tuple(selected),
        advanced_directions=directions,
        revision=1,
        created_at=now,
        updated_at=now,
        selection_config=config.to_dict(),
    )
    return expanded, blueprint
