from __future__ import annotations

from decimal import Decimal
import random
import unittest

from _support import SRC_DIR  # noqa: F401
from pokerhelper.domain import (
    ActionRequest,
    ActionType,
    GameConfig,
    InputActionKind,
    Position,
    all_cards,
    apply_action,
    evaluate,
    game_state_id,
    initial_state,
    replay,
)


class DeterministicPropertyTests(unittest.TestCase):
    def test_PROP_001_evaluation_is_permutation_invariant(self) -> None:
        generator = random.Random(1701)
        deck = list(all_cards())
        for case in range(200):
            cards = generator.sample(deck, 7)
            expected = evaluate(cards).rank
            generator.shuffle(cards)
            with self.subTest(case=case):
                self.assertEqual(expected, evaluate(cards).rank)

    def test_PROP_002_legal_action_frontier_replays_identically(self) -> None:
        visited = 0

        def walk(state, requests: tuple[ActionRequest, ...], depth: int) -> None:
            nonlocal visited
            visited += 1
            replayed = replay(state.config, requests)
            self.assertEqual(game_state_id(state), game_state_id(replayed))
            self.assertEqual(state.pot_bb, sum((player.total_contribution_bb for player in state.players), Decimal("0")))
            for player in state.players:
                self.assertEqual(
                    player.starting_stack_bb,
                    player.stack_behind_bb + player.total_contribution_bb,
                )
            if depth == 0 or state.legal_actions is None:
                return
            for next_request in self._frontier_requests(state):
                walk(apply_action(state, next_request), requests + (next_request,), depth - 1)

        walk(initial_state(GameConfig.mvp()), (), 6)
        self.assertGreater(visited, 500)

    @staticmethod
    def _frontier_requests(state) -> tuple[ActionRequest, ...]:
        legal = state.legal_actions
        assert legal is not None
        actor = legal.actor
        requests: list[ActionRequest] = []
        if legal.can_fold:
            requests.append(ActionRequest(actor, InputActionKind.FOLD))
        if legal.can_check:
            requests.append(ActionRequest(actor, InputActionKind.CHECK))
        if legal.can_call:
            requests.append(ActionRequest(actor, InputActionKind.CALL))
        if legal.can_raise:
            if legal.min_full_raise_to_bb is not None:
                requests.append(
                    ActionRequest(actor, InputActionKind.RAISE, legal.min_full_raise_to_bb)
                )
                midpoint = legal.min_full_raise_to_bb + (
                    legal.max_raise_to_bb - legal.min_full_raise_to_bb
                ) / Decimal("2")
                if midpoint not in {legal.min_full_raise_to_bb, legal.max_raise_to_bb}:
                    requests.append(ActionRequest(actor, InputActionKind.RAISE, midpoint))
            if legal.all_in_resolves_to == ActionType.RAISE_TO:
                requests.append(ActionRequest(actor, InputActionKind.ALL_IN))
        unique: dict[tuple[InputActionKind, Decimal | None], ActionRequest] = {}
        for item in requests:
            unique[(item.kind, item.target_bb)] = item
        return tuple(unique.values())


if __name__ == "__main__":
    unittest.main()

