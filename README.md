# AI Tutor

AI Tutor V0.1 is a deterministic Python engine for a persistent learning loop:

`Knowledge Graph -> Learning Graph <-> Mastery Graph`

The current milestones implement the shared concept graph, learner state,
dependency unlocking, and explainable mastery evaluation. The project intentionally
uses only the Python standard library and JSON-friendly models.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## CLI quick start

```powershell
python scripts/tutor_cli.py create machine_learning --name "Machine Learning"
python scripts/tutor_cli.py next machine_learning
python scripts/tutor_cli.py learn machine_learning
python scripts/tutor_cli.py evaluate machine_learning --concept machine_learning `
  --concept-quiz 0.9 --practice 0.8 --application 0.8 --transfer 0.7
python scripts/tutor_cli.py status machine_learning
```

After installation, the same commands are available through `ai-tutor`. Set
`AI_TUTOR_DATA_DIR` to change the default data location, pass `--compact` for
single-line JSON, or use `--input -` to read structured JSON from stdin.

Every command emits structured JSON by default. Blueprint views can also be
rendered as a Markdown Blueprint view with a Mermaid mind map, a core-backbone
score table, a prerequisite graph, and collapsible advancement directions:

```powershell
python scripts/tutor_cli.py --format markdown blueprint machine_learning
python scripts/tutor_cli.py --format markdown roadmap machine_learning
python scripts/tutor_cli.py --format markdown directions machine_learning
```

Data is atomically persisted under `data/`.

Detailed usage: [AI Tutor Skill 使用说明](docs/ai-tutor-skill-user-guide.md).

## Local dashboard

Start the read-only local dashboard for a persisted Blueprint:

```powershell
ai-tutor dashboard
```

The workspace discovers every persisted Subject and supports in-page switching.
Use `ai-tutor dashboard machine-learning` for a direct Subject entry, or add
`--port 9000`, `--host 127.0.0.1`, or `--no-open` when needed. The dashboard
reads Blueprint, dynamic Roadmap, Mastery, recommendations, reviews, and history
through `TutorService`; it never edits JSON files directly.

## Current scope

- Concept and relation models
- Graph mutation and traversal
- Prerequisite queries
- Graph validation, including prerequisite-cycle detection
- JSON-compatible serialization and restoration
- Learner concept state and misconception tracking
- Deterministic prerequisite thresholds and unlock decisions
- Weighted mastery evaluation with separate score and confidence
- Explainable mastery updates and weak-concept queries
- Deterministic next-concept ranking with an explainable factor breakdown
- Atomic JSON persistence for subjects and per-learner state
- JSON CLI: `create`, `status`, `graph`, `next`, `learn`, `evaluate`, `review`,
  `expand`, `quiz-register`, `quiz-submit`, `session-start`, `session-end`,
  `history`, `progress`, `blueprint-create`, `blueprint`, `roadmap`, `directions`
- Structured four-level quiz and LLM answer-assessment protocol
- Persistent quiz attempts and misconception detection history
- Connected, bounded, rollback-safe progressive graph expansion
- Diagnostic/learning/review quiz purposes with a shared validated protocol
- Explainable 1/3/7/14/30-day review scheduling
- Codex Tutor Skill with progressively disclosed graph, pedagogy, mastery, and quiz rules
- Persistent learning sessions with automatic action events
- Progress analytics for mastery, confidence, attempts, retention, sessions, and reviews
- Versioned JSON schemas with legacy migration and previous-version backup recovery
- Installable `ai-tutor` console command and persisted-data `doctor` check
- Goal-bounded Subject Blueprint with coarse landscape, algorithmic core backbone,
  dynamic roadmap stages, and advancement directions
- Goal-aware MVLG generation with configurable Core Score, recursive prerequisite
  closure, DAG topological layers, dynamic graph-expansion refresh, mastery overlay,
  and explainable inclusion reasons

The V0.1 core loop is now ready for its Machine Learning acceptance scenario.
