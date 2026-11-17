from __future__ import annotations

from decimal import Decimal
import unittest

from _support import SRC_DIR  # noqa: F401
from pokerhelper.domain import (
    ActionRequest,
    ActionType,
    DomainError,
    GameConfig,
    InputActionKind,
    PlayerStatus,
    Position,
    PositionConfig,
    RaiseClassification,
    ResolvedAction,
    SIX_MAX_POSITIONS,
    apply_action,
    initial_state,
    replay,
)


def request(actor: Position, kind: InputActionKind, target: str | None = None) -> ActionRequest:
    return ActionRequest(actor, kind, Decimal(target) if target is not None else None)


def config_with_stack(position: Position, stack: str) -> GameConfig:
    return GameConfig(
        positions=tuple(
            PositionConfig(seat, Decimal(stack if seat == position else "100"))
            for seat in SIX_MAX_POSITIONS
        ),
        small_blind_bb=Decimal("0.5"),
    )


class GameStateTests(unittest.TestCase):
    def test_BET_001_initial_state(self) -> None:
        state = initial_state(GameConfig.mvp())
        self.assertEqual(Position.UTG, state.current_actor)
        self.assertEqual(Decimal("1.5"), state.pot_bb)
        self.assertEqual(Decimal("1"), state.current_wager_bb)
        self.assertEqual(Decimal("1"), state.amount_to_call_bb)
        self.assertEqual(Decimal("2"), state.min_full_raise_to_bb)
        self.assertEqual(Decimal("99.5"), state.player(Position.SB).stack_behind_bb)
        self.assertEqual(Decimal("99"), state.player(Position.BB).stack_behind_bb)

    def test_POS_001_fold_through_order_and_terminal_hand(self) -> None:
        actions = [
            request(Position.UTG, InputActionKind.FOLD),
            request(Position.HJ, InputActionKind.FOLD),
            request(Position.CO, InputActionKind.FOLD),
            request(Position.BTN, InputActionKind.FOLD),
            request(Position.SB, InputActionKind.FOLD),
        ]
        state = replay(GameConfig.mvp(), actions)
        self.assertTrue(state.hand_terminal)
        self.assertTrue(state.betting_round_closed)
        self.assertIsNone(state.current_actor)
        self.assertEqual(PlayerStatus.ACTIVE, state.player(Position.BB).status)
        self.assertEqual(Decimal("1.5"), state.pot_bb)

    def test_BET_002_limp_and_big_blind_check(self) -> None:
        actions = [
            request(Position.UTG, InputActionKind.CALL),
            request(Position.HJ, InputActionKind.FOLD),
            request(Position.CO, InputActionKind.FOLD),
            request(Position.BTN, InputActionKind.FOLD),
            request(Position.SB, InputActionKind.FOLD),
            request(Position.BB, InputActionKind.CHECK),
        ]
        state = replay(GameConfig.mvp(), actions)
        self.assertTrue(state.betting_round_closed)
        self.assertFalse(state.hand_terminal)
        self.assertEqual(Decimal("2.5"), state.pot_bb)

    def test_BET_003_open_and_call_reconcile_exactly(self) -> None:
        actions = [
            request(Position.UTG, InputActionKind.FOLD),
            request(Position.HJ, InputActionKind.FOLD),
            request(Position.CO, InputActionKind.RAISE, "2.5"),
            request(Position.BTN, InputActionKind.FOLD),
            request(Position.SB, InputActionKind.FOLD),
            request(Position.BB, InputActionKind.CALL),
        ]
        state = replay(GameConfig.mvp(), actions)
        self.assertEqual(Decimal("5.5"), state.pot_bb)
        self.assertEqual(Decimal("97.5"), state.player(Position.CO).stack_behind_bb)
        self.assertEqual(Decimal("97.5"), state.player(Position.BB).stack_behind_bb)
        self.assertTrue(state.betting_round_closed)
        self.assertEqual(RaiseClassification.FULL_RAISE, state.action_history[2].raise_classification)

    def test_BET_004_full_raise_updates_minimum_and_reopens(self) -> None:
        state = initial_state(GameConfig.mvp())
        state = apply_action(state, request(Position.UTG, InputActionKind.RAISE, "3"))
        self.assertEqual(Decimal("5"), state.min_full_raise_to_bb)
        self.assertEqual(Position.HJ, state.current_actor)
        self.assertTrue(state.legal_actions and state.legal_actions.can_raise)
        state = apply_action(state, request(Position.HJ, InputActionKind.RAISE, "8"))
        self.assertEqual(Decimal("13"), state.min_full_raise_to_bb)
        self.assertEqual(Position.CO, state.current_actor)

    def test_BET_005_short_all_in_does_not_reopen_prior_players(self) -> None:
        config = config_with_stack(Position.CO, "5")
        actions = [
            request(Position.UTG, InputActionKind.RAISE, "4"),
            request(Position.HJ, InputActionKind.CALL),
            request(Position.CO, InputActionKind.ALL_IN),
            request(Position.BTN, InputActionKind.FOLD),
            request(Position.SB, InputActionKind.FOLD),
            request(Position.BB, InputActionKind.FOLD),
        ]
        state = replay(config, actions)
        short_raise = state.action_history[2]
        self.assertEqual(ActionType.RAISE_TO, short_raise.type)
        self.assertTrue(short_raise.is_all_in)
        self.assertEqual(RaiseClassification.SHORT_RAISE, short_raise.raise_classification)
        self.assertEqual(Position.UTG, state.current_actor)
        self.assertFalse(state.legal_actions and state.legal_actions.can_raise)
        with self.assertRaises(DomainError) as error:
            apply_action(state, request(Position.UTG, InputActionKind.RAISE, "10"))
        self.assertEqual("POKER_RULE_RAISE_NOT_REOPENED", error.exception.code)

        state = apply_action(state, request(Position.UTG, InputActionKind.CALL))
        state = apply_action(state, request(Position.HJ, InputActionKind.CALL))
        self.assertTrue(state.betting_round_closed)
        self.assertEqual(Decimal("16.5"), state.pot_bb)

    def test_BET_006_player_yet_to_act_may_full_raise_after_short_all_in(self) -> None:
        config = config_with_stack(Position.CO, "5")
        state = replay(
            config,
            [
                request(Position.UTG, InputActionKind.RAISE, "4"),
                request(Position.HJ, InputActionKind.CALL),
                request(Position.CO, InputActionKind.ALL_IN),
            ],
        )
        self.assertEqual(Position.BTN, state.current_actor)
        self.assertTrue(state.legal_actions and state.legal_actions.can_raise)
        self.assertEqual(Decimal("8"), state.legal_actions.min_full_raise_to_bb)
        state = apply_action(state, request(Position.BTN, InputActionKind.RAISE, "8"))
        self.assertEqual(RaiseClassification.FULL_RAISE, state.action_history[-1].raise_classification)

    def test_BET_007_all_in_call_resolves_as_call(self) -> None:
        config = config_with_stack(Position.BB, "10")
        actions = [
            request(Position.UTG, InputActionKind.ALL_IN),
            request(Position.HJ, InputActionKind.FOLD),
            request(Position.CO, InputActionKind.FOLD),
            request(Position.BTN, InputActionKind.FOLD),
            request(Position.SB, InputActionKind.FOLD),
            request(Position.BB, InputActionKind.ALL_IN),
        ]
        state = replay(config, actions)
        action = state.action_history[-1]
        self.assertEqual(ActionType.CALL, action.type)
        self.assertTrue(action.is_all_in)
        self.assertTrue(state.hand_terminal)
        self.assertEqual(Decimal("110.5"), state.pot_bb)

    def test_BET_008_invalid_check_facing_wager(self) -> None:
        with self.assertRaises(DomainError) as error:
            apply_action(initial_state(GameConfig.mvp()), request(Position.UTG, InputActionKind.CHECK))
        self.assertEqual("POKER_RULE_CHECK_FACING_WAGER", error.exception.code)

    def test_BET_009_invalid_call_when_check_available(self) -> None:
        state = replay(
            GameConfig.mvp(),
            [
                request(Position.UTG, InputActionKind.CALL),
                request(Position.HJ, InputActionKind.FOLD),
                request(Position.CO, InputActionKind.FOLD),
                request(Position.BTN, InputActionKind.FOLD),
                request(Position.SB, InputActionKind.FOLD),
            ],
        )
        with self.assertRaises(DomainError) as error:
            apply_action(state, request(Position.BB, InputActionKind.CALL))
        self.assertEqual("POKER_RULE_CALL_WITH_NOTHING_TO_CALL", error.exception.code)

    def test_BET_010_invalid_non_all_in_under_raise(self) -> None:
        with self.assertRaises(DomainError) as error:
            apply_action(initial_state(GameConfig.mvp()), request(Position.UTG, InputActionKind.RAISE, "1.5"))
        self.assertEqual("POKER_RULE_RAISE_BELOW_MINIMUM", error.exception.code)

    def test_BET_011_invalid_raise_beyond_stack(self) -> None:
        with self.assertRaises(DomainError) as error:
            apply_action(initial_state(GameConfig.mvp()), request(Position.UTG, InputActionKind.RAISE, "101"))
        self.assertEqual("POKER_RULE_RAISE_EXCEEDS_STACK", error.exception.code)

    def test_POS_002_action_out_of_turn_is_explicit(self) -> None:
        with self.assertRaises(DomainError) as error:
            apply_action(initial_state(GameConfig.mvp()), request(Position.HJ, InputActionKind.FOLD))
        self.assertEqual("POKER_RULE_ACTION_OUT_OF_TURN", error.exception.code)
        self.assertEqual("actionHistory[0].actor", error.exception.path)

    def test_BET_012_replay_recalculates_annotations(self) -> None:
        invalid = ResolvedAction(
            actor=Position.UTG,
            type=ActionType.RAISE_TO,
            target_bb=Decimal("2"),
            is_all_in=True,
            raise_classification=RaiseClassification.FULL_RAISE,
        )
        with self.assertRaises(DomainError) as error:
            replay(GameConfig.mvp(), [invalid])
        self.assertEqual("REPLAY_ACTION_ANNOTATION_MISMATCH", error.exception.code)

    def test_ERR_004_invalid_position_layout_fails_closed(self) -> None:
        positions = tuple(
            PositionConfig(position, Decimal("100"))
            for position in reversed(SIX_MAX_POSITIONS)
        )
        with self.assertRaises(DomainError) as error:
            GameConfig(positions=positions, small_blind_bb=Decimal("0.5"))
        self.assertEqual("POKER_RULE_POSITION_LAYOUT_INVALID", error.exception.code)

    def test_ERR_005_forced_bet_cannot_exceed_stack(self) -> None:
        positions = tuple(
            PositionConfig(position, Decimal("0.5") if position == Position.BB else Decimal("100"))
            for position in SIX_MAX_POSITIONS
        )
        with self.assertRaises(DomainError) as error:
            GameConfig(positions=positions, small_blind_bb=Decimal("0.5"))
        self.assertEqual("POKER_RULE_FORCED_BET_EXCEEDS_STACK", error.exception.code)


if __name__ == "__main__":
    unittest.main()

