import tempfile
import unittest
import json
import contextlib
import io
from pathlib import Path

from scripts.tutor_cli import main, run
from tutor_engine.blueprint import BlueprintValidationError
from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository


def blueprint_payload() -> dict:
    concepts = [
        {
            "id": "problem_framing",
            "name": "Problem Framing",
            "difficulty": 1,
            "importance": 1.0,
            "depth": 1,
            "metadata": {
                "scope_tags": ["supervised_learning"],
                "goal_relevance": 1.0,
                "transfer_value": 1.0,
                "mental_model_value": 1.0,
                "expandable": True,
            },
        },
        {
            "id": "data_split",
            "name": "Train/Test Split",
            "difficulty": 1,
            "importance": 1.0,
            "depth": 2,
            "metadata": {
                "scope_tags": ["model_evaluation"],
                "goal_relevance": 1.0,
                "transfer_value": 0.9,
                "mental_model_value": 0.9,
                "expandable": True,
            },
        },
        {
            "id": "generalization",
            "name": "Generalization",
            "difficulty": 2,
            "importance": 1.0,
            "depth": 3,
            "metadata": {
                "scope_tags": ["model_evaluation"],
                "goal_relevance": 1.0,
                "transfer_value": 1.0,
                "mental_model_value": 1.0,
                "expandable": True,
            },
        },
        {
            "id": "linear_models",
            "name": "Linear Models",
            "difficulty": 2,
            "importance": 0.8,
            "depth": 3,
            "metadata": {
                "scope_tags": ["supervised_learning"],
                "goal_relevance": 0.8,
                "transfer_value": 0.7,
                "mental_model_value": 0.7,
                "expandable": True,
            },
        },
    ]
    return {
        "scope": {
            "goal": "Build a tabular classification project",
            "target_level": "practical_intermediate",
            "included": ["supervised_learning", "model_evaluation"],
            "excluded": ["reinforcement_learning"],
            "weekly_hours": 5,
        },
        "landscape": {
            "concepts": concepts,
            "relations": [
                {"id": "root_problem", "source": "ml", "target": "problem_framing", "type": "part_of"},
                {"id": "problem_split", "source": "problem_framing", "target": "data_split", "type": "prerequisite", "threshold": 0.8},
                {"id": "split_generalization", "source": "data_split", "target": "generalization", "type": "prerequisite", "threshold": 0.8},
                {"id": "split_linear", "source": "data_split", "target": "linear_models", "type": "prerequisite", "threshold": 0.8},
            ],
            "sections": [
                {"id": "orientation", "name": "Orientation", "description": "Frame the task.", "concept_ids": ["problem_framing"]},
                {"id": "evaluation", "name": "Evaluation", "description": "Reason about generalization.", "concept_ids": ["data_split", "generalization"]},
                {"id": "models", "name": "Models", "description": "Build initial models.", "concept_ids": ["linear_models"]},
            ],
        },
        "backbone_size": 3,
        "advanced_directions": [
            {
                "id": "deep_learning",
                "name": "Deep Learning",
                "description": "Advance to representation learning.",
                "entry_concept_ids": ["generalization"],
                "in_scope": False,
            }
        ],
    }


class BlueprintEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary.name)
        self.service = TutorService(JsonRepository(self.data_dir))
        self.service.create_subject("ml", "Machine Learning")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_builds_landscape_backbone_directions_and_persists(self) -> None:
        created = self.service.create_blueprint("ml", blueprint_payload())
        self.assertEqual(len(created["landscape"]), 3)
        self.assertEqual(len(created["core_backbone"]), 3)
        self.assertIn(
            "data_split",
            [item["concept_id"] for item in created["core_backbone"]],
        )
        self.assertEqual(created["advanced_directions"][0]["id"], "deep_learning")

        resumed = TutorService(JsonRepository(self.data_dir))
        roadmap = resumed.roadmap("ml")
        directions = resumed.directions("ml")
        self.assertGreaterEqual(len(roadmap["stages"]), 2)
        self.assertEqual(roadmap["stages"][0]["status"], "current")
        self.assertFalse(directions["directions"][0]["entry_ready"])
        self.assertTrue(resumed.doctor("ml")["blueprint"])

    def test_excluded_scope_rejects_entire_blueprint_without_graph_mutation(self) -> None:
        payload = blueprint_payload()
        payload["landscape"]["concepts"][0]["metadata"]["scope_tags"] = [
            "reinforcement_learning"
        ]
        with self.assertRaisesRegex(BlueprintValidationError, "excluded scope"):
            self.service.create_blueprint("ml", payload)
        graph = self.service.graph_view("ml")
        self.assertEqual([item["id"] for item in graph["concepts"]], ["ml"])
        self.assertFalse(self.service.doctor("ml")["blueprint"])

    def test_mastery_updates_roadmap_stage_status(self) -> None:
        self.service.create_blueprint("ml", blueprint_payload())
        roadmap = self.service.roadmap("ml")
        first_stage_ids = [item["id"] for item in roadmap["stages"][0]["concepts"]]
        for concept_id in first_stage_ids:
            self.service.evaluate(
                "ml",
                concept_id,
                {
                    "concept_quiz": 1.0,
                    "practice": 1.0,
                    "application": 1.0,
                    "transfer": 1.0,
                    "delayed_review": 1.0,
                },
            )
        updated = self.service.roadmap("ml")
        self.assertEqual(updated["stages"][0]["status"], "completed")
        self.assertEqual(updated["stages"][1]["status"], "current")

    def test_later_expansion_enforces_persisted_excluded_scope(self) -> None:
        self.service.create_blueprint("ml", blueprint_payload())
        with self.assertRaisesRegex(BlueprintValidationError, "excluded scope"):
            self.service.expand_subject(
                "ml",
                "generalization",
                {
                    "concepts": [
                        {
                            "id": "policy_gradient",
                            "name": "Policy Gradient",
                            "metadata": {
                                "scope_tags": ["reinforcement_learning"]
                            },
                        }
                    ],
                    "relations": [
                        {
                            "id": "generalization_policy",
                            "source": "generalization",
                            "target": "policy_gradient",
                            "type": "related_to",
                        }
                    ],
                },
            )
        graph = self.service.graph_view("ml")
        self.assertNotIn("policy_gradient", [item["id"] for item in graph["concepts"]])

    def test_cli_exposes_blueprint_roadmap_and_directions(self) -> None:
        input_path = self.data_dir / "blueprint-input.json"
        input_path.write_text(
            json.dumps(blueprint_payload(), ensure_ascii=False), encoding="utf-8"
        )
        common = ["--data-dir", str(self.data_dir)]
        created = run(common + ["blueprint-create", "ml", "--input", str(input_path)])
        roadmap = run(common + ["roadmap", "ml"])
        directions = run(common + ["directions", "ml"])
        self.assertEqual(created["scope"]["target_level"], "practical_intermediate")
        self.assertGreaterEqual(len(roadmap["stages"]), 2)
        self.assertEqual(directions["directions"][0]["id"], "deep_learning")

    def test_cli_renders_blueprint_as_mindmap_and_focused_views(self) -> None:
        input_path = self.data_dir / "blueprint-input.json"
        input_path.write_text(
            json.dumps(blueprint_payload(), ensure_ascii=False), encoding="utf-8"
        )
        self.service.create_blueprint("ml", blueprint_payload())
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main([
                "--data-dir", str(self.data_dir), "--format", "markdown",
                "blueprint", "ml",
            ])
        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("## 学习范围", rendered)
        self.assertIn("## 领域全景思维导图", rendered)
        self.assertIn("## 核心骨架", rendered)
        self.assertIn("## 核心依赖关系", rendered)
        self.assertIn("## 进阶方向", rendered)
        self.assertIn("```mermaid\nmindmap", rendered)
        self.assertIn('section_1["Orientation"]', rendered)
        self.assertIn('concept_1_1["Problem Framing · available · 可展开"]', rendered)
        self.assertIn("| 1 | Train/Test Split | core |", rendered)
        self.assertIn("flowchart LR", rendered)
        self.assertIn("<details>", rendered)
        self.assertIn("<summary>Deep Learning · 可选进阶</summary>", rendered)

    def test_blueprint_view_exposes_only_backbone_prerequisite_edges(self) -> None:
        view = self.service.create_blueprint("ml", blueprint_payload())
        edges = {(item["source"], item["target"]) for item in view["core_dependencies"]}
        self.assertEqual(edges, {
            ("problem_framing", "data_split"),
            ("data_split", "generalization"),
        })

    def test_goal_model_overrides_legacy_scope_goal(self) -> None:
        payload = blueprint_payload()
        payload["goal"] = {
            "id": "goal_ml_project",
            "subject_id": "ml",
            "description": "Ship an ML project",
            "target_level": "intermediate",
            "orientation": "practical",
            "time_budget": {"hours_per_week": 7, "target_months": 4},
        }
        created = self.service.create_blueprint("ml", payload)
        self.assertEqual(created["scope"]["goal"], "Ship an ML project")
        roadmap = self.service.roadmap("ml")
        self.assertEqual(roadmap["goal_id"], "goal_ml_project")
        self.assertEqual(roadmap["orientation"], "practical")
        self.assertEqual(roadmap["time_budget"], {"hours_per_week": 7, "target_months": 4})

    def test_roadmap_recomputes_mvlg_after_graph_expansion(self) -> None:
        self.service.create_blueprint("ml", blueprint_payload())
        before = self.service.roadmap("ml")["mvlg_concept_count"]
        self.service.expand_subject(
            "ml",
            "generalization",
            {
                "concepts": [{
                    "id": "ml_project",
                    "name": "ML Project",
                    "importance": 1.0,
                    "metadata": {
                        "scope_tags": ["supervised_learning"],
                        "goal_relevance": 1.0,
                    },
                }],
                "relations": [{
                    "id": "generalization_project",
                    "source": "generalization",
                    "target": "ml_project",
                    "type": "prerequisite",
                }],
            },
        )
        after = self.service.roadmap("ml")
        self.assertGreater(after["mvlg_concept_count"], before)
        self.assertIn("ml_project", [item["id"] for stage in after["stages"] for item in stage["concepts"]])

    def test_cli_rejects_markdown_for_unsupported_command(self) -> None:
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            exit_code = main([
                "--data-dir", str(self.data_dir), "--format", "markdown",
                "status", "ml",
            ])
        self.assertEqual(exit_code, 1)
        self.assertIn("Markdown output is not supported", error.getvalue())

    def test_rejected_markdown_command_does_not_mutate_state(self) -> None:
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            exit_code = main([
                "--data-dir", str(self.data_dir), "--format", "markdown",
                "session-start", "ml",
            ])
        self.assertEqual(exit_code, 1)
        self.assertIsNone(self.service.status("ml")["active_session"])


if __name__ == "__main__":
    unittest.main()
