"""Deterministic MVLG selection over an existing Knowledge Graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from tutor_engine.graph import ConceptGraph


def _unit(value: Any, default: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True, slots=True)
class RoadmapConfig:
    goal_weight: float = 0.40
    importance_weight: float = 0.30
    leverage_weight: float = 0.30
    core_threshold: float = 0.70
    max_core_candidates: int = 25

    def __post_init__(self) -> None:
        weights = (self.goal_weight, self.importance_weight, self.leverage_weight)
        if any(not 0 <= item <= 1 for item in weights):
            raise ValueError("roadmap score weights must be between 0 and 1")
        if abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("roadmap score weights must sum to 1.0")
        if not 0 <= self.core_threshold <= 1:
            raise ValueError("core_threshold must be between 0 and 1")
        if not 1 <= self.max_core_candidates <= 25:
            raise ValueError("max_core_candidates must be between 1 and 25")

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> RoadmapConfig:
        raw = payload.get("selection_config", {})
        legacy_size = payload.get("backbone_size")
        if legacy_size is not None and (
            isinstance(legacy_size, bool) or not isinstance(legacy_size, int)
        ):
            raise ValueError("backbone_size must be an integer")
        # backbone_size is accepted for input compatibility, but MVLG membership
        # is threshold-driven rather than a fixed top-N selection.
        maximum = raw.get("max_core_candidates", 25)
        return cls(
            goal_weight=float(raw.get("goal_weight", 0.40)),
            importance_weight=float(raw.get("importance_weight", 0.30)),
            leverage_weight=float(raw.get("leverage_weight", 0.30)),
            core_threshold=float(raw.get("core_threshold", 0.70)),
            max_core_candidates=int(maximum),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_weight": self.goal_weight,
            "importance_weight": self.importance_weight,
            "leverage_weight": self.leverage_weight,
            "core_threshold": self.core_threshold,
            "max_core_candidates": self.max_core_candidates,
        }


@dataclass(frozen=True, slots=True)
class ConceptAnalysis:
    concept_id: str
    goal_relevance: float
    importance_score: float
    leverage_score: float
    core_score: float
    direct_dependents: int
    indirect_dependents: int
    downstream_reach: float
    topological_layer: int
    inclusion_type: str
    selection_reason: str


@dataclass(frozen=True, slots=True)
class RoadmapAnalysis:
    concepts: tuple[ConceptAnalysis, ...]
    selected_core_ids: frozenset[str]
    mvlg_ids: frozenset[str]
    prerequisite_edges: tuple[tuple[str, str], ...]
    config: RoadmapConfig


def _adjacency(graph: ConceptGraph) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    forward = {item.id: [] for item in graph.concepts}
    reverse = {item.id: [] for item in graph.concepts}
    for relation in graph.relations:
        if relation.type == "prerequisite":
            forward[relation.source].append(relation.target)
            reverse[relation.target].append(relation.source)
    return forward, reverse


def _descendants(source: str, forward: Mapping[str, list[str]]) -> set[str]:
    seen: set[str] = set()
    stack = list(forward[source])
    while stack:
        node = stack.pop()
        if node not in seen:
            seen.add(node)
            stack.extend(forward[node])
    return seen


def _closure(selected: set[str], reverse: Mapping[str, list[str]], root: str) -> set[str]:
    result = set(selected)
    stack = list(selected)
    while stack:
        node = stack.pop()
        for prerequisite in reverse[node]:
            if prerequisite != root and prerequisite not in result:
                result.add(prerequisite)
                stack.append(prerequisite)
    return result


def _layers(nodes: set[str], edges: tuple[tuple[str, str], ...]) -> dict[str, int]:
    prerequisites = {node: [] for node in nodes}
    for source, target in edges:
        prerequisites[target].append(source)
    memo: dict[str, int] = {}

    def visit(node: str) -> int:
        if node not in memo:
            memo[node] = max((visit(item) + 1 for item in prerequisites[node]), default=0)
        return memo[node]

    return {node: visit(node) for node in nodes}


def analyze_roadmap(graph: ConceptGraph, config: RoadmapConfig) -> RoadmapAnalysis:
    """Select high-value concepts, close prerequisites, and layer the MVLG DAG."""
    graph.validate_graph()
    forward, reverse = _adjacency(graph)
    candidates = [item for item in graph.concepts if item.id != graph.subject_id]
    descendant_sets = {item.id: _descendants(item.id, forward) for item in candidates}
    max_direct = max((len(forward[item.id]) for item in candidates), default=0)
    max_indirect = max((max(0, len(descendant_sets[item.id]) - len(forward[item.id])) for item in candidates), default=0)
    raw: dict[str, dict[str, float | int]] = {}
    for concept in candidates:
        direct = len(forward[concept.id])
        indirect = max(0, len(descendant_sets[concept.id]) - direct)
        direct_score = direct / max_direct if max_direct else 0.0
        indirect_score = indirect / max_indirect if max_indirect else 0.0
        leverage = direct_score * 0.4 + indirect_score * 0.6
        relevance = _unit(concept.metadata.get("goal_relevance"), concept.importance)
        core_score = (
            relevance * config.goal_weight
            + concept.importance * config.importance_weight
            + leverage * config.leverage_weight
        )
        raw[concept.id] = {
            "goal_relevance": relevance,
            "importance_score": float(concept.importance),
            "leverage_score": leverage,
            "core_score": core_score,
            "direct_dependents": direct,
            "indirect_dependents": indirect,
            "downstream_reach": len(descendant_sets[concept.id]) / max(1, len(candidates) - 1),
        }
    ranked = sorted(candidates, key=lambda item: (-float(raw[item.id]["core_score"]), item.id))
    selected = {
        item.id for item in ranked
        if float(raw[item.id]["core_score"]) >= config.core_threshold
    }
    selected = set(list(item.id for item in ranked if item.id in selected)[:config.max_core_candidates])
    if not selected and ranked:
        selected.add(ranked[0].id)
    mvlg = _closure(selected, reverse, graph.subject_id)
    edges = tuple(
        (relation.source, relation.target)
        for relation in graph.relations
        if relation.type == "prerequisite"
        and relation.source in mvlg
        and relation.target in mvlg
    )
    layers = _layers(mvlg, edges)
    analyses = []
    for concept in candidates:
        if concept.id not in mvlg:
            continue
        inclusion = "core" if concept.id in selected else "prerequisite"
        metrics = raw[concept.id]
        if inclusion == "core":
            reason = (
                f"core_score {float(metrics['core_score']):.2f} meets threshold "
                f"{config.core_threshold:.2f}"
            )
        else:
            dependents = sorted(item for item in forward[concept.id] if item in mvlg)
            reason = f"required prerequisite for {', '.join(dependents)}"
        analyses.append(ConceptAnalysis(
            concept_id=concept.id,
            goal_relevance=round(float(metrics["goal_relevance"]), 6),
            importance_score=round(float(metrics["importance_score"]), 6),
            leverage_score=round(float(metrics["leverage_score"]), 6),
            core_score=round(float(metrics["core_score"]), 6),
            direct_dependents=int(metrics["direct_dependents"]),
            indirect_dependents=int(metrics["indirect_dependents"]),
            downstream_reach=round(float(metrics["downstream_reach"]), 6),
            topological_layer=layers[concept.id],
            inclusion_type=inclusion,
            selection_reason=reason,
        ))
    return RoadmapAnalysis(
        concepts=tuple(sorted(analyses, key=lambda item: (item.topological_layer, -item.core_score, item.concept_id))),
        selected_core_ids=frozenset(selected),
        mvlg_ids=frozenset(mvlg),
        prerequisite_edges=edges,
        config=config,
    )
