# Quiz and assessment protocol

Generate a concept-specific quiz with at least one question of each type: `recall`,
`understanding`, `application`, and `transfer`. Make the transfer item meaningfully
different from the teaching example. Rubrics describe the evidence required; do
not expose them before the learner answers.

Register the quiz:

```text
ai-tutor quiz-register --input QUIZ.json
```

```json
{
  "id": "quiz_probability_01",
  "subject_id": "machine_learning",
  "concept_id": "probability",
  "purpose": "diagnostic",
  "questions": [
    {
      "id": "q1",
      "type": "recall",
      "prompt": "...",
      "rubric": "...",
      "difficulty": 2
    }
  ]
}
```

Purpose is `diagnostic`, `learning`, or `review`. Collect every answer before
submission. Assess each answer against its rubric and provide concise reasoning.
Record a misconception only for a specific, reusable wrong mental model, not for
an omission, typo, vague response, or generic wrong answer.

Submit an object containing exactly all question IDs:

```text
ai-tutor quiz-submit SUBJECT --quiz QUIZ_ID --input RESULT.json
```

```json
{
  "answers": {"q1": "learner answer"},
  "assessments": [
    {
      "question_id": "q1",
      "score": 0.7,
      "reasoning": "Matches the definition but misses the boundary case.",
      "misconceptions": [
        {
          "id": "equiprobable_outcomes",
          "description": "Assumes all listed outcomes are equally likely.",
          "severity": 0.8
        }
      ]
    }
  ]
}
```

The engine rejects incomplete or duplicate assessments. It—not the language model—
computes the final mastery state, unlocks nodes, schedules reviews, and chooses the
next concept.
