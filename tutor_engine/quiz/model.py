"""Validated objects exchanged between the LLM and deterministic engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping


QuestionType = Literal["recall", "understanding", "application", "transfer"]
QuizPurpose = Literal["diagnostic", "learning", "review"]
QUESTION_TYPES = frozenset({"recall", "understanding", "application", "transfer"})


class QuizValidationError(ValueError):
    """Raised when LLM-produced quiz data violates the protocol."""


def _text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise QuizValidationError(f"{field_name} must be a non-empty string")


def _score(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise QuizValidationError(f"{field_name} must be a number")
    if not 0.0 <= float(value) <= 1.0:
        raise QuizValidationError(f"{field_name} must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class QuizQuestion:
    id: str
    type: QuestionType
    prompt: str
    rubric: str
    difficulty: int = 1

    def __post_init__(self) -> None:
        _text(self.id, "question.id")
        _text(self.prompt, "question.prompt")
        _text(self.rubric, "question.rubric")
        if self.type not in QUESTION_TYPES:
            raise QuizValidationError(f"unsupported question type: {self.type!r}")
        if (
            isinstance(self.difficulty, bool)
            or not isinstance(self.difficulty, int)
            or not 1 <= self.difficulty <= 5
        ):
            raise QuizValidationError("question.difficulty must be between 1 and 5")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> QuizQuestion:
        return cls(**dict(data))


@dataclass(frozen=True, slots=True)
class Quiz:
    id: str
    subject_id: str
    concept_id: str
    questions: tuple[QuizQuestion, ...]
    purpose: QuizPurpose = "learning"

    def __post_init__(self) -> None:
        _text(self.id, "quiz.id")
        _text(self.subject_id, "quiz.subject_id")
        _text(self.concept_id, "quiz.concept_id")
        if len({question.id for question in self.questions}) != len(self.questions):
            raise QuizValidationError("question ids must be unique")
        missing = QUESTION_TYPES - {question.type for question in self.questions}
        if missing:
            raise QuizValidationError(
                f"quiz must cover recall, understanding, application and transfer; "
                f"missing {sorted(missing)}"
            )
        if self.purpose not in {"diagnostic", "learning", "review"}:
            raise QuizValidationError(f"unsupported quiz purpose: {self.purpose!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "id": self.id,
            "subject_id": self.subject_id,
            "concept_id": self.concept_id,
            "questions": [question.to_dict() for question in self.questions],
            "purpose": self.purpose,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Quiz:
        return cls(
            id=data["id"],
            subject_id=data["subject_id"],
            concept_id=data["concept_id"],
            questions=tuple(
                QuizQuestion.from_dict(item) for item in data.get("questions", [])
            ),
            purpose=data.get("purpose", "learning"),
        )


@dataclass(frozen=True, slots=True)
class DetectedMisconception:
    id: str
    description: str
    severity: float = 0.5

    def __post_init__(self) -> None:
        _text(self.id, "misconception.id")
        _text(self.description, "misconception.description")
        _score(self.severity, "misconception.severity")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DetectedMisconception:
        return cls(**dict(data))


@dataclass(frozen=True, slots=True)
class AnswerAssessment:
    question_id: str
    score: float
    reasoning: str
    misconceptions: tuple[DetectedMisconception, ...] = ()

    def __post_init__(self) -> None:
        _text(self.question_id, "assessment.question_id")
        _score(self.score, "assessment.score")
        _text(self.reasoning, "assessment.reasoning")

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "score": self.score,
            "reasoning": self.reasoning,
            "misconceptions": [item.to_dict() for item in self.misconceptions],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AnswerAssessment:
        return cls(
            question_id=data["question_id"],
            score=data["score"],
            reasoning=data["reasoning"],
            misconceptions=tuple(
                DetectedMisconception.from_dict(item)
                for item in data.get("misconceptions", [])
            ),
        )


@dataclass(frozen=True, slots=True)
class QuizAttempt:
    id: str
    quiz_id: str
    subject_id: str
    concept_id: str
    learner_id: str
    answers: Mapping[str, str]
    assessments: tuple[AnswerAssessment, ...]
    created_at: str
    purpose: QuizPurpose = "learning"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "id": self.id,
            "quiz_id": self.quiz_id,
            "subject_id": self.subject_id,
            "concept_id": self.concept_id,
            "learner_id": self.learner_id,
            "answers": dict(self.answers),
            "assessments": [item.to_dict() for item in self.assessments],
            "created_at": self.created_at,
            "purpose": self.purpose,
        }
