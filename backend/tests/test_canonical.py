from __future__ import annotations

from decimal import Decimal
import unittest

from _support import SRC_DIR  # noqa: F401
from pokerhelper.domain import (
    ActionRequest,
    DomainError,
    GameConfig,
    InputActionKind,
    Position,
    canonical_json,
    content_id,
    game_config_id,
    game_state_id,
    replay,
)


class CanonicalTests(unittest.TestCase):
    def test_ID_001_equivalent_decimals_serialize_identically(self) -> None:
        values = [Decimal("2.5"), Decimal("2.50"), Decimal("02.500")]
        serializations = {canonical_json({"amount": value}) for value in values}
        identifiers = {content_id("test", {"amount": value}) for value in values}
        self.assertEqual(1, len(serializations))
        self.assertEqual(1, len(identifiers))

    def test_ID_002_negative_zero_normalizes(self) -> None:
        self.assertEqual(canonical_json({"amount": Decimal("0")}), canonical_json({"amount": Decimal("-0.000")}))

    def test_ID_003_mapping_order_is_not_semantic(self) -> None:
        first = {"a": Decimal("1"), "b": Decimal("2")}
        second = {"b": Decimal("2.0"), "a": Decimal("1.00")}
        self.assertEqual(canonical_json(first), canonical_json(second))

    def test_ID_004_action_history_order_is_semantic(self) -> None:
        first = [
            {"actor": "UTG", "type": "FOLD"},
            {"actor": "HJ", "type": "FOLD"},
        ]
        second = list(reversed(first))
        self.assertNotEqual(content_id("history", first), content_id("history", second))

    def test_ID_005_config_and_state_ids_are_stable(self) -> None:
        first_config = GameConfig.mvp()
        second_config = GameConfig.mvp()
        self.assertEqual(game_config_id(first_config), game_config_id(second_config))
        actions = [
            ActionRequest(Position.UTG, InputActionKind.FOLD),
            ActionRequest(Position.HJ, InputActionKind.FOLD),
        ]
        first_state = replay(first_config, actions)
        second_state = replay(second_config, actions)
        self.assertEqual(game_state_id(first_state), game_state_id(second_state))

    def test_ID_006_behavior_change_changes_state_id(self) -> None:
        fold = replay(GameConfig.mvp(), [ActionRequest(Position.UTG, InputActionKind.FOLD)])
        call = replay(GameConfig.mvp(), [ActionRequest(Position.UTG, InputActionKind.CALL)])
        self.assertNotEqual(game_state_id(fold), game_state_id(call))

    def test_ID_007_float_is_rejected(self) -> None:
        with self.assertRaises(DomainError) as error:
            canonical_json({"amount": 2.5})
        self.assertEqual("SCHEMA_CANONICAL_FLOAT_FORBIDDEN", error.exception.code)


if __name__ == "__main__":
    unittest.main()

