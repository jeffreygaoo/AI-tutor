# Progressive graph expansion

Read the existing graph before expanding. Add only the neighborhood needed for
the current goal or next diagnostic; the engine rejects batches over 20 concepts.
Every new node must connect to the requested anchor, directly or through another
node in the same batch. Keep prerequisite direction as `source prerequisite ->
target dependent`.

Write an expansion JSON object and call:

```text
ai-tutor expand SUBJECT --anchor CONCEPT --input FILE.json
```

Shape:

```json
{
  "concepts": [
    {
      "id": "statistics",
      "name": "Statistics",
      "description": "...",
      "difficulty": 2,
      "importance": 0.9,
      "depth": 1,
      "metadata": {"goal_relevance": 0.9, "expandable": true}
    }
  ],
  "relations": [
    {
      "id": "statistics_to_regression",
      "source": "statistics",
      "target": "regression",
      "type": "prerequisite",
      "strength": 0.9,
      "threshold": 0.75
    }
  ]
}
```

Allowed relation types: `prerequisite`, `related_to`, `part_of`, `applied_in`,
`extends`, `contrasts_with`. Use stable ASCII identifiers. Do not duplicate known
concepts or create a complete subject graph upfront. The engine validates the full
batch and preserves the previous graph on failure.
