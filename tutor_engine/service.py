"""Application service shared by the CLI and future API clients."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from tutor_engine.curriculum import CurriculumPlanner, DependencyEngine
from tutor_engine.blueprint import BlueprintValidationError, build_blueprint
from tutor_engine.graph import Concept, ConceptGraph, Relation, expand_graph
from tutor_engine.learner import Misconception
from tutor_engine.mastery import MasteryEvaluator
from tutor_engine.quiz import AnswerAssessment, Quiz, QuizAttempt, QuizEvaluator
from tutor_engine.review import ReviewScheduler
from tutor_engine.roadmap import RoadmapConfig, analyze_roadmap
from tutor_engine.session import LearningSession, utc_now
from tutor_engine.storage import JsonRepository, StorageError
from tutor_engine.storage import SCHEMA_VERSION


class TutorService:
    def __init__(self, repository: JsonRepository) -> None:
        self.repository = repository

    def create_subject(
        self, subject_id: str, name: str, learner_id: str = "default"
    ) -> dict[str, Any]:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        graph = ConceptGraph(
            subject_id,
            concepts=[
                Concept(
                    subject_id,
                    name.strip(),
                    description=f"Root concept for {name.strip()}.",
                    importance=1.0,
                    metadata={"goal_relevance": 1.0, "expandable": True},
                )
            ],
        )
        self.repository.save_graph(graph, overwrite=False)
        learner = self.repository.load_learner(subject_id, learner_id)
        DependencyEngine(graph, learner).refresh()
        self.repository.save_learner(subject_id, learner)
        return {
            "subject": subject_id,
            "name": name.strip(),
            "learner": learner_id,
            "root_concept": subject_id,
        }

    def status(self, subject_id: str, learner_id: str = "default") -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        DependencyEngine(graph, learner).refresh()
        mastered = sum(
            learner.get_or_create_concept(item.id).status == "mastered"
            for item in graph.concepts
        )
        current = next(
            (
                item.id
                for item in graph.concepts
                if learner.get_or_create_concept(item.id).status
                in {"learning", "weak", "familiar"}
            ),
            None,
        )
        selection = self._next_selection(graph, learner, subject_id)
        self.repository.save_learner(subject_id, learner)
        return {
            "subject": subject_id,
            "learner": learner_id,
            "progress": round(mastered / len(graph.concepts), 6) if graph.concepts else 0.0,
            "mastered": mastered,
            "total_concepts": len(graph.concepts),
            "current": current,
            "next": selection.concept,
            "active_session": learner.active_session_id,
        }

    def start_session(
        self, subject_id: str, learner_id: str = "default"
    ) -> dict[str, Any]:
        _, learner = self._load(subject_id, learner_id)
        if learner.active_session_id is not None:
            raise ValueError(f"learning session already active: {learner.active_session_id}")
        started_at = utc_now()
        session = LearningSession(
            id=f"session_{uuid4().hex}",
            subject_id=subject_id,
            learner_id=learner_id,
            started_at=started_at,
        )
        session.add_event("session_started", at=started_at)
        learner.active_session_id = session.id
        self.repository.save_learning_session(session)
        self.repository.save_learner(subject_id, learner)
        return session.to_dict()

    def end_session(
        self, subject_id: str, learner_id: str = "default"
    ) -> dict[str, Any]:
        _, learner = self._load(subject_id, learner_id)
        if learner.active_session_id is None:
            raise ValueError("no active learning session")
        session = self.repository.load_learning_session(
            subject_id, learner.active_session_id, learner_id
        )
        session.end()
        learner.active_session_id = None
        self.repository.save_learning_session(session)
        self.repository.save_learner(subject_id, learner)
        return session.to_dict()

    def session_history(
        self, subject_id: str, learner_id: str = "default"
    ) -> dict[str, Any]:
        self._load(subject_id, learner_id)
        sessions = self.repository.list_learning_sessions(subject_id, learner_id)
        return {
            "subject": subject_id,
            "learner": learner_id,
            "sessions": [session.to_dict() for session in sessions],
        }

    def progress_report(
        self, subject_id: str, learner_id: str = "default"
    ) -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        DependencyEngine(graph, learner).refresh()
        states = [learner.get_or_create_concept(item.id) for item in graph.concepts]
        distribution = {
            status: sum(state.status == status for state in states)
            for status in ("locked", "available", "learning", "weak", "familiar", "mastered")
        }
        sessions = self.repository.list_learning_sessions(subject_id, learner_id)
        attempts = self.repository.list_attempts(subject_id, learner_id)
        review_attempts = [attempt for attempt in attempts if attempt.get("purpose") == "review"]
        review_scores = [
            sum(float(item["score"]) for item in attempt.get("assessments", []))
            / len(attempt["assessments"])
            for attempt in review_attempts
            if attempt.get("assessments")
        ]
        unresolved = sum(
            not misconception.resolved
            for state in states
            for misconception in state.misconceptions
        )
        due_count = len(ReviewScheduler().due_concepts(learner))
        mastered = distribution["mastered"]
        completed_sessions = sum(session.ended_at is not None for session in sessions)
        last_activity = max(
            [
                value
                for state in states
                for value in (state.last_learned, state.mastery.updated_at)
                if value is not None
            ]
            + [session.ended_at or session.started_at for session in sessions],
            default=None,
        )
        self.repository.save_learner(subject_id, learner)
        return {
            "subject": subject_id,
            "learner": learner_id,
            "concepts": len(states),
            "mastered": mastered,
            "progress": round(mastered / len(states), 6) if states else 0.0,
            "average_mastery": round(sum(state.mastery.score for state in states) / len(states), 6) if states else 0.0,
            "average_confidence": round(sum(state.mastery.confidence for state in states) / len(states), 6) if states else 0.0,
            "status_distribution": distribution,
            "attempts": sum(state.attempt_count for state in states),
            "quiz_attempt_records": len(attempts),
            "unresolved_misconceptions": unresolved,
            "due_reviews": due_count,
            "review_retention": round(sum(review_scores) / len(review_scores), 6) if review_scores else None,
            "sessions": len(sessions),
            "completed_sessions": completed_sessions,
            "mastered_per_completed_session": round(mastered / completed_sessions, 6) if completed_sessions else None,
            "active_session": learner.active_session_id,
            "last_activity": last_activity,
        }

    def doctor(
        self, subject_id: str, learner_id: str = "default"
    ) -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        graph.validate_graph()
        sessions = self.repository.list_learning_sessions(subject_id, learner_id)
        attempts = self.repository.list_attempts(subject_id, learner_id)
        if learner.active_session_id is not None:
            self.repository.load_learning_session(
                subject_id, learner.active_session_id, learner_id
            )
        return {
            "status": "ok",
            "schema_version": SCHEMA_VERSION,
            "subject": subject_id,
            "learner": learner_id,
            "concepts": len(graph.concepts),
            "relations": len(graph.relations),
            "sessions": len(sessions),
            "attempts": len(attempts),
            "active_session": learner.active_session_id,
            "recovered_from_backup": list(self.repository.recoveries),
            "blueprint": self.repository.blueprint_exists(subject_id),
        }

    def create_blueprint(
        self,
        subject_id: str,
        payload: Mapping[str, Any],
        learner_id: str = "default",
    ) -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        if self.repository.blueprint_exists(subject_id):
            raise StorageError(f"blueprint already exists: {subject_id}")
        expanded, blueprint = build_blueprint(graph, payload)
        DependencyEngine(expanded, learner).refresh()
        self.repository.save_graph(expanded)
        self.repository.save_blueprint(blueprint)
        self.repository.save_learner(subject_id, learner)
        self._record_event(
            subject_id,
            learner,
            "blueprint_created",
            {
                "landscape_sections": len(blueprint.landscape),
                "backbone_concepts": len(blueprint.core_backbone),
                "advanced_directions": len(blueprint.advanced_directions),
            },
        )
        return self.blueprint_view(subject_id, learner_id)

    def blueprint_view(
        self, subject_id: str, learner_id: str = "default"
    ) -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        blueprint = self.repository.load_blueprint(subject_id)
        concept_map = {concept.id: concept for concept in graph.concepts}
        value = blueprint.to_dict()
        value["landscape"] = [
            {
                **section.to_dict(),
                "concepts": [
                    {
                        "id": concept_id,
                        "name": concept_map[concept_id].name,
                        "depth": concept_map[concept_id].depth,
                        "status": learner.get_or_create_concept(concept_id).status,
                    }
                    for concept_id in section.concept_ids
                ],
            }
            for section in blueprint.landscape
        ]
        value["expansion_candidates"] = [
            concept.id
            for concept in graph.concepts
            if concept.metadata.get("expandable", False)
            and concept.id != graph.subject_id
        ]
        backbone_ids = {item.concept_id for item in blueprint.core_backbone}
        value["core_dependencies"] = [
            {
                "source": relation.source,
                "target": relation.target,
                "threshold": relation.threshold,
            }
            for relation in graph.relations
            if relation.type == "prerequisite"
            and relation.source in backbone_ids
            and relation.target in backbone_ids
        ]
        return value

    def roadmap(
        self, subject_id: str, learner_id: str = "default"
    ) -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        DependencyEngine(graph, learner).refresh()
        blueprint = self.repository.load_blueprint(subject_id)
        concept_map = {concept.id: concept for concept in graph.concepts}
        roadmap_items = self._roadmap_items(graph, blueprint)
        grouped: dict[int, list] = {}
        for item in roadmap_items:
            level = getattr(item, "topological_layer", None)
            if level is None:
                level = max(0, item.stage - 1)
            grouped.setdefault(level, []).append(item)
        stages = []
        stage_names = ("Foundation", "Core", "Application", "Advanced", "Integration")
        current_assigned = False
        for number, level in enumerate(sorted(grouped), start=1):
            concepts = []
            for backbone in grouped[level]:
                state = learner.get_or_create_concept(backbone.concept_id)
                concepts.append(
                    {
                        "id": backbone.concept_id,
                        "name": concept_map[backbone.concept_id].name,
                        "status": state.status,
                        "mastery": state.mastery.to_dict(),
                        "leverage_score": backbone.leverage_score,
                        "core_score": backbone.core_score,
                        "inclusion_type": backbone.inclusion_type,
                        "selection_reason": backbone.selection_reason,
                    }
                )
            if all(item["status"] == "mastered" for item in concepts):
                status = "completed"
            elif not current_assigned:
                status = "current"
                current_assigned = True
            else:
                status = "upcoming"
            stages.append(
                {
                    "stage": number,
                    "id": f"stage_{number}",
                    "name": stage_names[min(number - 1, len(stage_names) - 1)],
                    "dependency_level": level,
                    "status": status,
                    "concepts": concepts,
                }
            )
        return {
            "subject": subject_id,
            "goal_id": blueprint.scope.goal_id or f"goal_{subject_id}_primary",
            "goal": blueprint.scope.goal,
            "target_level": blueprint.scope.target_level,
            "orientation": blueprint.scope.orientation,
            "time_budget": {
                "hours_per_week": blueprint.scope.weekly_hours,
                "target_months": blueprint.scope.target_months,
            },
            "version": blueprint.revision,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mvlg_concept_count": len(roadmap_items),
            "stages": stages,
        }

    def directions(
        self, subject_id: str, learner_id: str = "default"
    ) -> dict[str, Any]:
        _, learner = self._load(subject_id, learner_id)
        blueprint = self.repository.load_blueprint(subject_id)
        return {
            "subject": subject_id,
            "directions": [
                {
                    **direction.to_dict(),
                    "entry_ready": all(
                        learner.get_mastery(concept_id).score >= 0.8
                        for concept_id in direction.entry_concept_ids
                    ),
                }
                for direction in blueprint.advanced_directions
            ],
        }

    def graph_view(self, subject_id: str, learner_id: str = "default") -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        DependencyEngine(graph, learner).refresh()
        self.repository.save_learner(subject_id, learner)
        return {
            "subject": subject_id,
            "concepts": [
                {
                    **concept.to_dict(),
                    "learner": learner.get_or_create_concept(concept.id).to_dict(),
                }
                for concept in graph.concepts
            ],
            "relations": [relation.to_dict() for relation in graph.relations],
        }

    def next_concept(
        self, subject_id: str, learner_id: str = "default"
    ) -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        selection = self._next_selection(graph, learner, subject_id)
        self.repository.save_learner(subject_id, learner)
        return selection.to_dict()

    def learn(
        self,
        subject_id: str,
        learner_id: str = "default",
        concept_id: str | None = None,
    ) -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        dependencies = DependencyEngine(graph, learner)
        if concept_id is None:
            concept_id = self._next_selection(graph, learner, subject_id).concept
        if concept_id is None:
            raise ValueError("no concept is currently available to learn")
        concept = graph.get_concept(concept_id)
        state = learner.get_or_create_concept(concept_id)
        if state.status == "mastered":
            raise ValueError(f"concept is already mastered: {concept_id}")
        if not dependencies.unlock(concept_id):
            raise ValueError(f"concept is locked: {concept_id}")
        state.status = "learning"
        self.repository.save_learner(subject_id, learner)
        self._record_event(subject_id, learner, "concept_started", {"concept": concept.id})
        return {
            "concept": concept.id,
            "name": concept.name,
            "status": state.status,
            "description": concept.description,
        }

    def evaluate(
        self,
        subject_id: str,
        concept_id: str,
        evidence: Mapping[str, float],
        learner_id: str = "default",
    ) -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        graph.get_concept(concept_id)
        result = MasteryEvaluator().update_mastery(learner, concept_id, evidence)
        state = learner.get_or_create_concept(concept_id)
        if state.status == "mastered":
            ReviewScheduler().schedule_after_mastery(state)
        DependencyEngine(graph, learner).refresh()
        self.repository.save_learner(subject_id, learner)
        self._record_event(
            subject_id,
            learner,
            "mastery_updated",
            {"concept": concept_id, "score": state.mastery.score, "status": state.status},
        )
        return {
            "concept": concept_id,
            "evaluation": asdict(result),
            "mastery": state.mastery.to_dict(),
            "status": state.status,
            "next": self._next_selection(graph, learner, subject_id).to_dict(),
        }

    def review(self, subject_id: str, learner_id: str = "default") -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        graph_ids = {concept.id for concept in graph.concepts}
        due = [
            {
                "concept": state.concept_id,
                "scheduled_at": state.review.next_review,
                "mastery": state.mastery.to_dict(),
            }
            for state in ReviewScheduler().due_concepts(learner)
            if state.concept_id in graph_ids
        ]
        candidates = []
        for state in learner.concepts.values():
            unresolved = [
                item.to_dict() for item in state.misconceptions if not item.resolved
            ]
            if state.concept_id in graph_ids and state.attempt_count > 0 and (
                state.status != "mastered" or unresolved
            ):
                candidates.append(
                    {
                        "concept": state.concept_id,
                        "status": state.status,
                        "mastery": state.mastery.to_dict(),
                        "misconceptions": unresolved,
                    }
                )
        candidates.sort(
            key=lambda item: (item["mastery"]["score"], item["concept"])
        )
        return {
            "subject": subject_id,
            "due_reviews": due,
            "remediation_candidates": candidates,
            "review_candidates": due + candidates,
        }

    def expand_subject(
        self,
        subject_id: str,
        anchor_concept_id: str,
        expansion: Mapping[str, Any],
        learner_id: str = "default",
    ) -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        concepts = [Concept.from_dict(item) for item in expansion.get("concepts", [])]
        if self.repository.blueprint_exists(subject_id):
            scope = self.repository.load_blueprint(subject_id).scope
            for concept in concepts:
                tags = concept.metadata.get("scope_tags")
                if not isinstance(tags, (list, tuple)) or not tags:
                    raise BlueprintValidationError(
                        f"expanded concept {concept.id} requires metadata.scope_tags"
                    )
                excluded = set(tags) & set(scope.excluded)
                if excluded:
                    raise BlueprintValidationError(
                        f"concept {concept.id} violates excluded scope: {sorted(excluded)}"
                    )
        relations = [Relation.from_dict(item) for item in expansion.get("relations", [])]
        expanded = expand_graph(graph, anchor_concept_id, concepts, relations)
        DependencyEngine(expanded, learner).refresh()
        self.repository.save_graph(expanded)
        self.repository.save_learner(subject_id, learner)
        self._record_event(
            subject_id,
            learner,
            "graph_expanded",
            {"anchor": anchor_concept_id, "concepts": [item.id for item in concepts]},
        )
        return {
            "subject": subject_id,
            "anchor": anchor_concept_id,
            "added_concepts": [item.id for item in concepts],
            "added_relations": [item.id for item in relations],
            "total_concepts": len(expanded.concepts),
        }

    def register_quiz(
        self,
        quiz_data: Mapping[str, Any],
        learner_id: str = "default",
    ) -> dict[str, Any]:
        quiz = Quiz.from_dict(quiz_data)
        graph, _ = self._load(quiz.subject_id, learner_id)
        graph.get_concept(quiz.concept_id)
        self.repository.save_quiz(quiz, learner_id)
        return quiz.to_dict()

    def submit_quiz(
        self,
        subject_id: str,
        quiz_id: str,
        answers: Mapping[str, str],
        assessment_data: list[Mapping[str, Any]],
        learner_id: str = "default",
    ) -> dict[str, Any]:
        graph, learner = self._load(subject_id, learner_id)
        quiz = self.repository.load_quiz(subject_id, quiz_id, learner_id)
        assessments = tuple(
            AnswerAssessment.from_dict(item) for item in assessment_data
        )
        quiz_result = QuizEvaluator().evaluate(quiz, answers, assessments)
        mastery_result = MasteryEvaluator().update_mastery(
            learner, quiz.concept_id, quiz_result.evidence
        )
        state = learner.get_or_create_concept(quiz.concept_id)
        scheduler = ReviewScheduler()
        if quiz.purpose == "review":
            scheduler.record_review(state, quiz_result.score)
        elif state.status == "mastered":
            scheduler.schedule_after_mastery(state)
        known = {item.id: item for item in state.misconceptions}
        for assessment in assessments:
            for detected in assessment.misconceptions:
                if detected.id in known:
                    item = known[detected.id]
                    item.description = detected.description
                    item.severity = max(item.severity, detected.severity)
                    item.resolved = False
                    item.resolved_at = None
                else:
                    item = Misconception(
                        detected.id, detected.description, detected.severity
                    )
                    state.misconceptions.append(item)
                    known[item.id] = item
        DependencyEngine(graph, learner).refresh()
        attempt = QuizAttempt(
            id=f"attempt_{uuid4().hex}",
            quiz_id=quiz.id,
            subject_id=subject_id,
            concept_id=quiz.concept_id,
            learner_id=learner_id,
            answers=dict(answers),
            assessments=assessments,
            created_at=datetime.now(timezone.utc).isoformat(),
            purpose=quiz.purpose,
        )
        self.repository.save_learner(subject_id, learner)
        self.repository.save_attempt(attempt)
        self._record_event(
            subject_id,
            learner,
            "quiz_submitted",
            {
                "quiz": quiz.id,
                "concept": quiz.concept_id,
                "purpose": quiz.purpose,
                "score": quiz_result.score,
                "status": state.status,
            },
        )
        return {
            "attempt_id": attempt.id,
            "quiz": quiz.id,
            "purpose": quiz.purpose,
            "concept": quiz.concept_id,
            "quiz_score": quiz_result.score,
            "mastery_evidence": dict(quiz_result.evidence),
            "mastery_evaluation": asdict(mastery_result),
            "mastery": state.mastery.to_dict(),
            "status": state.status,
            "misconceptions": [
                item.to_dict() for item in state.misconceptions if not item.resolved
            ],
            "next": self._next_selection(graph, learner, subject_id).to_dict(),
        }

    def _load(self, subject_id: str, learner_id: str):
        graph = self.repository.load_graph(subject_id)
        learner = self.repository.load_learner(subject_id, learner_id)
        unknown = set(learner.concepts) - {item.id for item in graph.concepts}
        if unknown:
            raise StorageError(
                f"learner state references unknown concepts: {sorted(unknown)}"
            )
        return graph, learner

    def _next_selection(self, graph, learner, subject_id: str):
        planner = CurriculumPlanner(graph, learner)
        if not self.repository.blueprint_exists(subject_id):
            return planner.next_concept()
        blueprint = self.repository.load_blueprint(subject_id)
        by_stage: dict[int, set[str]] = {}
        for item in self._roadmap_items(graph, blueprint):
            stage = getattr(item, "topological_layer", None)
            if stage is None:
                stage = max(0, item.stage - 1)
            by_stage.setdefault(stage, set()).add(item.concept_id)
        for stage in sorted(by_stage):
            incomplete = {
                concept_id
                for concept_id in by_stage[stage]
                if learner.get_or_create_concept(concept_id).status != "mastered"
            }
            if not incomplete:
                continue
            selection = planner.next_concept(incomplete)
            if selection.concept is not None:
                return selection
            break
        return planner.next_concept()

    @staticmethod
    def _roadmap_items(graph, blueprint):
        """Dynamically query the MVLG for new Blueprints; preserve legacy files."""
        if not blueprint.selection_config:
            return blueprint.core_backbone
        config = RoadmapConfig(**dict(blueprint.selection_config))
        return analyze_roadmap(graph, config).concepts

    def _record_event(
        self,
        subject_id: str,
        learner,
        event_type: str,
        data: Mapping[str, Any],
    ) -> None:
        if learner.active_session_id is None:
            return
        session = self.repository.load_learning_session(
            subject_id, learner.active_session_id, learner.learner_id
        )
        session.add_event(event_type, data)
        self.repository.save_learning_session(session)
