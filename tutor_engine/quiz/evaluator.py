"""Convert validated per-question assessments into mastery evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from tutor_engine.quiz.model import AnswerAssessment, Quiz, QuizValidationError


@dataclass(frozen=True, slots=True)
class QuizResult:
    score: float
    evidence: Mapping[str, float]
    assessments: tuple[AnswerAssessment, ...]


class QuizEvaluator:
    def evaluate(
        self,
        quiz: Quiz,
        answers: Mapping[str, str],
        assessments: Sequence[AnswerAssessment],
    ) -> QuizResult:
        question_ids = {question.id for question in quiz.questions}
        if set(answers) != question_ids:
            raise QuizValidationError("answers must match all quiz question ids exactly")
        if any(not isinstance(answer, str) or not answer.strip() for answer in answers.values()):
            raise QuizValidationError("every answer must be non-empty")
        assessment_ids = [assessment.question_id for assessment in assessments]
        if len(set(assessment_ids)) != len(assessment_ids):
            raise QuizValidationError("each question must have exactly one assessment")
        if set(assessment_ids) != question_ids:
            raise QuizValidationError("assessments must match all quiz question ids exactly")

        by_id = {assessment.question_id: assessment for assessment in assessments}
        grouped: dict[str, list[float]] = {
            "concept_quiz": [],
            "application": [],
            "transfer": [],
        }
        all_scores = []
        for question in quiz.questions:
            score = float(by_id[question.id].score)
            all_scores.append(score)
            dimension = {
                "recall": "concept_quiz",
                "understanding": "concept_quiz",
                "application": "application",
                "transfer": "transfer",
            }[question.type]
            grouped[dimension].append(score)
        evidence = {
            dimension: sum(scores) / len(scores)
            for dimension, scores in grouped.items()
            if scores
        }
        if quiz.purpose == "review":
            evidence["delayed_review"] = sum(all_scores) / len(all_scores)
        return QuizResult(
            score=sum(all_scores) / len(all_scores),
            evidence=evidence,
            assessments=tuple(assessments),
        )
