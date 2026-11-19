"""SQLAlchemy implementation of the Trainer persistence port."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from pokerhelper.application.training_repository import TrainingRepository
from pokerhelper.domain.errors import fail

from .database import Database, DecisionRow, TrainingSessionRow, json_text, parse_json


class SqlAlchemyTrainingRepository(TrainingRepository):
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_session(self, record: dict[str, Any]) -> dict[str, Any]:
        row = TrainingSessionRow(
            session_id=record["sessionId"],
            schema_version=record["schemaVersion"],
            status=record["status"],
            scenario_id=record["scenarioId"],
            solution_id=record["solutionId"],
            solution_version=record["solutionVersion"],
            selected_node_ids_json=json_text(record["selectedNodeIds"]),
            hero_positions_json=json_text(record["heroPositions"]),
            target_decisions=record["targetDecisions"],
            feedback_mode=record["feedbackMode"],
            scoring_policy_version=record["scoringPolicyVersion"],
            sampling_policy_version=record["samplingPolicyVersion"],
            accuracy_mode=record["accuracyMode"],
            approximate_acknowledged_at=record.get("approximateAcknowledgedAt"),
            rng_enabled=int(record["rngEnabled"]),
            drill_type=record["drillType"],
            source_session_id=record.get("sourceSessionId"),
            drill_items_json=json_text(record.get("drillItems", [])),
            pending_prompt_json=None,
            started_at=record["startedAt"],
            completed_at=None,
            summary_json=json_text(record["summary"]),
        )
        try:
            with self.database.session() as database_session:
                database_session.add(row)
        except IntegrityError as exc:
            fail("TRAINER_SESSION_CONFLICT", "sessionId", "The training session could not be created.", details={"reason": str(exc.orig)})
        return self.get_session(record["sessionId"])

    def get_session(self, session_id: str) -> dict[str, Any]:
        with self.database.session() as database_session:
            row = database_session.get(TrainingSessionRow, session_id)
            if row is None:
                _session_not_found(session_id)
            return _session_record(row)

    def list_sessions(self) -> list[dict[str, Any]]:
        with self.database.session() as database_session:
            rows = database_session.scalars(
                select(TrainingSessionRow).order_by(TrainingSessionRow.started_at.desc())
            ).all()
            return [_session_record(row) for row in rows]

    def list_decisions(self, session_id: str) -> list[dict[str, Any]]:
        self.get_session(session_id)
        with self.database.session() as database_session:
            rows = database_session.scalars(
                select(DecisionRow)
                .where(DecisionRow.session_id == session_id)
                .order_by(DecisionRow.sequence)
            ).all()
            return [_decision_record(row) for row in rows]

    def list_all_decisions(self) -> list[dict[str, Any]]:
        with self.database.session() as database_session:
            rows = database_session.scalars(
                select(DecisionRow).order_by(DecisionRow.answered_at)
            ).all()
            return [_decision_record(row) for row in rows]

    def get_decision(self, session_id: str, decision_id: str) -> dict[str, Any]:
        with self.database.session() as database_session:
            row = database_session.get(DecisionRow, decision_id)
            if row is None or row.session_id != session_id:
                fail(
                    "TRAINER_DECISION_NOT_FOUND",
                    "decisionId",
                    "The requested training decision does not exist.",
                    details={"decisionId": decision_id},
                )
            return _decision_record(row)

    def get_decision_by_prompt(self, prompt_id: str) -> dict[str, Any] | None:
        with self.database.session() as database_session:
            row = database_session.scalar(select(DecisionRow).where(DecisionRow.prompt_id == prompt_id))
            return _decision_record(row) if row is not None else None

    def save_prompt(self, session_id: str, prompt: dict[str, Any]) -> dict[str, Any]:
        with self.database.session() as database_session:
            row = database_session.get(TrainingSessionRow, session_id)
            if row is None:
                _session_not_found(session_id)
            if row.status != "ACTIVE":
                fail("TRAINER_SESSION_NOT_ACTIVE", "sessionId", "Only an active session can present another decision.")
            row.pending_prompt_json = json_text(prompt)
        return self.get_session(session_id)

    def append_decision(
        self,
        session_id: str,
        prompt_id: str,
        decision: dict[str, Any],
        summary: dict[str, Any],
        *,
        completed_at: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        with self.database.session() as database_session:
            duplicate = database_session.scalar(select(DecisionRow).where(DecisionRow.prompt_id == prompt_id))
            if duplicate is not None:
                return _session_record(database_session.get(TrainingSessionRow, duplicate.session_id)), _decision_record(duplicate)
            session_row = database_session.get(TrainingSessionRow, session_id)
            if session_row is None:
                _session_not_found(session_id)
            if session_row.status != "ACTIVE":
                fail("TRAINER_SESSION_NOT_ACTIVE", "sessionId", "Only an active session accepts decisions.")
            pending = parse_json(session_row.pending_prompt_json)
            if pending is None or pending.get("promptId") != prompt_id:
                fail("TRAINER_PROMPT_STALE", "promptId", "This prompt is no longer the active decision.")
            row = _new_decision_row(decision)
            database_session.add(row)
            session_row.pending_prompt_json = None
            session_row.summary_json = json_text(summary)
            if completed_at is not None:
                session_row.status = "COMPLETED"
                session_row.completed_at = completed_at
            database_session.flush()
            session_record = _session_record(session_row)
            decision_record = _decision_record(row)
        return session_record, decision_record

    def complete_session(self, session_id: str, *, completed_at: str) -> dict[str, Any]:
        with self.database.session() as database_session:
            row = database_session.get(TrainingSessionRow, session_id)
            if row is None:
                _session_not_found(session_id)
            if row.status != "ACTIVE":
                return _session_record(row)
            completed = database_session.scalar(
                select(DecisionRow.decision_id).where(DecisionRow.session_id == session_id).limit(1)
            )
            row.status = "COMPLETED" if completed is not None else "ABANDONED"
            row.completed_at = completed_at
            row.pending_prompt_json = None
        return self.get_session(session_id)

    def delete_session(self, session_id: str) -> None:
        with self.database.session() as database_session:
            row = database_session.get(TrainingSessionRow, session_id)
            if row is None:
                _session_not_found(session_id)
            database_session.delete(row)


def _session_record(row: TrainingSessionRow) -> dict[str, Any]:
    return {
        "sessionId": row.session_id,
        "schemaVersion": row.schema_version,
        "status": row.status,
        "scenarioId": row.scenario_id,
        "solutionId": row.solution_id,
        "solutionVersion": row.solution_version,
        "selectedNodeIds": parse_json(row.selected_node_ids_json, []),
        "heroPositions": parse_json(row.hero_positions_json, []),
        "targetDecisions": row.target_decisions,
        "feedbackMode": row.feedback_mode,
        "scoringPolicyVersion": row.scoring_policy_version,
        "samplingPolicyVersion": row.sampling_policy_version,
        "accuracyMode": row.accuracy_mode,
        "approximateAcknowledgedAt": row.approximate_acknowledged_at,
        "rngEnabled": bool(row.rng_enabled),
        "drillType": row.drill_type,
        "sourceSessionId": row.source_session_id,
        "drillItems": parse_json(row.drill_items_json, []),
        "pendingPrompt": parse_json(row.pending_prompt_json),
        "startedAt": row.started_at,
        "completedAt": row.completed_at,
        "summary": parse_json(row.summary_json, {}),
    }


def _decision_record(row: DecisionRow) -> dict[str, Any]:
    return {
        "decisionId": row.decision_id,
        "promptId": row.prompt_id,
        "sessionId": row.session_id,
        "sequence": row.sequence,
        "scenarioId": row.scenario_id,
        "gameConfigId": row.game_config_id,
        "solutionId": row.solution_id,
        "solutionVersion": row.solution_version,
        "nodeId": row.node_id,
        "heroPosition": row.hero_position,
        "actionHistoryKey": row.action_history_key,
        "heroCombo": row.hero_combo,
        "groupedHand": row.grouped_hand,
        "offeredOptions": parse_json(row.offered_options_json, []),
        "selectedOptionId": row.selected_option_id,
        "selectedResolvedAction": parse_json(row.selected_resolved_action_json, {}),
        "comboReachWeight": row.combo_reach_weight,
        "referenceSnapshot": parse_json(row.reference_snapshot_json, []),
        "highestEvOptionId": row.highest_ev_option_id,
        "evLossBb": row.ev_loss_bb,
        "feedbackSeverity": row.feedback_severity,
        "strategyStatus": row.strategy_status,
        "scoringPolicyVersion": row.scoring_policy_version,
        "accuracyMode": row.accuracy_mode,
        "rngRoll": row.rng_roll,
        "rngMapping": parse_json(row.rng_mapping_json),
        "presentedAt": row.presented_at,
        "answeredAt": row.answered_at,
        "interpretation": row.interpretation,
    }


def _new_decision_row(record: dict[str, Any]) -> DecisionRow:
    return DecisionRow(
        decision_id=record["decisionId"],
        prompt_id=record["promptId"],
        session_id=record["sessionId"],
        sequence=record["sequence"],
        scenario_id=record["scenarioId"],
        game_config_id=record["gameConfigId"],
        solution_id=record["solutionId"],
        solution_version=record["solutionVersion"],
        node_id=record["nodeId"],
        hero_position=record["heroPosition"],
        action_history_key=record["actionHistoryKey"],
        hero_combo=record["heroCombo"],
        grouped_hand=record["groupedHand"],
        offered_options_json=json_text(record["offeredOptions"]),
        selected_option_id=record["selectedOptionId"],
        selected_resolved_action_json=json_text(record["selectedResolvedAction"]),
        combo_reach_weight=record["comboReachWeight"],
        reference_snapshot_json=json_text(record["referenceSnapshot"]),
        highest_ev_option_id=record["highestEvOptionId"],
        ev_loss_bb=record["evLossBb"],
        feedback_severity=record["feedbackSeverity"],
        strategy_status=record["strategyStatus"],
        scoring_policy_version=record["scoringPolicyVersion"],
        accuracy_mode=record["accuracyMode"],
        rng_roll=record.get("rngRoll"),
        rng_mapping_json=json_text(record["rngMapping"]) if record.get("rngMapping") is not None else None,
        presented_at=record["presentedAt"],
        answered_at=record["answeredAt"],
        interpretation=record["interpretation"],
    )


def _session_not_found(session_id: str) -> None:
    fail(
        "TRAINER_SESSION_NOT_FOUND",
        "sessionId",
        "The requested training session does not exist.",
        details={"sessionId": session_id},
    )
