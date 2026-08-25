"""Black-box smoke tests for the AI Tutor V0.1 main learning loop."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI = PROJECT_ROOT / "scripts" / "tutor_cli.py"


class TutorSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary.name) / "data"
        self.inputs_dir = Path(self.temporary.name) / "inputs"
        self.inputs_dir.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def cli(self, *arguments: str) -> dict:
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "--data-dir",
                str(self.data_dir),
                "--compact",
                *arguments,
            ],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        if result.returncode != 0:
            self.fail(
                f"CLI failed ({result.returncode}): {' '.join(arguments)}\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        return json.loads(result.stdout)

    def write_json(self, name: str, payload: dict) -> str:
        path = self.inputs_dir / name
        path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        return str(path)

    def expand_machine_learning(self) -> None:
        expansion = {
            "concepts": [
                {
                    "id": "probability",
                    "name": "Probability",
                    "difficulty": 2,
                    "importance": 0.9,
                    "depth": 1,
                },
                {
                    "id": "statistics",
                    "name": "Statistics",
                    "difficulty": 2,
                    "importance": 0.9,
                    "depth": 2,
                },
            ],
            "relations": [
                {
                    "id": "probability_part_of_ml",
                    "source": "probability",
                    "target": "machine_learning",
                    "type": "part_of",
                },
                {
                    "id": "probability_to_statistics",
                    "source": "probability",
                    "target": "statistics",
                    "type": "prerequisite",
                    "threshold": 0.8,
                },
                {
                    "id": "statistics_to_ml",
                    "source": "statistics",
                    "target": "machine_learning",
                    "type": "prerequisite",
                    "threshold": 0.8,
                },
            ],
        }
        self.cli(
            "expand",
            "machine_learning",
            "--anchor",
            "machine_learning",
            "--input",
            self.write_json("expansion.json", expansion),
        )

    def test_smoke_001_create_expand_and_select_first_concept(self) -> None:
        created = self.cli(
            "create", "machine_learning", "--name", "Machine Learning"
        )
        self.assertEqual(created["root_concept"], "machine_learning")

        self.expand_machine_learning()
        selected = self.cli("next", "machine_learning")
        self.assertEqual(selected["concept"], "probability")
        self.assertIn("推荐学习“Probability”", selected["reason"])
        self.assertEqual(self.cli("doctor", "machine_learning")["status"], "ok")

    def test_smoke_004_cli_preserves_chinese_names(self) -> None:
        created = self.cli("create", "machine-learning", "--name", "机器学习")
        self.assertEqual(created["name"], "机器学习")

        # Verify both persisted UTF-8 data and a fresh CLI process response.
        graph = self.cli("graph", "machine-learning")
        self.assertEqual(graph["concepts"][0]["name"], "机器学习")
        stored = json.loads(
            (self.data_dir / "subjects" / "machine-learning.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(stored["concepts"][0]["name"], "机器学习")

    def test_smoke_002_diagnostic_persists_mastery_and_misconception(self) -> None:
        self.cli("create", "machine_learning", "--name", "Machine Learning")
        self.expand_machine_learning()
        question_types = ("recall", "understanding", "application", "transfer")
        quiz = {
            "id": "diagnostic_probability_smoke",
            "subject_id": "machine_learning",
            "concept_id": "probability",
            "purpose": "diagnostic",
            "questions": [
                {
                    "id": f"q{index}",
                    "type": question_type,
                    "prompt": f"{question_type} probability.",
                    "rubric": "Demonstrates the required understanding.",
                }
                for index, question_type in enumerate(question_types, start=1)
            ],
        }
        self.cli(
            "quiz-register",
            "--input",
            self.write_json("diagnostic.json", quiz),
        )
        submission = {
            "answers": {f"q{index}": "learner answer" for index in range(1, 5)},
            "assessments": [
                {
                    "question_id": f"q{index}",
                    "score": 0.2,
                    "reasoning": "The answer applies an incorrect mental model.",
                    "misconceptions": (
                        [
                            {
                                "id": "equiprobable_outcomes",
                                "description": "Assumes all listed outcomes are equally likely.",
                                "severity": 0.8,
                            }
                        ]
                        if index == 4
                        else []
                    ),
                }
                for index in range(1, 5)
            ],
        }
        result = self.cli(
            "quiz-submit",
            "machine_learning",
            "--quiz",
            quiz["id"],
            "--input",
            self.write_json("diagnostic-result.json", submission),
        )
        self.assertEqual(result["status"], "weak")
        self.assertEqual(result["misconceptions"][0]["id"], "equiprobable_outcomes")

        # A fresh CLI process must recover the diagnostic result from disk.
        review = self.cli("review", "machine_learning")
        probability = next(
            item
            for item in review["remediation_candidates"]
            if item["concept"] == "probability"
        )
        self.assertEqual(probability["status"], "weak")
        self.assertEqual(len(probability["misconceptions"]), 1)

    def test_smoke_003_learning_unlocks_next_node_and_resumes_session(self) -> None:
        self.cli("create", "machine_learning", "--name", "Machine Learning")
        self.expand_machine_learning()
        started = self.cli("session-start", "machine_learning")
        learned = self.cli(
            "learn", "machine_learning", "--concept", "probability"
        )
        self.assertEqual(learned["status"], "learning")

        evaluated = self.cli(
            "evaluate",
            "machine_learning",
            "--concept",
            "probability",
            "--concept-quiz",
            "0.9",
            "--practice",
            "0.9",
            "--application",
            "0.9",
            "--transfer",
            "0.9",
            "--delayed-review",
            "0.9",
        )
        self.assertEqual(evaluated["status"], "mastered")
        self.assertEqual(evaluated["next"]["concept"], "statistics")
        ended = self.cli("session-end", "machine_learning")
        self.assertEqual(ended["id"], started["id"])

        # Each call is a separate process, simulating close/reopen persistence.
        status = self.cli("status", "machine_learning")
        progress = self.cli("progress", "machine_learning")
        history = self.cli("history", "machine_learning")
        graph = self.cli("graph", "machine_learning")
        probability = next(
            item for item in graph["concepts"] if item["id"] == "probability"
        )
        self.assertEqual(status["next"], "statistics")
        self.assertEqual(progress["mastered"], 1)
        self.assertEqual(progress["completed_sessions"], 1)
        self.assertEqual(len(history["sessions"]), 1)
        self.assertIsNotNone(probability["learner"]["review"]["next_review"])


if __name__ == "__main__":
    unittest.main()
