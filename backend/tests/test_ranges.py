from __future__ import annotations

from collections import Counter
from decimal import Decimal
import unittest

from _support import SRC_DIR  # noqa: F401
from pokerhelper.domain import (
    Card,
    DomainError,
    ExactCombo,
    RangeEntry,
    WeightedRange,
    all_exact_combos,
    combos_by_class,
    grouped_classes,
)


class RangeTests(unittest.TestCase):
    def test_RANGE_001_1326_combos_map_to_169_classes(self) -> None:
        combos = all_exact_combos()
        labels = grouped_classes()
        self.assertEqual(1326, len(combos))
        self.assertEqual(169, len(labels))
        self.assertEqual(169, len(set(labels)))
        self.assertEqual(set(labels), {combo.grouped_class for combo in combos})

    def test_RANGE_002_class_combo_counts_are_exact(self) -> None:
        grouped = combos_by_class()
        counts = Counter(len(combos) for combos in grouped.values())
        self.assertEqual(13, counts[6])
        self.assertEqual(78, counts[4])
        self.assertEqual(78, counts[12])
        self.assertEqual(6, len(grouped["KK"]))
        self.assertEqual(4, len(grouped["AKs"]))
        self.assertEqual(12, len(grouped["AKo"]))

    def test_RANGE_003_normalization_is_exact_and_deterministic(self) -> None:
        source = WeightedRange.from_mapping({"AsKs": "1", "AhKh": "1", "AdKd": "0.5"})
        first = source.normalized()
        second = source.normalized()
        self.assertEqual(first, second)
        self.assertEqual(Decimal("1"), first.total_weight)
        self.assertEqual(Decimal("0.4"), first.weight_for("AsKs"))
        self.assertEqual(Decimal("0.2"), first.weight_for("AdKd"))

    def test_RANGE_004_card_removal_counts(self) -> None:
        full = WeightedRange.full()
        one_blocked = full.remove_cards([Card.parse("As")])
        two_blocked = full.remove_cards([Card.parse("As"), Card.parse("Kd")])
        self.assertEqual(1275, len(one_blocked.entries))
        self.assertEqual(1225, len(two_blocked.entries))
        self.assertTrue(all(Card.parse("As") not in entry.combo.cards for entry in one_blocked.entries))

    def test_RANGE_005_grouped_aggregation_uses_exact_weights(self) -> None:
        source = WeightedRange.from_mapping({"AsKs": "1", "AhKh": "0.5", "AhKc": "0.25"})
        grouped = source.grouped_weights()
        self.assertEqual(Decimal("1.5"), grouped["AKs"])
        self.assertEqual(Decimal("0.25"), grouped["AKo"])

    def test_RANGE_006_duplicate_combo_fails(self) -> None:
        combo = ExactCombo.parse("AsKs")
        with self.assertRaises(DomainError) as error:
            WeightedRange((RangeEntry(combo, Decimal("1")), RangeEntry(combo, Decimal("0.5"))))
        self.assertEqual("STRATEGY_DUPLICATE_COMBO", error.exception.code)

    def test_RANGE_007_invalid_weight_fails(self) -> None:
        with self.assertRaises(DomainError) as error:
            RangeEntry(ExactCombo.parse("AsKs"), Decimal("1.1"))
        self.assertEqual("STRATEGY_RANGE_WEIGHT_OUT_OF_BOUNDS", error.exception.code)

    def test_RANGE_008_zero_range_cannot_normalize(self) -> None:
        source = WeightedRange.from_mapping({"AsKs": "0"})
        with self.assertRaises(DomainError) as error:
            source.normalized()
        self.assertEqual("STRATEGY_RANGE_EMPTY", error.exception.code)

    def test_RANGE_009_duplicate_blocked_card_fails(self) -> None:
        full = WeightedRange.full()
        with self.assertRaises(DomainError) as error:
            full.remove_cards([Card.parse("As"), Card.parse("As")])
        self.assertEqual("POKER_RULE_DUPLICATE_CARD", error.exception.code)


if __name__ == "__main__":
    unittest.main()

