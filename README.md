# AI Tutor

[简体中文](README.zh-CN.md) | English

AI Tutor V0.1 is a local-first, goal-bounded learning engine. It combines an
objective knowledge graph with per-learner mastery, prerequisite unlocking,
adaptive roadmap generation, quizzes, misconceptions, learning sessions, and
spaced review.

The Python engine is deterministic and model-independent. Codex can orchestrate
the included `ai-tutor` Skill for teaching and semantic assessment, but the CLI,
dashboard, roadmap, and persisted learning state do not require Codex or any
online model.

> V0.1 targets single-machine, single-user use. It stores data as local JSON and
> does not require a database or a separate frontend service.

## Highlights

- Goal-bounded Subject Blueprint with a coarse domain landscape.
- Engine-selected minimum viable learning graph (MVLG).
- Dynamic roadmap based on prerequisites, goal relevance, and mastery.
- Progressive, bounded expansion of a topic into teachable child concepts.
- Hierarchical mastery aggregated from required child concepts.
- Explainable next-concept selection and deterministic unlocking.
- Diagnostic, learning, and review quizzes with structured evidence.
- Misconception tracking and 1/3/7/14/30-day spaced review.
- Persistent learning sessions, attempts, progress, and history.
- Local Chinese dashboard with multi-Subject switching and recursive drill-down.
- Confirmed progress reset and Subject deletion with recoverable archives.
- Versioned, atomic JSON persistence with previous-version backups.

## How it works

```text
Language model / human / CLI
             |
             v
        TutorService
      /      |       \
Knowledge  Mastery  Curriculum
  Graph     Graph      Planner
      \      |       /
       JsonRepository
             |
           data/
```

The dashboard frontend uses plain HTML, CSS, and JavaScript. The same Python
process serves both static assets and JSON APIs, so the project is logically
layered but not deployed as separate frontend and backend applications.

## Requirements

- Python 3.11 or newer
- A modern browser for the dashboard
- Codex only if you want to use the bundled Skill workflow

Runtime code uses the Python standard library. Building or installing the package
uses `setuptools`.

## Installation

### macOS / Linux

```bash
git clone <repository-url>
cd AI-tutor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

### Windows PowerShell

```powershell
git clone <repository-url>
Set-Location AI-tutor
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

For development, replace the last command with `python -m pip install -e .`.

Verify the installation:

```bash
ai-tutor --version
ai-tutor --help
```

## Quick start

Create a local Subject and inspect its state:

```bash
ai-tutor create machine_learning --name "Machine Learning"
ai-tutor status machine_learning
ai-tutor graph machine_learning
```

Start the workspace dashboard:

```bash
ai-tutor dashboard
```

By default it is available at <http://127.0.0.1:8765/>. Use
`ai-tutor dashboard SUBJECT`, `--port`, `--host`, or `--no-open` when needed.

A newly created Subject contains only its root concept. Use the AI Tutor Skill or
the structured CLI protocols to create its Blueprint, diagnostic, and detailed
concept expansions.

## Use with Codex

The repository contains a model-facing Skill in [`skill/ai-tutor`](skill/ai-tutor).
Install that directory into your Codex skills directory, restart Codex, open this
repository as the workspace, and start with a request such as:

```text
$ai-tutor I want to learn cloud computing from the beginning.
My goal is to become a cloud application developer. I can study five hours a week.
```

The Skill uses the language model for explanations, examples, quiz generation,
and rubric-based semantic assessment. It uses `TutorService` and the CLI as the
source of truth for persisted state and deterministic decisions.

See the [AI Tutor Skill user guide](docs/ai-tutor-skill-user-guide.md) for the
full workflow.

## Common CLI commands

| Command | Purpose |
| --- | --- |
| `create` | Create a Subject root |
| `blueprint-create` | Persist a goal, landscape, and roadmap configuration |
| `blueprint` | Inspect the goal-bounded landscape and backbone |
| `roadmap` | Recompute the personalized MVLG stages |
| `directions` | Inspect optional advancement directions |
| `expand` | Add one bounded batch below an anchor concept |
| `status` / `progress` | Inspect learning state and analytics |
| `next` / `learn` | Select or start the next teachable concept |
| `quiz-register` / `quiz-submit` | Persist a quiz and assessed attempt |
| `review` | List due reviews and remediation candidates |
| `session-start` / `session-end` / `history` | Manage learning sessions |
| `doctor` | Validate persisted data |
| `reset-progress` | Reset one learner while preserving curriculum data |
| `delete-subject` | Remove a Subject and all learner data |

Commands return JSON by default. `blueprint`, `roadmap`, and `directions` support
Markdown output when `--format markdown` is placed before the command:

```bash
ai-tutor --format markdown roadmap machine_learning
```

Global options such as `--learner`, `--data-dir`, and `--compact` must also appear
before the command.

## Data and privacy

The default data directory is `./data`:

```text
data/
├── subjects/       # objective knowledge graphs
├── blueprints/     # goals, landscapes, and roadmap configuration
├── learners/       # mastery, confidence, reviews, and misconceptions
├── sessions/       # quizzes, attempts, and learning-session history
└── archive/        # recoverable reset/delete archives
```

`data/` is ignored by Git because it may contain private learning goals, answers,
history, and misconceptions. Do not publish that directory. Back it up if the
learning state matters to you.

Writes are atomic, existing files receive a `.bak` copy, and reset/delete actions
move affected files into a timestamped archive before completing.

More details: [Data and privacy](docs/data-and-privacy.md).

## Reset and delete

Both destructive commands require the exact Subject ID as confirmation:

```bash
ai-tutor reset-progress machine_learning --confirm machine_learning
ai-tutor delete-subject machine_learning --confirm machine_learning
```

`reset-progress` affects only the selected learner. It preserves the Subject
graph, Blueprint, and expanded topics. `delete-subject` removes the Subject,
Blueprint, and every learner's associated resources from the active workspace.

## Other language models

The engine is not tied to Codex. DeepSeek, OpenAI API models, or other LLMs can
generate lessons and structured payloads, but V0.1 does not include a provider API
adapter. A replacement model must convert its output to the Blueprint, expansion,
quiz, and assessment JSON accepted by `TutorService` or the CLI.

See [Architecture and model integration](docs/architecture.md).

## Development

Run the complete test suite:

```bash
python -m unittest discover -v
```

The V0.1 suite covers graph validation, Blueprint generation, roadmap selection,
mastery, quizzes, persistence, sessions, progressive expansion, hierarchy,
dashboard APIs, reset, deletion, and recovery behavior.

See [Contributing](CONTRIBUTING.md) and [smoke-test cases](docs/smoke-test-cases.md).

## V0.1 limitations

- Optimized for one machine and one primary user.
- JSON persistence; no SQLite or server database.
- No authentication or public-network hardening.
- Frontend and backend are served by one local Python process.
- No built-in DeepSeek/OpenAI/other provider client.
- Semantic answer assessment still depends on a language model or human assessor.
- No automatic archive-restore command yet.

## License

Licensed under the [Apache License 2.0](LICENSE).
