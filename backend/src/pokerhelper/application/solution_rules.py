"""Shared replay validation for Study nodes and Trainer action submission."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from pokerhelper.domain.canonical import game_config_id, resolved_action_payload
from pokerhelper.domain.decimal_utils import as_decimal, normalized_decimal
from pokerhelper.domain.errors import fail
from pokerhelper.domain.game import (
    ActionRequest,
    ActionType,
    GameConfig,
    GameState,
    InputActionKind,
    PositionConfig,
    ResolvedAction,
    apply_action,
    replay,
)
from pokerhelper.domain.positions import Position, SIX_MAX_POSITIONS
from pokerhelper.domain.rake import RakeCollectionRule, RakePolicy
from pokerhelper.solutions import SolutionArtifact


@dataclass(frozen=True, slots=True)
class ValidatedSolutionNode:
    state: GameState
    game_config_id: str
    resolved_actions: dict[str, ResolvedAction]


class SolutionRuleValidator:
    """Replay solution nodes through the canonical poker engine once and cache them."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], ValidatedSolutionNode] = {}

    def validate(self, artifact: SolutionArtifact, node_id: str) -> ValidatedSolutionNode:
        key = (artifact.solution_id, node_id)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        node = artifact.node(node_id)
        config = game_config_from_manifest(artifact.manifest)
        actions = [_request(item) for item in artifact.manifest["scenario"]["assumedPriorActions"]]
        actions.extend(_request(item) for item in node["actionHistory"])
        state = replay(config, actions)
        _require_node_state(node, state)

        resolved: dict[str, ResolvedAction] = {}
        for option in node["actions"]:
            next_state = apply_action(state, _request(option, actor=node["actor"]))
            calculated = next_state.action_history[-1]
            _require_option_match(option, calculated, node_id)
            resolved[option["actionId"]] = calculated
        result = ValidatedSolutionNode(state, game_config_id(config), resolved)
        self._cache[key] = result
        return result

    def validate_artifact(self, artifact: SolutionArtifact) -> None:
        for node_id in artifact.nodes:
            self.validate(artifact, node_id)


def game_config_from_manifest(manifest: Mapping[str, Any]) -> GameConfig:
    game = manifest["game"]
    rake = game["rake"]
    return GameConfig(
        positions=tuple(PositionConfig(position, Decimal(game["effectiveStackBb"])) for position in SIX_MAX_POSITIONS),
        small_blind_bb=Decimal(game["smallBlindBb"]),
        big_blind_bb=Decimal(game["bigBlindBb"]),
        ante_bb=Decimal(game["anteBb"]),
        rake_policy=RakePolicy(
            policy_version=rake["policyVersion"],
            rate=Decimal(rake["rate"]),
            cap_bb=Decimal(rake["capBb"]),
            no_flop_no_drop=bool(rake["noFlopNoDrop"]),
            collection_rule=RakeCollectionRule.QUALIFYING_POSTFLOP_POT,
        ),
    )


def resolved_action_json(action: ResolvedAction) -> dict[str, Any]:
    payload = resolved_action_payload(action)
    return {
        key: normalized_decimal(value) if isinstance(value, Decimal) else value
        for key, value in payload.items()
    }


def _request(raw: Mapping[str, Any], *, actor: str | None = None) -> ActionRequest:
    position = Position(actor or raw["actor"])
    action_type = raw["type"]
    if action_type == "FOLD":
        return ActionRequest(position, InputActionKind.FOLD)
    if action_type == "CHECK":
        return ActionRequest(position, InputActionKind.CHECK)
    if action_type == "CALL":
        return ActionRequest(position, InputActionKind.CALL)
    if action_type == "RAISE_TO":
        return ActionRequest(position, InputActionKind.RAISE, Decimal(raw["targetBb"]))
    fail("SOLUTION_ACTION_TYPE_INVALID", "action.type", "The solution action cannot be resolved by the poker engine.")


def _require_node_state(node: Mapping[str, Any], state: GameState) -> None:
    actor = state.current_actor.value if state.current_actor is not None else None
    player = state.player(state.current_actor) if state.current_actor is not None else None
    comparisons = {
        "actor": (actor, node["actor"]),
        "potBb": (normalized_decimal(state.pot_bb), node["potBb"]),
        "amountToCallBb": (normalized_decimal(state.amount_to_call_bb), node["amountToCallBb"]),
        "actorContributionBb": (
            normalized_decimal(player.street_contribution_bb) if player is not None else None,
            node["actorContributionBb"],
        ),
        "actorStackBehindBb": (
            normalized_decimal(player.stack_behind_bb) if player is not None else None,
            node["actorStackBehindBb"],
        ),
    }
    for field, (calculated, declared) in comparisons.items():
        if calculated != declared:
            fail(
                "SOLUTION_POKER_STATE_MISMATCH",
                f"nodes.{node['nodeId']}.{field}",
                "The solution node disagrees with canonical poker replay.",
                details={"calculated": calculated, "declared": declared},
            )


def _require_option_match(option: Mapping[str, Any], resolved: ResolvedAction, node_id: str) -> None:
    expected_target = option["targetBb"]
    calculated_target = normalized_decimal(resolved.target_bb) if resolved.target_bb is not None else None
    expected = (option["type"], expected_target, option["isAllIn"])
    calculated = (resolved.type.value, calculated_target, resolved.is_all_in)
    if expected != calculated:
        fail(
            "SOLUTION_ACTION_REPLAY_MISMATCH",
            f"nodes.{node_id}.actions.{option['actionId']}",
            "A supported option does not resolve to the declared poker action.",
            details={"expected": expected, "calculated": calculated},
        )
