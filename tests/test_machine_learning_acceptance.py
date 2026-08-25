import tempfile
import unittest
from pathlib import Path

from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository


def four_level_quiz(quiz_id: str, concept_id: str, purpose: str) -> dict:
    return {
        "id": quiz_id,
        "subject_id": "machine_learning",
        "concept_id": concept_id,
        "purpose": purpose,
        "questions": [
            {"id": f"{quiz_id}_r", "type": "recall", "prompt": "Recall it.", "rubric": "Correct definition."},
            {"id": f"{quiz_id}_u", "type": "understanding", "prompt": "Explain it.", "rubric": "Correct mechanism."},
            {"id": f"{quiz_id}_a", "type": "application", "prompt": "Apply it.", "rubric": "Correct application."},
            {"id": f"{quiz_id}_t", "type": "transfer", "prompt": "Transfer it.", "rubric": "Correct transfer."},
        ],
    }


def submit_payload(quiz: dict, score: float) -> tuple[dict[str, str], list[dict]]:
    answers = {question["id"]: "learner answer" for question in quiz["questions"]}
    assessments = [
        {"question_id": question["id"], "score": score, "reasoning": "Rubric-based."}
        for question in quiz["questions"]
    ]
    return answers, assessments


class MachineLearningAcceptanceTest(unittest.TestCase):
    def test_new_learner_diagnostic_learning_mastery_unlock_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary)
            service = TutorService(JsonRepository(data_dir))
            service.create_subject("machine_learning", "Machine Learning")
            service.expand_subject(
                "machine_learning",
                "machine_learning",
                {
                    "concepts": [
                        {"id": "probability", "name": "Probability", "importance": 0.9, "depth": 1},
                        {"id": "statistics", "name": "Statistics", "importance": 0.9, "depth": 2},
                    ],
                    "relations": [
                        {"id": "probability_to_ml", "source": "probability", "target": "machine_learning", "type": "part_of"},
                        {"id": "probability_to_statistics", "source": "probability", "target": "statistics", "type": "prerequisite", "threshold": 0.8},
                        {"id": "statistics_to_ml", "source": "statistics", "target": "machine_learning", "type": "prerequisite", "threshold": 0.8},
                    ],
                },
            )
            session = service.start_session("machine_learning")

            diagnostic = four_level_quiz("diagnostic_probability", "probability", "diagnostic")
            service.register_quiz(diagnostic)
            answers, assessments = submit_payload(diagnostic, 0.2)
            diagnosed = service.submit_quiz(
                "machine_learning", diagnostic["id"], answers, assessments
            )
            self.assertEqual(diagnosed["status"], "weak")
            self.assertEqual(service.next_concept("machine_learning")["concept"], "probability")

            service.learn("machine_learning", concept_id="probability")
            service.evaluate(
                "machine_learning",
                "probability",
                {
                    "concept_quiz": 1.0,
                    "practice": 1.0,
                    "application": 1.0,
                    "transfer": 1.0,
                    "delayed_review": 1.0,
                },
            )
            # Existing diagnostic evidence is blended, so repeat strong transfer evidence.
            service.evaluate(
                "machine_learning",
                "probability",
                {
                    "concept_quiz": 1.0,
                    "practice": 1.0,
                    "application": 1.0,
                    "transfer": 1.0,
                    "delayed_review": 1.0,
                },
            )
            self.assertEqual(service.next_concept("machine_learning")["concept"], "statistics")
            ended = service.end_session("machine_learning")
            self.assertEqual(ended["id"], session["id"])

            resumed = TutorService(JsonRepository(data_dir))
            status = resumed.status("machine_learning")
            report = resumed.progress_report("machine_learning")
            review = resumed.review("machine_learning")
            self.assertEqual(status["next"], "statistics")
            self.assertEqual(report["mastered"], 1)
            self.assertEqual(report["sessions"], 1)
            self.assertEqual(report["quiz_attempt_records"], 1)
            self.assertEqual(len(review["due_reviews"]), 0)
            probability = next(
                item for item in resumed.graph_view("machine_learning")["concepts"]
                if item["id"] == "probability"
            )
            self.assertIsNotNone(probability["learner"]["review"]["next_review"])
