"""Versioned cash-game rake policies."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .decimal_utils import CENTI_BB, ONE, ZERO, as_decimal, floor_to_increment
from .errors import fail


class RakeCollectionRule(str, Enum):
    QUALIFYING_POSTFLOP_POT = "QUALIFYING_POSTFLOP_POT"


@dataclass(frozen=True, slots=True)
class RakePolicy:
    policy_version: str
    rate: Decimal
    cap_bb: Decimal
    no_flop_no_drop: bool
    collection_rule: RakeCollectionRule
    rounding_increment_bb: Decimal = CENTI_BB

    def __post_init__(self) -> None:
        rate = as_decimal(self.rate, path="rakePolicy.rate")
        cap = as_decimal(self.cap_bb, path="rakePolicy.capBb")
        increment = as_decimal(self.rounding_increment_bb, path="rakePolicy.roundingIncrementBb")
        if not self.policy_version:
            fail("SCHEMA_RAKE_VERSION_REQUIRED", "rakePolicy.policyVersion", "Rake policy version is required.")
        if rate < ZERO or rate > ONE:
            fail("POKER_RULE_RAKE_RATE_INVALID", "rakePolicy.rate", "Rake rate must be between 0 and 1.")
        if cap < ZERO:
            fail("POKER_RULE_RAKE_CAP_NEGATIVE", "rakePolicy.capBb", "Rake cap cannot be negative.")
        if increment <= ZERO:
            fail(
                "POKER_RULE_RAKE_INCREMENT_NOT_POSITIVE",
                "rakePolicy.roundingIncrementBb",
                "Rake rounding increment must be positive.",
            )
        object.__setattr__(self, "rate", rate)
        object.__setattr__(self, "cap_bb", cap)
        object.__setattr__(self, "rounding_increment_bb", increment)


MVP_RAKE_POLICY = RakePolicy(
    policy_version="MVP_CASH_5PCT_1BB_NFND_V1",
    rate=Decimal("0.05"),
    cap_bb=Decimal("1"),
    no_flop_no_drop=True,
    collection_rule=RakeCollectionRule.QUALIFYING_POSTFLOP_POT,
)


def calculate_rake(
    pot_bb: Decimal | int | str,
    *,
    saw_flop: bool,
    qualifying: bool = True,
    policy: RakePolicy = MVP_RAKE_POLICY,
) -> Decimal:
    pot = as_decimal(pot_bb, path="potBb")
    if pot < ZERO:
        fail("POKER_RULE_POT_NEGATIVE", "potBb", "Pot cannot be negative.")
    if pot == ZERO or not qualifying or (policy.no_flop_no_drop and not saw_flop):
        return ZERO
    raw = min(pot * policy.rate, policy.cap_bb)
    return floor_to_increment(raw, policy.rounding_increment_bb, path="rakeBb")

