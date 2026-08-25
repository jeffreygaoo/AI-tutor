# Subject Blueprint protocol

Use a Blueprint to give the learner a global but coarse view before detailed
teaching. It contains a goal-bounded Scope, 5–10 landscape sections with roughly
20–60 total coarse concepts, an Engine-selected core backbone, and 3–10 optional
advancement directions. Do not claim exhaustive coverage of an open domain.

First create the Subject root, then write a Blueprint JSON object and call:

```text
ai-tutor blueprint-create SUBJECT --input BLUEPRINT.json
```

Required shape:

```json
{
  "scope": {
    "goal": "Build a tabular classification project",
    "target_level": "practical_intermediate",
    "included": ["supervised_learning", "model_evaluation"],
    "excluded": ["reinforcement_learning"],
    "weekly_hours": 5
  },
  "landscape": {
    "concepts": [
      {
        "id": "generalization",
        "name": "Generalization",
        "description": "Performance on unseen data.",
        "difficulty": 2,
        "importance": 1.0,
        "depth": 2,
        "metadata": {
          "scope_tags": ["model_evaluation"],
          "goal_relevance": 1.0,
          "transfer_value": 1.0,
          "mental_model_value": 1.0,
          "expandable": true
        }
      }
    ],
    "relations": [],
    "sections": [
      {
        "id": "evaluation",
        "name": "Model Evaluation",
        "description": "Reason about reliable performance.",
        "concept_ids": ["generalization"]
      }
    ]
  },
  "backbone_size": 12,
  "advanced_directions": [
    {
      "id": "deep_learning",
      "name": "Deep Learning",
      "description": "Learn representation-based models.",
      "entry_concept_ids": ["generalization"],
      "in_scope": false
    }
  ]
}
```

The preferred V0.1 input separates Goal from landscape Scope. Legacy `scope.goal`,
`scope.target_level`, `scope.weekly_hours`, and `backbone_size` remain accepted:

```json
{
  "goal": {
    "id": "goal_ml_project",
    "subject_id": "machine_learning",
    "description": "Independently build basic ML projects",
    "target_level": "intermediate",
    "orientation": "practical",
    "time_budget": {"hours_per_week": 5, "target_months": 6}
  },
  "scope": {
    "included": ["supervised_learning", "model_evaluation"],
    "excluded": ["reinforcement_learning"]
  },
  "selection_config": {
    "goal_weight": 0.4,
    "importance_weight": 0.3,
    "leverage_weight": 0.3,
    "core_threshold": 0.7,
    "max_core_candidates": 25
  }
}
```

Every landscape concept requires one or more `scope_tags`; excluded tags are hard
errors. Add reliable prerequisite edges in `source prerequisite -> target dependent`
direction and use `part_of` for taxonomy. Connect every new concept to the Subject
root, directly or through the submitted batch.

The language model supplies structured `goal_relevance` estimates from 0 to 1;
the Concept supplies `importance`. The Engine computes direct and indirect
dependents, then normalizes leverage using `0.4 * direct + 0.6 * indirect`.
Core Score defaults to `0.4 * goal relevance + 0.3 * importance + 0.3 * leverage`.
Weights and the default `0.70` threshold are configurable and weights must sum to
1. Do not submit `core_backbone`: the Engine selects threshold-qualified concepts,
recursively adds all prerequisites, validates the DAG, and calculates topological
layers. The resulting MVLG is the roadmap skeleton. `backbone_size` is deprecated
and no longer forces a top-N selection.

After creation:

```text
ai-tutor blueprint SUBJECT
ai-tutor roadmap SUBJECT
ai-tutor directions SUBJECT
```

For a human-readable Blueprint visualization, put the format option before the
command. Its default composition is a scope summary, Mermaid landscape mind map,
core-backbone score table, Mermaid prerequisite graph, and collapsible advancement
directions:

```text
ai-tutor --format markdown blueprint SUBJECT
ai-tutor --format markdown roadmap SUBJECT
ai-tutor --format markdown directions SUBJECT
```

The Blueprint is broad and coarse. Roadmap is dynamically recomputed from the
current Knowledge Graph, persisted Goal/configuration, and learner Mastery; it is
not a permanently fixed list. `roadmap` and `next` are separate views. When learning enters an expandable concept,
use the ordinary graph expansion protocol to add at most 20 detailed nodes around
that anchor. Scope exclusions continue to guide generation; do not add an excluded
direction to the active learning graph.
