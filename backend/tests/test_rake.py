from __future__ import annotations

from decimal import Decimal
import unittest

from _support import SRC_DIR  # noqa: F401
from pokerhelper.domain import DomainError, MVP_RAKE_POLICY, calculate_rake


class RakeTests(unittest.TestCase):
    def test_RAKE_001_preset_is_named_and_exact(self) -> None:
        self.assertEqual("MVP_CASH_5PCT_1BB_NFND_V1", MVP_RAKE_POLICY.policy_version)
        self.assertEqual(Decimal("0.05"), MVP_RAKE_POLICY.rate)
        self.assertEqual(Decimal("1"), MVP_RAKE_POLICY.cap_bb)

    def test_RAKE_002_no_flop_no_drop(self) -> None:
        self.assertEqual(Decimal("0"), calculate_rake("100", saw_flop=False))

    def test_RAKE_003_rounds_down_to_centi_bb(self) -> None:
        self.assertEqual(Decimal("0"), calculate_rake("0.19", saw_flop=True))
        self.assertEqual(Decimal("0.01"), calculate_rake("0.20", saw_flop=True))
        self.assertEqual(Decimal("0.61"), calculate_rake("12.39", saw_flop=True))

    def test_RAKE_004_cap_applies(self) -> None:
        self.assertEqual(Decimal("0.99"), calculate_rake("19.99", saw_flop=True))
        self.assertEqual(Decimal("1"), calculate_rake("20", saw_flop=True))
        self.assertEqual(Decimal("1"), calculate_rake("200", saw_flop=True))

    def test_RAKE_005_non_qualifying_pot_is_zero(self) -> None:
        self.assertEqual(Decimal("0"), calculate_rake("20", saw_flop=True, qualifying=False))

    def test_RAKE_006_negative_pot_fails(self) -> None:
        with self.assertRaises(DomainError) as error:
            calculate_rake("-0.01", saw_flop=True)
        self.assertEqual("POKER_RULE_POT_NEGATIVE", error.exception.code)


if __name__ == "__main__":
    unittest.main()

