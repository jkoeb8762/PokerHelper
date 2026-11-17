from __future__ import annotations

import unittest

from _support import SRC_DIR, load_json  # noqa: F401
from pokerhelper.domain import Card, DomainError, HandCategory, evaluate, evaluate_five


class HandEvaluatorTests(unittest.TestCase):
    def test_EVAL_001_reference_corpus(self) -> None:
        fixture = load_json("hand-evaluation-reference-v1.json")
        self.assertEqual("EVAL_REFERENCE_V1", fixture["corpusVersion"])
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                cards = tuple(Card.parse(value) for value in case["cards"])
                result = evaluate(cards)
                self.assertEqual(HandCategory[case["category"]], result.rank.category)
                self.assertEqual(tuple(case["tiebreak"]), result.rank.tiebreak)

    def test_EVAL_002_category_order_is_exact(self) -> None:
        hands = [
            ["As", "Kd", "9h", "6c", "3s"],
            ["Js", "Jd", "Ac", "9h", "4s"],
            ["As", "Ad", "Kc", "Kd", "Qh"],
            ["Qc", "Qd", "Qh", "As", "9d"],
            ["As", "Kd", "Qh", "Jc", "Ts"],
            ["Ah", "Jh", "9h", "4h", "2h"],
            ["Kh", "Kd", "Kc", "2s", "2d"],
            ["Ac", "Ad", "Ah", "As", "Kd"],
            ["As", "Ks", "Qs", "Js", "Ts"],
        ]
        ranks = [evaluate_five(Card.parse(card) for card in hand) for hand in hands]
        self.assertEqual(ranks, sorted(ranks))

    def test_EVAL_003_ties_ignore_suits(self) -> None:
        first = evaluate_five(Card.parse(card) for card in ["As", "Kd", "Qh", "Jc", "Ts"])
        second = evaluate_five(Card.parse(card) for card in ["Ah", "Kc", "Qs", "Jd", "Th"])
        self.assertEqual(first, second)

    def test_EVAL_004_duplicate_card_is_rejected(self) -> None:
        with self.assertRaises(DomainError) as error:
            evaluate(Card.parse(card) for card in ["As", "As", "Qh", "Jc", "Ts", "9d", "2c"])
        self.assertEqual("POKER_RULE_DUPLICATE_CARD", error.exception.code)

    def test_EVAL_005_invalid_card_count_is_rejected(self) -> None:
        with self.assertRaises(DomainError) as error:
            evaluate(Card.parse(card) for card in ["As", "Kd", "Qh", "Jc"])
        self.assertEqual("POKER_RULE_EVALUATION_CARD_COUNT_INVALID", error.exception.code)


if __name__ == "__main__":
    unittest.main()

