---
name: ai-tutor
description: Build a goal-bounded subject landscape, core learning backbone, advancement directions, and personalized learning graph, then teach through diagnostic questions, interactive lessons, mastery updates, misconception remediation, and spaced review. Use when the user wants to map, start, continue, test, review, or inspect progress in an AI Tutor subject stored by this project.
---

# AI Tutor

Use the Python engine as the source of truth for graph, learner state, mastery,
unlocking, next-concept selection, attempts, and review dates. Use language-model
judgment for teaching and semantic answer assessment, then submit structured data
to the engine. Never infer persisted state from conversation memory.

Run commands from the repository root. Prefer `.venv/Scripts/ai-tutor.exe` on
Windows or `.venv/bin/ai-tutor` on POSIX when present; otherwise use the installed
`ai-tutor` command or an available Python 3 runtime with `scripts/tutor_cli.py`.
Every command returns JSON by default. For a human-readable Blueprint, roadmap, or
directions view, pass `--format markdown` before the command. The Blueprint view
uses a Mermaid mind map for breadth, a table for backbone scores, a directed graph
for prerequisites, and collapsible advancement details. Rendering does not change
persisted data. If a command fails, explain the error and do not invent
or manually patch the resulting learning state.

## Route the request

- New subject: create its root, generate a goal-bounded coarse landscape through
  `blueprint-create`, inspect the algorithm-selected backbone, then run a short
  diagnostic before choosing the first lesson. Read
  [blueprint-rules.md](references/blueprint-rules.md).
- Landscape, roadmap, or directions request: use `blueprint`, `roadmap`, or
  `directions`. Present landscape breadth separately from the prioritized MVLG.
  Treat the Knowledge Graph as source of truth: roadmap is dynamically queried
  using Goal, configurable Core Score, prerequisite closure, topological layers,
  and learner Mastery. Use `next` separately for the immediate recommendation.
- Continue or ask what is next: call `status`, then `next`; inspect `graph` when
  the reason or prerequisite chain matters.
- Learn: call `learn`, teach exactly one concept interactively, then assess it.
  Read [pedagogy.md](references/pedagogy.md).
- Test or diagnose: generate and register a four-level quiz, gather answers, make
  rubric-based structured assessments, then submit them. Read
  [quiz-rules.md](references/quiz-rules.md).
- Review: call `review`; prioritize due reviews, then unresolved misconceptions
  and weak concepts. Use a quiz with purpose `review` so the delayed-review signal
  and next interval are persisted.
- Progress report: call `progress` (and `history` when the learner asks for session
  detail) and summarize observable state only. Read
  [mastery-rules.md](references/mastery-rules.md) when interpreting confidence or
  mastery.
- Local visual dashboard: run `ai-tutor dashboard` for the multi-Subject workspace,
  or `ai-tutor dashboard SUBJECT` for a direct entry. It provides read-only
  Apple-inspired Overview, Blueprint, Roadmap, Concepts, and History views. The
  dashboard must consume `TutorService`; never edit persisted JSON from the UI.
- Detail request inside one landscape branch: read
  [graph-rules.md](references/graph-rules.md), then expand only that anchor's next
  useful neighborhood.

## Learning loop

Keep the loop small: select one unlocked concept, explain briefly, show one useful
example, ask a question, wait for the learner, adapt, then quiz. Do not advance
because the learner merely says they understand. After quiz submission, use the
engine's `status`, mastery, misconceptions, review schedule, and `next` result to
decide whether to remediate, review, or move on.

For an actual teaching turn, call `session-start` before the first learning action
unless `status` reports an active session. Call `session-end` when the learner ends
the study block; do not close an active session merely because one assistant turn
has ended. Learning, graph-expansion, mastery-update, and quiz-submission actions
are recorded automatically while a session is active.

Persist every graph expansion, quiz registration, and assessed attempt. Do not
claim mastery, progress, or misconception resolution without engine-backed evidence.
