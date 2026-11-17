"""Deterministic six-max no-limit preflop state and action replay."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum
from typing import Iterable

from .decimal_utils import ONE, ZERO, as_decimal
from .errors import fail
from .positions import Position, SIX_MAX_POSITIONS, next_eligible
from .rake import MVP_RAKE_POLICY, RakePolicy


class Variant(str, Enum):
    NLHE = "NLHE"


class BettingStructure(str, Enum):
    NO_LIMIT = "NO_LIMIT"


class GameType(str, Enum):
    CASH = "CASH"


class Street(str, Enum):
    PREFLOP = "PREFLOP"


class PlayerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FOLDED = "FOLDED"
    ALL_IN = "ALL_IN"


class InputActionKind(str, Enum):
    FOLD = "FOLD"
    CHECK = "CHECK"
    CALL = "CALL"
    RAISE = "RAISE"
    ALL_IN = "ALL_IN"


class ActionType(str, Enum):
    FOLD = "FOLD"
    CHECK = "CHECK"
    CALL = "CALL"
    RAISE_TO = "RAISE_TO"


class RaiseClassification(str, Enum):
    FULL_RAISE = "FULL_RAISE"
    SHORT_RAISE = "SHORT_RAISE"


@dataclass(frozen=True, slots=True)
class PositionConfig:
    position: Position
    starting_stack_bb: Decimal

    def __post_init__(self) -> None:
        stack = as_decimal(self.starting_stack_bb, path=f"positions.{self.position.value}.startingStackBb")
        if stack <= ZERO:
            fail(
                "POKER_RULE_STARTING_STACK_NOT_POSITIVE",
                f"positions.{self.position.value}.startingStackBb",
                "Starting stack must be positive.",
            )
        object.__setattr__(self, "starting_stack_bb", stack)


@dataclass(frozen=True, slots=True)
class GameConfig:
    positions: tuple[PositionConfig, ...]
    small_blind_bb: Decimal
    big_blind_bb: Decimal = ONE
    ante_bb: Decimal = ZERO
    rake_policy: RakePolicy = MVP_RAKE_POLICY
    schema_version: str = "1.0.0"
    identity_profile_version: str = "1"
    variant: Variant = Variant.NLHE
    betting_structure: BettingStructure = BettingStructure.NO_LIMIT
    game_type: GameType = GameType.CASH
    table_size: int = 6

    def __post_init__(self) -> None:
        positions = tuple(self.positions)
        small = as_decimal(self.small_blind_bb, path="smallBlindBb")
        big = as_decimal(self.big_blind_bb, path="bigBlindBb")
        ante = as_decimal(self.ante_bb, path="anteBb")
        actual = tuple(item.position for item in positions)
        if actual != SIX_MAX_POSITIONS or self.table_size != 6:
            fail(
                "POKER_RULE_POSITION_LAYOUT_INVALID",
                "positions",
                "The MVP requires positions ordered UTG, HJ, CO, BTN, SB, BB.",
                details={"received": [position.value for position in actual]},
            )
        if big != ONE:
            fail("POKER_RULE_BIG_BLIND_UNIT_INVALID", "bigBlindBb", "The normalized big blind must equal 1 BB.")
        if small < ZERO or small > big:
            fail("POKER_RULE_SMALL_BLIND_INVALID", "smallBlindBb", "Small blind must be between 0 and 1 BB.")
        if ante < ZERO:
            fail("POKER_RULE_ANTE_NEGATIVE", "anteBb", "Ante cannot be negative.")
        for item in positions:
            forced = ante
            if item.position == Position.SB:
                forced += small
            if item.position == Position.BB:
                forced += big
            if forced > item.starting_stack_bb:
                fail(
                    "POKER_RULE_FORCED_BET_EXCEEDS_STACK",
                    f"positions.{item.position.value}.startingStackBb",
                    "Forced contributions cannot exceed the starting stack.",
                )
        object.__setattr__(self, "positions", positions)
        object.__setattr__(self, "small_blind_bb", small)
        object.__setattr__(self, "big_blind_bb", big)
        object.__setattr__(self, "ante_bb", ante)

    @classmethod
    def mvp(cls) -> "GameConfig":
        return cls(
            positions=tuple(PositionConfig(position, Decimal("100")) for position in SIX_MAX_POSITIONS),
            small_blind_bb=Decimal("0.5"),
        )


@dataclass(frozen=True, slots=True)
class PlayerState:
    position: Position
    starting_stack_bb: Decimal
    stack_behind_bb: Decimal
    street_contribution_bb: Decimal
    total_contribution_bb: Decimal
    status: PlayerStatus


@dataclass(frozen=True, slots=True)
class ActionRequest:
    actor: Position
    kind: InputActionKind
    target_bb: Decimal | None = None

    def __post_init__(self) -> None:
        if self.kind == InputActionKind.RAISE:
            if self.target_bb is None:
                fail("SCHEMA_RAISE_TARGET_REQUIRED", "action.targetBb", "A raise requires a target amount.")
            object.__setattr__(self, "target_bb", as_decimal(self.target_bb, path="action.targetBb"))
        elif self.target_bb is not None:
            fail(
                "SCHEMA_ACTION_TARGET_FORBIDDEN",
                "action.targetBb",
                "Only a raise request may provide targetBb.",
            )


@dataclass(frozen=True, slots=True)
class ResolvedAction:
    actor: Position
    type: ActionType
    target_bb: Decimal | None = None
    is_all_in: bool = False
    raise_classification: RaiseClassification | None = None


@dataclass(frozen=True, slots=True)
class LegalActions:
    actor: Position
    can_fold: bool
    can_check: bool
    can_call: bool
    call_amount_bb: Decimal
    can_raise: bool
    min_full_raise_to_bb: Decimal | None
    max_raise_to_bb: Decimal
    short_all_in_only: bool
    can_all_in: bool
    all_in_resolves_to: ActionType | None


@dataclass(frozen=True, slots=True)
class GameState:
    config: GameConfig
    street: Street
    players: tuple[PlayerState, ...]
    action_history: tuple[ResolvedAction, ...]
    current_actor: Position | None
    pot_bb: Decimal
    current_wager_bb: Decimal
    amount_to_call_bb: Decimal
    min_full_raise_to_bb: Decimal
    last_full_raise_increment_bb: Decimal
    legal_actions: LegalActions | None
    betting_round_closed: bool
    hand_terminal: bool
    pending_positions: frozenset[Position]
    acted_since_last_full_raise: frozenset[Position]

    def player(self, position: Position) -> PlayerState:
        for player in self.players:
            if player.position == position:
                return player
        fail(
            "POKER_RULE_POSITION_UNSUPPORTED",
            "position",
            "Position is not part of this game.",
            details={"position": position.value},
        )


def initial_state(config: GameConfig) -> GameState:
    players: list[PlayerState] = []
    for seat in config.positions:
        ante = min(config.ante_bb, seat.starting_stack_bb)
        remaining = seat.starting_stack_bb - ante
        blind = ZERO
        if seat.position == Position.SB:
            blind = min(config.small_blind_bb, remaining)
        elif seat.position == Position.BB:
            blind = min(config.big_blind_bb, remaining)
        total = ante + blind
        stack = seat.starting_stack_bb - total
        players.append(
            PlayerState(
                position=seat.position,
                starting_stack_bb=seat.starting_stack_bb,
                stack_behind_bb=stack,
                street_contribution_bb=blind,
                total_contribution_bb=total,
                status=PlayerStatus.ALL_IN if stack == ZERO else PlayerStatus.ACTIVE,
            )
        )

    player_tuple = tuple(players)
    pending = frozenset(player.position for player in player_tuple if player.status == PlayerStatus.ACTIVE)
    actor = next_eligible(None, pending)
    wager = max((player.street_contribution_bb for player in player_tuple), default=ZERO)
    state = GameState(
        config=config,
        street=Street.PREFLOP,
        players=player_tuple,
        action_history=(),
        current_actor=actor,
        pot_bb=sum((player.total_contribution_bb for player in player_tuple), ZERO),
        current_wager_bb=wager,
        amount_to_call_bb=_amount_to_call(actor, player_tuple, wager),
        min_full_raise_to_bb=wager + config.big_blind_bb,
        last_full_raise_increment_bb=config.big_blind_bb,
        legal_actions=None,
        betting_round_closed=actor is None,
        hand_terminal=_is_terminal(player_tuple),
        pending_positions=pending,
        acted_since_last_full_raise=frozenset(),
    )
    state = replace(state, legal_actions=_legal_actions(state))
    _validate_state_invariants(state)
    return state


def apply_action(state: GameState, request: ActionRequest) -> GameState:
    action_index = len(state.action_history)
    if state.betting_round_closed or state.hand_terminal or state.current_actor is None:
        fail(
            "POKER_RULE_ACTION_AFTER_TERMINAL",
            f"actionHistory[{action_index}]",
            "No voluntary action is allowed after the betting decision is closed.",
        )
    if request.actor != state.current_actor:
        fail(
            "POKER_RULE_ACTION_OUT_OF_TURN",
            f"actionHistory[{action_index}].actor",
            f"Expected {state.current_actor.value} to act, but received {request.actor.value}.",
            details={"expected": state.current_actor.value, "received": request.actor.value},
        )

    player = state.player(request.actor)
    if player.status != PlayerStatus.ACTIVE:
        fail(
            "POKER_RULE_INELIGIBLE_ACTOR",
            f"actionHistory[{action_index}].actor",
            "Folded and all-in players cannot act.",
            details={"status": player.status.value},
        )

    resolved = _resolve_request(state, request, action_index=action_index)
    players = _apply_resolved_to_players(state, resolved)
    wager = state.current_wager_bb
    is_full_raise = resolved.raise_classification == RaiseClassification.FULL_RAISE
    is_short_raise = resolved.raise_classification == RaiseClassification.SHORT_RAISE
    if resolved.type == ActionType.RAISE_TO:
        assert resolved.target_bb is not None
        wager = resolved.target_bb

    if is_full_raise:
        increment = wager - state.current_wager_bb
        last_full_increment = increment
        acted = frozenset({request.actor})
        pending = {
            item.position
            for item in players
            if item.position != request.actor and item.status == PlayerStatus.ACTIVE
        }
    else:
        last_full_increment = state.last_full_raise_increment_bb
        acted = frozenset(set(state.acted_since_last_full_raise) | {request.actor})
        pending = set(state.pending_positions)
        pending.discard(request.actor)
        if is_short_raise:
            pending.update(
                item.position
                for item in players
                if item.position != request.actor
                and item.status == PlayerStatus.ACTIVE
                and item.street_contribution_bb < wager
            )

    pending = {
        position
        for position in pending
        if _player_from(players, position).status == PlayerStatus.ACTIVE
    }
    terminal = _is_terminal(players)
    if terminal:
        pending.clear()
    closed = not pending
    actor = None if closed else next_eligible(request.actor, pending)
    history = state.action_history + (resolved,)
    next_state = GameState(
        config=state.config,
        street=state.street,
        players=players,
        action_history=history,
        current_actor=actor,
        pot_bb=sum((item.total_contribution_bb for item in players), ZERO),
        current_wager_bb=wager,
        amount_to_call_bb=_amount_to_call(actor, players, wager),
        min_full_raise_to_bb=wager + last_full_increment,
        last_full_raise_increment_bb=last_full_increment,
        legal_actions=None,
        betting_round_closed=closed,
        hand_terminal=terminal,
        pending_positions=frozenset(pending),
        acted_since_last_full_raise=acted,
    )
    next_state = replace(next_state, legal_actions=_legal_actions(next_state))
    _validate_state_invariants(next_state)
    return next_state


def replay(
    config: GameConfig,
    actions: Iterable[ActionRequest | ResolvedAction],
) -> GameState:
    state = initial_state(config)
    for index, action in enumerate(actions):
        if isinstance(action, ActionRequest):
            state = apply_action(state, action)
            continue
        request = _request_from_resolved(action)
        state = apply_action(state, request)
        recalculated = state.action_history[-1]
        if recalculated != action:
            fail(
                "REPLAY_ACTION_ANNOTATION_MISMATCH",
                f"actionHistory[{index}]",
                "Stored action annotations or amounts do not match deterministic replay.",
                details={"stored": _action_debug(action), "recalculated": _action_debug(recalculated)},
            )
    return state


def _resolve_request(state: GameState, request: ActionRequest, *, action_index: int) -> ResolvedAction:
    player = state.player(request.actor)
    to_call = max(ZERO, state.current_wager_bb - player.street_contribution_bb)
    path = f"actionHistory[{action_index}]"

    if request.kind == InputActionKind.FOLD:
        if to_call == ZERO:
            fail("POKER_RULE_FOLD_WHEN_CHECK_AVAILABLE", f"{path}.type", "Cannot fold when checking is available.")
        return ResolvedAction(request.actor, ActionType.FOLD)

    if request.kind == InputActionKind.CHECK:
        if to_call != ZERO:
            fail(
                "POKER_RULE_CHECK_FACING_WAGER",
                f"{path}.type",
                "Cannot check while facing a wager.",
                details={"amountToCallBb": str(min(to_call, player.stack_behind_bb))},
            )
        return ResolvedAction(request.actor, ActionType.CHECK)

    if request.kind == InputActionKind.CALL:
        if to_call == ZERO:
            fail("POKER_RULE_CALL_WITH_NOTHING_TO_CALL", f"{path}.type", "Cannot call when no amount is owed.")
        return ResolvedAction(
            request.actor,
            ActionType.CALL,
            is_all_in=player.stack_behind_bb <= to_call,
        )

    if request.kind == InputActionKind.ALL_IN:
        if player.stack_behind_bb == ZERO:
            fail("POKER_RULE_ALL_IN_WITHOUT_STACK", f"{path}.type", "Player has no remaining stack.")
        max_target = player.street_contribution_bb + player.stack_behind_bb
        if max_target <= state.current_wager_bb:
            return ResolvedAction(request.actor, ActionType.CALL, is_all_in=True)
        return _resolve_raise(state, request.actor, max_target, action_index=action_index)

    if request.kind == InputActionKind.RAISE:
        assert request.target_bb is not None
        return _resolve_raise(state, request.actor, request.target_bb, action_index=action_index)

    fail("SCHEMA_ACTION_KIND_UNSUPPORTED", f"{path}.type", "Unsupported preflop action kind.")


def _resolve_raise(
    state: GameState,
    actor: Position,
    target: Decimal,
    *,
    action_index: int,
) -> ResolvedAction:
    player = state.player(actor)
    path = f"actionHistory[{action_index}].targetBb"
    max_target = player.street_contribution_bb + player.stack_behind_bb
    if actor in state.acted_since_last_full_raise:
        fail(
            "POKER_RULE_RAISE_NOT_REOPENED",
            f"actionHistory[{action_index}].type",
            "A short all-in raise did not reopen raising for this player.",
        )
    if not _opponent_can_respond(state.players, actor):
        fail(
            "POKER_RULE_RAISE_WITHOUT_RESPONDER",
            f"actionHistory[{action_index}].type",
            "Cannot raise when no opponent has chips available to respond.",
        )
    if target <= state.current_wager_bb:
        fail(
            "POKER_RULE_RAISE_TARGET_NOT_ABOVE_WAGER",
            path,
            "Raise target must exceed the current wager.",
            details={"currentWagerBb": str(state.current_wager_bb)},
        )
    if target > max_target:
        fail(
            "POKER_RULE_RAISE_EXCEEDS_STACK",
            path,
            "Raise target exceeds the actor's available stack.",
            details={"maxTargetBb": str(max_target)},
        )
    increment = target - state.current_wager_bb
    full = increment >= state.last_full_raise_increment_bb
    is_all_in = target == max_target
    if not full and not is_all_in:
        fail(
            "POKER_RULE_RAISE_BELOW_MINIMUM",
            path,
            "A raise below the minimum is legal only when it is all-in.",
            details={"minimumFullRaiseToBb": str(state.min_full_raise_to_bb)},
        )
    return ResolvedAction(
        actor=actor,
        type=ActionType.RAISE_TO,
        target_bb=target,
        is_all_in=is_all_in,
        raise_classification=(
            RaiseClassification.FULL_RAISE if full else RaiseClassification.SHORT_RAISE
        ),
    )


def _apply_resolved_to_players(
    state: GameState,
    action: ResolvedAction,
) -> tuple[PlayerState, ...]:
    result: list[PlayerState] = []
    for player in state.players:
        if player.position != action.actor:
            result.append(player)
            continue
        if action.type == ActionType.FOLD:
            result.append(replace(player, status=PlayerStatus.FOLDED))
            continue
        if action.type == ActionType.CHECK:
            result.append(player)
            continue
        if action.type == ActionType.CALL:
            owed = max(ZERO, state.current_wager_bb - player.street_contribution_bb)
            added = min(owed, player.stack_behind_bb)
        else:
            assert action.target_bb is not None
            added = action.target_bb - player.street_contribution_bb
        stack = player.stack_behind_bb - added
        result.append(
            replace(
                player,
                stack_behind_bb=stack,
                street_contribution_bb=player.street_contribution_bb + added,
                total_contribution_bb=player.total_contribution_bb + added,
                status=PlayerStatus.ALL_IN if stack == ZERO else PlayerStatus.ACTIVE,
            )
        )
    return tuple(result)


def _legal_actions(state: GameState) -> LegalActions | None:
    if state.current_actor is None or state.betting_round_closed or state.hand_terminal:
        return None
    player = state.player(state.current_actor)
    owed = max(ZERO, state.current_wager_bb - player.street_contribution_bb)
    call_amount = min(owed, player.stack_behind_bb)
    max_target = player.street_contribution_bb + player.stack_behind_bb
    raise_rights = state.current_actor not in state.acted_since_last_full_raise
    can_raise = (
        raise_rights
        and max_target > state.current_wager_bb
        and _opponent_can_respond(state.players, state.current_actor)
    )
    min_full = state.min_full_raise_to_bb if can_raise and max_target >= state.min_full_raise_to_bb else None
    if player.stack_behind_bb == ZERO:
        all_in_type = None
    elif max_target <= state.current_wager_bb:
        all_in_type = ActionType.CALL
    elif can_raise:
        all_in_type = ActionType.RAISE_TO
    else:
        all_in_type = None
    return LegalActions(
        actor=state.current_actor,
        can_fold=owed > ZERO,
        can_check=owed == ZERO,
        can_call=owed > ZERO,
        call_amount_bb=call_amount,
        can_raise=can_raise,
        min_full_raise_to_bb=min_full,
        max_raise_to_bb=max_target,
        short_all_in_only=can_raise and max_target < state.min_full_raise_to_bb,
        can_all_in=all_in_type is not None,
        all_in_resolves_to=all_in_type,
    )


def _amount_to_call(
    actor: Position | None,
    players: tuple[PlayerState, ...],
    wager: Decimal,
) -> Decimal:
    if actor is None:
        return ZERO
    player = _player_from(players, actor)
    return min(max(ZERO, wager - player.street_contribution_bb), player.stack_behind_bb)


def _player_from(players: tuple[PlayerState, ...], position: Position) -> PlayerState:
    for player in players:
        if player.position == position:
            return player
    fail("POKER_RULE_POSITION_UNSUPPORTED", "position", "Position is not part of this game.")


def _opponent_can_respond(players: tuple[PlayerState, ...], actor: Position) -> bool:
    return any(
        player.position != actor
        and player.status == PlayerStatus.ACTIVE
        and player.stack_behind_bb > ZERO
        for player in players
    )


def _is_terminal(players: tuple[PlayerState, ...]) -> bool:
    non_folded = [player for player in players if player.status != PlayerStatus.FOLDED]
    if len(non_folded) <= 1:
        return True
    active = [player for player in non_folded if player.status == PlayerStatus.ACTIVE]
    if not active:
        return True
    if len(active) > 1:
        return False
    wager = max(player.street_contribution_bb for player in non_folded)
    return active[0].street_contribution_bb >= wager


def _request_from_resolved(action: ResolvedAction) -> ActionRequest:
    if action.type == ActionType.FOLD:
        return ActionRequest(action.actor, InputActionKind.FOLD)
    if action.type == ActionType.CHECK:
        return ActionRequest(action.actor, InputActionKind.CHECK)
    if action.type == ActionType.CALL:
        return ActionRequest(action.actor, InputActionKind.CALL)
    assert action.target_bb is not None
    return ActionRequest(action.actor, InputActionKind.RAISE, action.target_bb)


def _action_debug(action: ResolvedAction) -> dict[str, object]:
    return {
        "actor": action.actor.value,
        "type": action.type.value,
        "targetBb": str(action.target_bb) if action.target_bb is not None else None,
        "isAllIn": action.is_all_in,
        "raiseClassification": (
            action.raise_classification.value if action.raise_classification is not None else None
        ),
    }


def _validate_state_invariants(state: GameState) -> None:
    if state.pot_bb != sum((player.total_contribution_bb for player in state.players), ZERO):
        fail("REPLAY_POT_MISMATCH", "state.potBb", "Pot does not reconcile with player contributions.")
    expected_wager = max((player.street_contribution_bb for player in state.players), default=ZERO)
    if state.current_wager_bb != expected_wager:
        fail("REPLAY_WAGER_MISMATCH", "state.currentWagerBb", "Current wager does not match contributions.")
    for player in state.players:
        values = (
            player.stack_behind_bb,
            player.street_contribution_bb,
            player.total_contribution_bb,
        )
        if any(value < ZERO for value in values):
            fail(
                "REPLAY_NEGATIVE_AMOUNT",
                f"state.players.{player.position.value}",
                "Stacks and contributions cannot be negative.",
            )
        if player.stack_behind_bb + player.total_contribution_bb != player.starting_stack_bb:
            fail(
                "REPLAY_STACK_MISMATCH",
                f"state.players.{player.position.value}",
                "Starting stack must equal stack behind plus total contribution.",
            )

