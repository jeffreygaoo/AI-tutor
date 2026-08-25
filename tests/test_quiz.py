import tempfile
import unittest
from pathlib import Path

from tutor_engine.quiz import Quiz, QuizValidationError
from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository


def quiz_payload() -> dict:
    return {
        "id": "quiz_probability_1",
        "subject_id": "probability",
        "concept_id": "probability",
        "questions": [
            {"id": "q1", "type": "recall", "prompt": "Define probability.", "rubric": "Definition"},
            {"id": "q2", "type": "understanding", "prompt": "Explain its range.", "rubric": "0 to 1"},
            {"id": "q3", "type": "application", "prompt": "Compute a fair coin event.", "rubric": "1/2"},
            {"id": "q4", "type": "transfer", "prompt": "Apply it to a new case.", "rubric": "Sound model"},
        ],
    }


class QuizTests(unittest.TestCase):
    def test_requires_all_four_cognitive_types(self) -> None:
        payload = quiz_payload()
        payload["questions"] = payload["questions"][:3]
        with self.assertRaisesRegex(QuizValidationError, "missing"):
            Quiz.from_dict(payload)

    def test_structured_assessment_updates_mastery_and_misconception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = TutorService(JsonRepository(Path(temporary)))
            service.create_subject("probability", "Probability")
            service.register_quiz(quiz_payload())
            answers = {f"q{number}": "answer" for number in range(1, 5)}
            assessments = [
                {
                    "question_id": f"q{number}",
                    "score": 0.8 if number != 4 else 0.2,
                    "reasoning": "Rubric-based assessment.",
                    "misconceptions": (
                        [{
                            "id": "equiprobable_outcomes",
                            "description": "Assumes all outcomes are equally likely.",
                            "severity": 0.8,
                        }]
                        if number == 4 else []
                    ),
                }
                for number in range(1, 5)
            ]
            result = service.submit_quiz(
                "probability", "quiz_probability_1", answers, assessments
            )
            self.assertEqual(result["mastery_evidence"]["transfer"], 0.2)
            self.assertEqual(result["misconceptions"][0]["id"], "equiprobable_outcomes")

            resumed = TutorService(JsonRepository(Path(temporary)))
            graph = resumed.graph_view("probability")
            state = graph["concepts"][0]["learner"]
            self.assertEqual(state["attempt_count"], 1)
            self.assertEqual(len(state["misconceptions"]), 1)
            attempts = list(Path(temporary).rglob("attempt_*.json"))
            self.assertEqual(len(attempts), 1)

    def test_incomplete_assessment_does_not_update_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            service = TutorService(JsonRepository(Path(temporary)))
            service.create_subject("probability", "Probability")
            service.register_quiz(quiz_payload())
            with self.assertRaisesRegex(QuizValidationError, "assessments"):
                service.submit_quiz(
                    "probability",
                    "quiz_probability_1",
                    {f"q{number}": "answer" for number in range(1, 5)},
                    [{"question_id": "q1", "score": 1.0, "reasoning": "Correct."}],
                )
            state = service.graph_view("probability")["concepts"][0]["learner"]
            self.assertEqual(state["attempt_count"], 0)

    def test_diagnostic_and_review_use_the_same_validated_protocol(self) -> None:
        diagnostic = quiz_payload()
        diagnostic["purpose"] = "diagnostic"
        self.assertEqual(Quiz.from_dict(diagnostic).purpose, "diagnostic")
        review = quiz_payload()
        review["purpose"] = "review"
        self.assertEqual(Quiz.from_dict(review).purpose, "review")

    def test_review_submission_adds_delayed_evidence_and_advances_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = JsonRepository(Path(temporary))
            service = TutorService(repository)
            service.create_subject("probability", "Probability")
            payload = quiz_payload()
            payload["id"] = "review_probability_1"
            payload["purpose"] = "review"
            service.register_quiz(payload)
            learner = repository.load_learner("probability")
            state = learner.get_or_create_concept("probability")
            state.status = "mastered"
            state.mastery.score = 0.9
            state.mastery.confidence = 0.8
            state.review.stage = 0
            state.review.next_review = "2026-08-25T00:00:00+00:00"
            repository.save_learner("probability", learner)
            result = service.submit_quiz(
                "probability",
                "review_probability_1",
                {f"q{number}": "answer" for number in range(1, 5)},
                [
                    {
                        "question_id": f"q{number}",
                        "score": 0.9,
                        "reasoning": "Correct and well transferred.",
                    }
                    for number in range(1, 5)
                ],
            )
            self.assertEqual(result["mastery_evidence"]["delayed_review"], 0.9)
            restored = repository.load_learner("probability")
            self.assertEqual(restored.concepts["probability"].review.stage, 1)
