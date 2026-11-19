from __future__ import annotations

from decimal import Decimal
import unittest

from pokerhelper.domain.errors import DomainError
from pokerhelper.domain.trainer import (
    FeedbackSeverity,
    ReferenceAction,
    StrategyStatus,
    rng_bands,
    score_decision,
    severity_for,
    weighted_index,
)


class FixedRandom:
    def __init__(self, value: int) -> None:
        self.value = value

    def randbelow(self, upper: int) -> int:
        self.upper = upper
        return self.value


class TrainerFeedbackTests(unittest.TestCase):
    def test_ev_loss_uses_unrounded_exact_decimals(self) -> None:
        result = score_decision(
            (
                ReferenceAction("fold", Decimal("0.1"), Decimal("0")),
                ReferenceAction("call", Decimal("0.9"), Decimal("0.1844")),
            ),
            "fold",
        )
        self.assertEqual(Decimal("0.1844"), result.ev_loss_bb)
        self.assertEqual(FeedbackSeverity.SIGNIFICANT_MISTAKE, result.severity)
        self.assertEqual("call", result.highest_ev_option_id)

    def test_feedback_threshold_boundaries_are_inclusive(self) -> None:
        self.assertEqual(FeedbackSeverity.NO_MATERIAL_EV_LOSS, severity_for("0.010"))
        self.assertEqual(FeedbackSeverity.SMALL_EV_LOSS, severity_for("0.050"))
        self.assertEqual(FeedbackSeverity.SIGNIFICANT_MISTAKE, severity_for("0.250"))
        self.assertEqual(FeedbackSeverity.MAJOR_MISTAKE, severity_for("0.2500001"))

    def test_low_frequency_support_is_not_conflated_with_cost(self) -> None:
        result = score_decision(
            (
                ReferenceAction("fold", Decimal("0.02"), Decimal("0.100")),
                ReferenceAction("raise", Decimal("0.98"), Decimal("0.105")),
            ),
            "fold",
        )
        self.assertEqual(StrategyStatus.LOW_FREQUENCY_SUPPORTED, result.strategy_status)
        self.assertEqual(FeedbackSeverity.NO_MATERIAL_EV_LOSS, result.severity)
        self.assertIn("rarity is not itself a mistake", result.interpretation)

    def test_zero_frequency_costly_action_is_a_deviation(self) -> None:
        result = score_decision(
            (
                ReferenceAction("fold", Decimal("0"), Decimal("0")),
                ReferenceAction("raise", Decimal("1"), Decimal("0.3")),
            ),
            "fold",
        )
        self.assertEqual(StrategyStatus.COSTLY_DEVIATION, result.strategy_status)
        self.assertEqual(FeedbackSeverity.MAJOR_MISTAKE, result.severity)

    def test_solver_noise_is_not_presented_as_material_support(self) -> None:
        result = score_decision(
            (
                ReferenceAction("fold", Decimal("0.995575229399"), Decimal("0")),
                ReferenceAction("call", Decimal("0.004424770601"), Decimal("-12.882187987722")),
            ),
            "call",
        )
        self.assertEqual(StrategyStatus.COSTLY_DEVIATION, result.strategy_status)
        self.assertEqual(FeedbackSeverity.MAJOR_MISTAKE, result.severity)
        self.assertIn("priority for review", result.interpretation)

    def test_material_frequency_with_large_ev_gap_is_not_called_supported(self) -> None:
        result = score_decision(
            (
                ReferenceAction("fold", Decimal("0.98"), Decimal("0")),
                ReferenceAction("call", Decimal("0.02"), Decimal("-1.5")),
            ),
            "call",
        )
        self.assertEqual(StrategyStatus.COSTLY_DEVIATION, result.strategy_status)
        self.assertEqual(FeedbackSeverity.MAJOR_MISTAKE, result.severity)

    def test_rng_bands_use_largest_remainder_and_stable_ties(self) -> None:
        bands = rng_bands(
            (
                ReferenceAction("fold", Decimal("0.333"), Decimal("0")),
                ReferenceAction("call", Decimal("0.333"), Decimal("0")),
                ReferenceAction("raise", Decimal("0.334"), Decimal("0")),
            )
        )
        self.assertEqual((1, 33), (bands[0].start, bands[0].end))
        self.assertEqual((34, 66), (bands[1].start, bands[1].end))
        self.assertEqual((67, 100), (bands[2].start, bands[2].end))
        self.assertEqual(100, sum(band.count for band in bands))

    def test_weighted_sampling_never_selects_zero_weight(self) -> None:
        randomizer = FixedRandom(0)
        self.assertEqual(1, weighted_index(("0", "0.25", "0.75"), randomizer))
        self.assertEqual(100, randomizer.upper)
        self.assertEqual(2, weighted_index(("0", "0.25", "0.75"), FixedRandom(25)))

    def test_weighted_sampling_rejects_empty_range(self) -> None:
        with self.assertRaises(DomainError) as raised:
            weighted_index(("0", "0"), FixedRandom(0))
        self.assertEqual("TRAINER_SAMPLING_RANGE_EMPTY", raised.exception.code)


if __name__ == "__main__":
    unittest.main()
