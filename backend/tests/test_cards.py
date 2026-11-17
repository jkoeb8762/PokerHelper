from __future__ import annotations

import unittest

from _support import SRC_DIR  # noqa: F401
from pokerhelper.domain import Board, Card, Deck, DomainError, ExactCombo, all_cards, all_exact_combos


class CardTests(unittest.TestCase):
    def test_CARD_001_all_cards_round_trip_and_are_unique(self) -> None:
        cards = all_cards()
        self.assertEqual(52, len(cards))
        self.assertEqual(52, len(set(cards)))
        self.assertEqual(cards, tuple(Card.parse(str(card)) for card in cards))

    def test_CARD_002_deck_is_complete_and_deterministic(self) -> None:
        first = Deck()
        second = Deck()
        self.assertEqual(52, len(first))
        self.assertEqual(first.cards, second.cards)
        self.assertEqual("As", str(first.cards[0]))
        self.assertEqual("2c", str(first.cards[-1]))

    def test_CARD_003_board_sizes(self) -> None:
        for cards in ([], ["As", "Kd", "Qh"], ["As", "Kd", "Qh", "Jc"], ["As", "Kd", "Qh", "Jc", "Ts"]):
            with self.subTest(cards=cards):
                self.assertEqual(len(cards), len(Board.parse(cards).cards))
        for cards in (["As"], ["As", "Kd"], ["As", "Kd", "Qh", "Jc", "Ts", "9s"]):
            with self.subTest(cards=cards):
                with self.assertRaisesRegex(DomainError, "POKER_RULE_BOARD_SIZE_INVALID"):
                    Board.parse(cards)

    def test_CARD_004_duplicates_are_rejected(self) -> None:
        with self.assertRaises(DomainError) as error:
            Board.parse(["As", "Kd", "As"])
        self.assertEqual("POKER_RULE_DUPLICATE_CARD", error.exception.code)
        self.assertEqual("board.cards[2]", error.exception.path)

    def test_CARD_005_exact_combo_notation_is_canonical(self) -> None:
        self.assertEqual("KsKd", str(ExactCombo.parse("KdKs")))
        self.assertEqual("AsKs", str(ExactCombo.parse("KsAs")))
        self.assertEqual("AhKc", str(ExactCombo.parse("KcAh")))
        self.assertEqual("KK", ExactCombo.parse("KsKd").grouped_class)
        self.assertEqual("AKs", ExactCombo.parse("AsKs").grouped_class)
        self.assertEqual("AKo", ExactCombo.parse("AhKc").grouped_class)

    def test_CARD_006_all_exact_combos_are_unique(self) -> None:
        combos = all_exact_combos()
        self.assertEqual(1326, len(combos))
        self.assertEqual(1326, len(set(combos)))

    def test_CARD_007_duplicate_combo_card_fails(self) -> None:
        with self.assertRaises(DomainError) as error:
            ExactCombo.parse("AsAs")
        self.assertEqual("POKER_RULE_DUPLICATE_CARD", error.exception.code)


if __name__ == "__main__":
    unittest.main()

