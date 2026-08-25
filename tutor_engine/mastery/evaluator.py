"""A small, explainable rule-based mastery model for V0.1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

from tutor_engine.learner import Learner, LearnerConcept


WEIGHTS = {
    "concept_quiz": 0.30,
    "practice": 0.25,
    "application": 0.20,
    "transfer": 0.15,
    "delayed_review": 0.10,
}


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    score: float
    confidence: float
    contributions: Mapping[str, float]
    evidence: Mapping[str, float]
    explanation: str


class MasteryEvaluator:
    def evaluate(
        self, evidence: Mapping[str, float], *, previous_attempts: int = 0
    ) -> EvaluationResult:
        if not evidence:
            raise ValueError("at least one evidence score is required")
        unknown = set(evidence) - set(WEIGHTS)
        if unknown:
            raise ValueError(f"unknown evidence dimensions: {sorted(unknown)}")
        for dimension, score in evidence.items():
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise ValueError(f"{dimension} score must be a number")
            if not 0.0 <= float(score) <= 1.0:
                raise ValueError(f"{dimension} score must be between 0.0 and 1.0")

        observed_weight = sum(WEIGHTS[key] for key in evidence)
        contributions = {
            key: float(score) * WEIGHTS[key] for key, score in evidence.items()
        }
        score = sum(contributions.values()) / observed_weight
        coverage = observed_weight / sum(WEIGHTS.values())
        repetitions = min(previous_attempts + 1, 5) / 5
        confidence = coverage * 0.7 + repetitions * 0.3
        explanation = (
            f"score={score:.3f} from {len(evidence)} evidence dimension(s); "
            f"confidence={confidence:.3f} (coverage={coverage:.2f}, "
            f"attempts={previous_attempts + 1})"
        )
        return EvaluationResult(
            score=score,
            confidence=confidence,
            contributions=contributions,
            evidence=dict(evidence),
            explanation=explanation,
        )

    def update_mastery(
        self,
        learner: Learner,
        concept_id: str,
        evidence: Mapping[str, float],
    ) -> EvaluationResult:
        state = learner.get_or_create_concept(concept_id)
        result = self.evaluate(evidence, previous_attempts=state.attempt_count)
        self._merge_result(state, result)
        return result

    def _merge_result(self, state: LearnerConcept, result: EvaluationResult) -> None:
        previous = state.mastery
        total_weight = previous.confidence + result.confidence
        if total_weight:
            previous.score = round(
                (
                    previous.score * previous.confidence
                    + result.score * result.confidence
                )
                / total_weight,
                6,
            )
        previous.confidence = round(
            1 - (1 - previous.confidence) * (1 - result.confidence), 6
        )
        now = datetime.now(timezone.utc).isoformat()
        previous.updated_at = now
        state.attempt_count += 1
        state.last_learned = now
        state.status = self.status_for(previous.score, previous.confidence)

    @staticmethod
    def status_for(score: float, confidence: float = 1.0) -> str:
        if score < 0.30:
            return "weak"
        if score < 0.60:
            return "learning"
        if score < 0.80 or confidence < 0.60:
            return "familiar"
        return "mastered"

    @staticmethod
    def get_weak_concepts(learner: Learner) -> tuple[LearnerConcept, ...]:
        return tuple(
            state
            for state in learner.concepts.values()
            if state.mastery.score < 0.30 and state.attempt_count > 0
        )
