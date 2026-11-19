"""Phase 3 Trainer orchestration over immutable solutions and durable records."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import random
from typing import Any, Callable, Iterable
from uuid import uuid4

from pokerhelper.application.catalog import StudyCatalog
from pokerhelper.application.solution_rules import SolutionRuleValidator, resolved_action_json
from pokerhelper.application.training_repository import TrainingRepository
from pokerhelper.domain.decimal_utils import normalized_decimal
from pokerhelper.domain.errors import fail
from pokerhelper.domain.trainer import (
    CALIBRATION_MINIMUM_SAMPLE,
    FREQUENCY_SUPPORT_TOLERANCE,
    SAMPLING_POLICY_VERSION,
    SCORING_POLICY_VERSION,
    FeedbackSeverity,
    RandomIndexSource,
    ReferenceAction,
    rng_bands,
    score_decision,
    weighted_index,
)


SESSION_SCHEMA_VERSION = "1.0.0"
VALID_FEEDBACK_MODES = {"IMMEDIATE", "DELAYED"}
VALID_POSITIONS = {"SB", "BB"}


class SystemRandomSource(RandomIndexSource):
    def __init__(self) -> None:
        self._random = random.SystemRandom()

    def randbelow(self, upper: int) -> int:
        return self._random.randrange(upper)


class TrainingService:
    def __init__(
        self,
        catalog: StudyCatalog,
        repository: TrainingRepository,
        *,
        rule_validator: SolutionRuleValidator | None = None,
        randomizer: RandomIndexSource | None = None,
        clock: Callable[[], str] | None = None,
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        self.catalog = catalog
        self.repository = repository
        self.rule_validator = rule_validator or catalog.rule_validator
        self.randomizer = randomizer or SystemRandomSource()
        self.clock = clock or _utc_now
        self.id_factory = id_factory or (lambda prefix: f"{prefix}:{uuid4()}")

    def create_session(self, command: dict[str, Any]) -> dict[str, Any]:
        return self._create_session(command, drill_type="STANDARD", source_session_id=None, drill_items=[])

    def repeat_session(self, session_id: str) -> dict[str, Any]:
        source = self.repository.get_session(session_id)
        command = {
            "scenarioId": source["scenarioId"],
            "nodeIds": source["selectedNodeIds"],
            "heroPositions": source["heroPositions"],
            "targetDecisions": source["targetDecisions"],
            "feedbackMode": source["feedbackMode"],
            "rngEnabled": source["rngEnabled"],
            "acknowledgeApproximate": source["accuracyMode"] == "REFERENCE_MODEL",
        }
        return self._create_session(command, drill_type="REPEAT", source_session_id=session_id, drill_items=[])

    def redrill(self, session_id: str, mode: str) -> dict[str, Any]:
        source = self.repository.get_session(session_id)
        decisions = self.repository.list_decisions(session_id)
        if not decisions:
            fail("TRAINER_REDRILL_EMPTY", "sessionId", "A session needs completed decisions before a targeted drill can be created.")
        if mode == "MISTAKES":
            selected = [
                item for item in decisions
                if item["feedbackSeverity"] in {
                    FeedbackSeverity.SIGNIFICANT_MISTAKE.value,
                    FeedbackSeverity.MAJOR_MISTAKE.value,
                }
            ]
            if not selected:
                selected = [item for item in decisions if Decimal(item["evLossBb"]) > Decimal("0.010")]
            if not selected:
                selected = sorted(decisions, key=lambda item: Decimal(item["evLossBb"]), reverse=True)[:5]
            drill_type = "MISTAKE_REVIEW"
        elif mode == "CLOSE_DECISIONS":
            selected = [item for item in decisions if _is_close_mixed_decision(item)]
            if not selected:
                selected = sorted(decisions, key=lambda item: Decimal(item["evLossBb"]))[:5]
            drill_type = "CLOSE_DECISIONS"
        else:
            fail("TRAINER_REDRILL_MODE_INVALID", "mode", "Redrill mode must be MISTAKES or CLOSE_DECISIONS.")
        selected = sorted(selected, key=lambda item: Decimal(item["evLossBb"]), reverse=mode == "MISTAKES")[:20]
        items = _unique_drill_items(selected)
        target = min(20, max(10, len(items) * 3))
        command = {
            "scenarioId": source["scenarioId"],
            "nodeIds": sorted({item["nodeId"] for item in items}),
            "heroPositions": sorted({item["heroPosition"] for item in selected}),
            "targetDecisions": target,
            "feedbackMode": source["feedbackMode"],
            "rngEnabled": source["rngEnabled"],
            "acknowledgeApproximate": source["accuracyMode"] == "REFERENCE_MODEL",
        }
        return self._create_session(
            command,
            drill_type=drill_type,
            source_session_id=session_id,
            drill_items=items,
        )

    def next_prompt(self, session_id: str) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        if session["status"] != "ACTIVE":
            fail("TRAINER_SESSION_NOT_ACTIVE", "sessionId", "This training session is no longer active.")
        if session["pendingPrompt"] is not None:
            return _public_prompt(session["pendingPrompt"])

        artifact = self.catalog.store.get(session["solutionId"])
        if session["drillItems"]:
            item = session["drillItems"][self.randomizer.randbelow(len(session["drillItems"]))]
            node_id = item["nodeId"]
            combo = item["heroCombo"]
        else:
            node_id = session["selectedNodeIds"][self.randomizer.randbelow(len(session["selectedNodeIds"]))]
            node_for_sampling = artifact.node(node_id)
            combos = sorted(node_for_sampling["exactCombos"])
            weights = [node_for_sampling["exactCombos"][combo]["reachFrequency"] for combo in combos]
            combo = combos[weighted_index(weights, self.randomizer)]

        node = artifact.node(node_id)
        strategy = node["exactCombos"][combo]
        if Decimal(strategy["reachFrequency"]) <= 0:
            fail("TRAINER_SAMPLED_UNREACHABLE_COMBO", "heroCombo", "The sampled exact combo has zero reach weight.")
        validated = self.rule_validator.validate(artifact, node_id)
        sequence = int(session["summary"]["decisionsCompleted"]) + 1
        prompt = {
            "promptId": self.id_factory("prompt"),
            "sessionId": session_id,
            "sequence": sequence,
            "targetDecisions": session["targetDecisions"],
            "scenarioId": session["scenarioId"],
            "solutionId": session["solutionId"],
            "solutionVersion": session["solutionVersion"],
            "nodeId": node_id,
            "heroPosition": node["actor"],
            "heroCombo": combo,
            "groupedHand": strategy["group"],
            "comboReachWeight": strategy["reachFrequency"],
            "actionHistory": node["actionHistory"],
            "potBb": node["potBb"],
            "amountToCallBb": node["amountToCallBb"],
            "actorStackBehindBb": node["actorStackBehindBb"],
            "offeredOptions": [
                {
                    **option,
                    "resolvedAction": resolved_action_json(validated.resolved_actions[option["actionId"]]),
                }
                for option in node["actions"]
            ],
            "feedbackMode": session["feedbackMode"],
            "accuracyMode": session["accuracyMode"],
            "rngAvailable": session["rngEnabled"],
            "rngRoll": None,
            "rngMapping": None,
            "presentedAt": self.clock(),
        }
        self.repository.save_prompt(session_id, prompt)
        return _public_prompt(prompt)

    def show_rng(self, session_id: str) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        prompt = session["pendingPrompt"]
        if session["status"] != "ACTIVE" or prompt is None:
            fail("TRAINER_PROMPT_REQUIRED", "sessionId", "Present a training decision before requesting an RNG roll.")
        if not session["rngEnabled"]:
            fail("TRAINER_RNG_DISABLED", "sessionId", "The optional RNG aid was not enabled for this session.")
        if prompt["rngRoll"] is not None:
            return {"roll": prompt["rngRoll"], "mapping": prompt["rngMapping"]}
        artifact = self.catalog.store.get(session["solutionId"])
        node = artifact.node(prompt["nodeId"])
        strategy = node["exactCombos"][prompt["heroCombo"]]
        reference = _reference_actions(node, strategy)
        labels = {option["actionId"]: option["label"] for option in node["actions"]}
        mapping = [
            {"optionId": band.option_id, "label": labels[band.option_id], "start": band.start, "end": band.end}
            for band in rng_bands(reference)
        ]
        prompt["rngRoll"] = self.randomizer.randbelow(100) + 1
        prompt["rngMapping"] = mapping
        self.repository.save_prompt(session_id, prompt)
        return {"roll": prompt["rngRoll"], "mapping": mapping}

    def submit_decision(self, session_id: str, prompt_id: str, selected_option_id: str) -> dict[str, Any]:
        duplicate = self.repository.get_decision_by_prompt(prompt_id)
        if duplicate is not None:
            if duplicate["sessionId"] != session_id:
                fail("TRAINER_PROMPT_STALE", "promptId", "The prompt belongs to a different session.")
            session = self.repository.get_session(session_id)
            return self._submission_response(session, duplicate)

        session = self.repository.get_session(session_id)
        prompt = session["pendingPrompt"]
        if session["status"] != "ACTIVE" or prompt is None or prompt["promptId"] != prompt_id:
            fail("TRAINER_PROMPT_STALE", "promptId", "This prompt is no longer the active decision.")
        offered = {option["actionId"]: option for option in prompt["offeredOptions"]}
        if selected_option_id not in offered:
            fail("TRAINER_OPTION_NOT_OFFERED", "selectedOptionId", "The selected action was not offered for this decision.")

        artifact = self.catalog.store.get(session["solutionId"])
        node = artifact.node(prompt["nodeId"])
        validated = self.rule_validator.validate(artifact, prompt["nodeId"])
        selected_resolved = validated.resolved_actions[selected_option_id]
        strategy = node["exactCombos"].get(prompt["heroCombo"])
        if strategy is None or Decimal(strategy["reachFrequency"]) <= 0:
            fail("TRAINER_COMBO_NOT_AVAILABLE", "heroCombo", "The exact combo is not available at this solution node.")
        reference = _reference_actions(node, strategy)
        score = score_decision(reference, selected_option_id)
        answered_at = self.clock()
        decision = {
            "decisionId": self.id_factory("decision"),
            "promptId": prompt_id,
            "sessionId": session_id,
            "sequence": prompt["sequence"],
            "scenarioId": session["scenarioId"],
            "gameConfigId": validated.game_config_id,
            "solutionId": session["solutionId"],
            "solutionVersion": session["solutionVersion"],
            "nodeId": prompt["nodeId"],
            "heroPosition": prompt["heroPosition"],
            "actionHistoryKey": _action_history_key(node),
            "heroCombo": prompt["heroCombo"],
            "groupedHand": strategy["group"],
            "offeredOptions": prompt["offeredOptions"],
            "selectedOptionId": selected_option_id,
            "selectedResolvedAction": resolved_action_json(selected_resolved),
            "comboReachWeight": strategy["reachFrequency"],
            "referenceSnapshot": [
                {
                    "optionId": item.option_id,
                    "frequency": normalized_decimal(item.frequency),
                    "actionEvBb": normalized_decimal(item.action_ev_bb),
                }
                for item in reference
            ],
            "highestEvOptionId": score.highest_ev_option_id,
            "evLossBb": normalized_decimal(score.ev_loss_bb),
            "feedbackSeverity": score.severity.value,
            "strategyStatus": score.strategy_status.value,
            "scoringPolicyVersion": SCORING_POLICY_VERSION,
            "accuracyMode": session["accuracyMode"],
            "rngRoll": prompt["rngRoll"],
            "rngMapping": prompt["rngMapping"],
            "presentedAt": prompt["presentedAt"],
            "answeredAt": answered_at,
            "interpretation": score.interpretation,
        }
        decisions = self.repository.list_decisions(session_id) + [decision]
        summary = summarize_decisions(decisions)
        completed_at = answered_at if len(decisions) >= session["targetDecisions"] else None
        saved_session, saved_decision = self.repository.append_decision(
            session_id,
            prompt_id,
            decision,
            summary,
            completed_at=completed_at,
        )
        return self._submission_response(saved_session, saved_decision)

    def complete_session(self, session_id: str) -> dict[str, Any]:
        return _public_session(self.repository.complete_session(session_id, completed_at=self.clock()))

    def session_detail(self, session_id: str) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        decisions = self.repository.list_decisions(session_id)
        reveal = session["feedbackMode"] == "IMMEDIATE" or session["status"] != "ACTIVE"
        return {
            **_public_session(session),
            "decisions": decisions if reveal else [_redacted_decision(item) for item in decisions],
        }

    def list_sessions(self) -> dict[str, Any]:
        return {"items": [_public_session(item) for item in self.repository.list_sessions()]}

    def decision_replay(self, session_id: str, decision_id: str) -> dict[str, Any]:
        session = self.repository.get_session(session_id)
        if session["feedbackMode"] == "DELAYED" and session["status"] == "ACTIVE":
            fail("TRAINER_FEEDBACK_DELAYED", "decisionId", "Feedback is available when this delayed-feedback session ends.")
        decision = self.repository.get_decision(session_id, decision_id)
        return {
            "session": _public_session(session),
            "decision": decision,
            "assumptions": self.catalog.assumptions(decision["solutionId"]),
        }

    def statistics(self) -> dict[str, Any]:
        hidden_session_ids = {
            session["sessionId"]
            for session in self.repository.list_sessions()
            if session["feedbackMode"] == "DELAYED" and session["status"] == "ACTIVE"
        }
        decisions = [
            decision
            for decision in self.repository.list_all_decisions()
            if decision["sessionId"] not in hidden_session_ids
        ]
        return summarize_decisions(decisions)

    def delete_session(self, session_id: str) -> None:
        self.repository.delete_session(session_id)

    def _create_session(
        self,
        command: dict[str, Any],
        *,
        drill_type: str,
        source_session_id: str | None,
        drill_items: list[dict[str, str]],
    ) -> dict[str, Any]:
        scenario_id = command["scenarioId"]
        scenario = self.catalog.scenario(scenario_id)
        artifact = self.catalog.store.get(scenario["solutionId"])
        accuracy_mode = "CERTIFIED" if artifact.manifest["trainerEligible"] else "REFERENCE_MODEL"
        now = self.clock()
        if accuracy_mode == "REFERENCE_MODEL" and not command.get("acknowledgeApproximate", False):
            fail(
                "TRAINER_APPROXIMATE_ACKNOWLEDGEMENT_REQUIRED",
                "acknowledgeApproximate",
                "This pack requires acknowledgement that feedback is relative to an approximate reference model.",
            )
        positions = command.get("heroPositions") or ["SB", "BB"]
        if not positions or any(position not in VALID_POSITIONS for position in positions):
            fail("TRAINER_POSITION_INVALID", "heroPositions", "Trainer positions must be SB and/or BB.")
        requested_nodes = command.get("nodeIds")
        available = {node["nodeId"]: node for node in scenario["nodes"]}
        node_ids = requested_nodes or [node_id for node_id, node in available.items() if node["actor"] in positions]
        if not node_ids or len(set(node_ids)) != len(node_ids):
            fail("TRAINER_NODE_SELECTION_INVALID", "nodeIds", "Select at least one unique solution node.")
        for node_id in node_ids:
            node = available.get(node_id)
            if node is None or node["actor"] not in positions:
                fail("TRAINER_NODE_SELECTION_INVALID", "nodeIds", "Every selected node must exist and match the selected positions.")
            self.rule_validator.validate(artifact, node_id)
        target = command.get("targetDecisions", 20)
        if not isinstance(target, int) or isinstance(target, bool) or target < 1 or target > 100:
            fail("TRAINER_TARGET_INVALID", "targetDecisions", "Training length must be between 1 and 100 decisions.")
        feedback_mode = command.get("feedbackMode", "IMMEDIATE")
        if feedback_mode not in VALID_FEEDBACK_MODES:
            fail("TRAINER_FEEDBACK_MODE_INVALID", "feedbackMode", "Feedback mode must be IMMEDIATE or DELAYED.")
        record = {
            "sessionId": self.id_factory("session"),
            "schemaVersion": SESSION_SCHEMA_VERSION,
            "status": "ACTIVE",
            "scenarioId": scenario_id,
            "solutionId": artifact.solution_id,
            "solutionVersion": artifact.manifest["version"],
            "selectedNodeIds": list(node_ids),
            "heroPositions": list(positions),
            "targetDecisions": target,
            "feedbackMode": feedback_mode,
            "scoringPolicyVersion": SCORING_POLICY_VERSION,
            "samplingPolicyVersion": SAMPLING_POLICY_VERSION,
            "accuracyMode": accuracy_mode,
            "approximateAcknowledgedAt": now if accuracy_mode == "REFERENCE_MODEL" else None,
            "rngEnabled": bool(command.get("rngEnabled", False)),
            "drillType": drill_type,
            "sourceSessionId": source_session_id,
            "drillItems": drill_items,
            "startedAt": now,
            "summary": summarize_decisions([]),
        }
        return _public_session(self.repository.create_session(record))

    @staticmethod
    def _submission_response(session: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        reveal = session["feedbackMode"] == "IMMEDIATE" or session["status"] != "ACTIVE"
        return {
            "session": _public_session(session),
            "recorded": True,
            "feedbackVisible": reveal,
            "decision": decision if reveal else _redacted_decision(decision),
        }


def summarize_decisions(decisions: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = list(decisions)
    losses = [Decimal(item["evLossBb"]) for item in items]
    total = sum(losses, Decimal(0))
    count = len(items)
    average = total / count if count else Decimal(0)
    severity_counts = {severity.value: 0 for severity in FeedbackSeverity}
    for item in items:
        severity_counts[item["feedbackSeverity"]] += 1
    return {
        "decisionsCompleted": count,
        "totalEvLossBb": normalized_decimal(total),
        "averageEvLossBb": normalized_decimal(average),
        "evLossPer100DecisionsBb": normalized_decimal(average * 100),
        "severityCounts": severity_counts,
        "byPosition": _breakdown(items, "heroPosition"),
        "byActionSequence": _breakdown(items, "actionHistoryKey"),
        "byScenario": _breakdown(items, "scenarioId"),
        "byGroupedHand": _breakdown(items, "groupedHand"),
        "frequencyCalibration": {
            "minimumSample": CALIBRATION_MINIMUM_SAMPLE,
            "buckets": _calibration(items),
        },
    }


def _breakdown(items: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[item[field]].append(item)
    result = []
    for key, values in grouped.items():
        total = sum((Decimal(item["evLossBb"]) for item in values), Decimal(0))
        result.append({
            "key": key,
            "decisions": len(values),
            "totalEvLossBb": normalized_decimal(total),
            "averageEvLossBb": normalized_decimal(total / len(values)),
        })
    return sorted(result, key=lambda item: (-Decimal(item["totalEvLossBb"]), item["key"]))


def _calibration(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        action_set = tuple(reference["optionId"] for reference in item["referenceSnapshot"])
        key = (item["scenarioId"], item["solutionId"], item["nodeId"], item["groupedHand"], action_set)
        buckets[key].append(item)
    output: list[dict[str, Any]] = []
    for (scenario_id, solution_id, node_id, group, action_set), decisions in buckets.items():
        if len(decisions) < CALIBRATION_MINIMUM_SAMPLE:
            continue
        actions = []
        for option_id in action_set:
            observed = Decimal(sum(item["selectedOptionId"] == option_id for item in decisions)) / len(decisions)
            expected = sum(
                (
                    Decimal(next(ref["frequency"] for ref in item["referenceSnapshot"] if ref["optionId"] == option_id))
                    for item in decisions
                ),
                Decimal(0),
            ) / len(decisions)
            actions.append({
                "optionId": option_id,
                "observedFrequency": normalized_decimal(observed),
                "referenceFrequency": normalized_decimal(expected),
                "deviationPp": normalized_decimal((observed - expected) * 100),
            })
        output.append({
            "scenarioId": scenario_id,
            "solutionId": solution_id,
            "nodeId": node_id,
            "groupedHand": group,
            "sampleSize": len(decisions),
            "actions": actions,
        })
    return sorted(output, key=lambda item: (item["scenarioId"], item["nodeId"], item["groupedHand"]))


def _reference_actions(node: dict[str, Any], strategy: dict[str, Any]) -> tuple[ReferenceAction, ...]:
    return tuple(
        ReferenceAction(
            option["actionId"],
            Decimal(strategy["frequencies"][option["actionId"]]),
            Decimal(strategy["evBb"][option["actionId"]]),
        )
        for option in node["actions"]
    )


def _action_history_key(node: dict[str, Any]) -> str:
    if not node["actionHistory"]:
        return f"{node['actor']} opening decision"
    return " > ".join(f"{item['actor']} {item['label']}" for item in node["actionHistory"]) + f" > {node['actor']} to act"


def _public_prompt(prompt: dict[str, Any]) -> dict[str, Any]:
    return dict(prompt)


def _public_session(session: dict[str, Any]) -> dict[str, Any]:
    public = {key: value for key, value in session.items() if key not in {"pendingPrompt", "drillItems"}}
    if session["feedbackMode"] == "DELAYED" and session["status"] == "ACTIVE":
        public["summary"] = _hidden_summary(session["summary"]["decisionsCompleted"])
    return public


def _hidden_summary(decisions_completed: int) -> dict[str, Any]:
    summary = summarize_decisions([])
    summary["decisionsCompleted"] = decisions_completed
    return summary


def _redacted_decision(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "decisionId": decision["decisionId"],
        "sessionId": decision["sessionId"],
        "sequence": decision["sequence"],
        "heroCombo": decision["heroCombo"],
        "groupedHand": decision["groupedHand"],
        "selectedOptionId": decision["selectedOptionId"],
        "answeredAt": decision["answeredAt"],
        "feedbackPending": True,
    }


def _is_close_mixed_decision(decision: dict[str, Any]) -> bool:
    reference = decision["referenceSnapshot"]
    material = [item for item in reference if Decimal(item["frequency"]) >= FREQUENCY_SUPPORT_TOLERANCE]
    if len(material) < 2:
        return False
    evs = sorted((Decimal(item["actionEvBb"]) for item in material), reverse=True)
    return evs[0] - evs[1] <= Decimal("0.010")


def _unique_drill_items(decisions: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result = []
    for item in decisions:
        key = (item["nodeId"], item["heroCombo"])
        if key not in seen:
            result.append({"nodeId": key[0], "heroCombo": key[1]})
            seen.add(key)
    return result


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
