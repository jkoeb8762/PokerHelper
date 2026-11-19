"""Exact-decimal Trainer scoring, sampling, and mixed-strategy RNG rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from enum import Enum
from typing import Protocol, Sequence

from .decimal_utils import ONE, ZERO, as_decimal, normalized_decimal
from .errors import fail


SCORING_POLICY_VERSION = "1"
SAMPLING_POLICY_VERSION = "UNIFORM_NODE_REACH_WEIGHTED_COMBO_V1"
FREQUENCY_NORMALIZATION_TOLERANCE = Decimal("0.000000001")
FREQUENCY_SUPPORT_TOLERANCE = Decimal("0.01")
CALIBRATION_MINIMUM_SAMPLE = 50


class FeedbackSeverity(str, Enum):
    NO_MATERIAL_EV_LOSS = "NO_MATERIAL_EV_LOSS"
    SMALL_EV_LOSS = "SMALL_EV_LOSS"
    SIGNIFICANT_MISTAKE = "SIGNIFICANT_MISTAKE"
    MAJOR_MISTAKE = "MAJOR_MISTAKE"


class StrategyStatus(str, Enum):
    PURE_PREFERRED = "PURE_PREFERRED"
    SUPPORTED_MIX = "SUPPORTED_MIX"
    LOW_FREQUENCY_SUPPORTED = "LOW_FREQUENCY_SUPPORTED"
    EV_EQUIVALENT_OUTSIDE_MIX = "EV_EQUIVALENT_OUTSIDE_MIX"
    COSTLY_DEVIATION = "COSTLY_DEVIATION"


@dataclass(frozen=True, slots=True)
class ReferenceAction:
    option_id: str
    frequency: Decimal
    action_ev_bb: Decimal

    def __post_init__(self) -> None:
        frequency = as_decimal(self.frequency, path=f"referenceSnapshot.{self.option_id}.frequency")
        ev = as_decimal(self.action_ev_bb, path=f"referenceSnapshot.{self.option_id}.actionEvBb")
        if frequency < ZERO or frequency > ONE:
            fail("TRAINER_FREQUENCY_OUT_OF_RANGE", "referenceSnapshot", "Reference frequencies must be between zero and one.")
        object.__setattr__(self, "frequency", frequency)
        object.__setattr__(self, "action_ev_bb", ev)


@dataclass(frozen=True, slots=True)
class ScoredDecision:
    highest_ev_option_id: str
    ev_loss_bb: Decimal
    severity: FeedbackSeverity
    strategy_status: StrategyStatus
    interpretation: str


@dataclass(frozen=True, slots=True)
class RngBand:
    option_id: str
    start: int
    end: int

    @property
    def count(self) -> int:
        return self.end - self.start + 1


class RandomIndexSource(Protocol):
    def randbelow(self, upper: int) -> int: ...


def score_decision(
    reference: Sequence[ReferenceAction],
    selected_option_id: str,
    *,
    support_tolerance: Decimal = FREQUENCY_SUPPORT_TOLERANCE,
) -> ScoredDecision:
    if not reference:
        fail("TRAINER_REFERENCE_EMPTY", "referenceSnapshot", "At least one offered action is required for scoring.")
    if len({item.option_id for item in reference}) != len(reference):
        fail("TRAINER_REFERENCE_DUPLICATE", "referenceSnapshot", "Reference option identifiers must be unique.")
    total = sum((item.frequency for item in reference), ZERO)
    if abs(total - ONE) > FREQUENCY_NORMALIZATION_TOLERANCE:
        fail(
            "TRAINER_FREQUENCY_NOT_NORMALIZED",
            "referenceSnapshot",
            "Reference frequencies must sum to one.",
            details={"sum": normalized_decimal(total)},
        )
    selected = next((item for item in reference if item.option_id == selected_option_id), None)
    if selected is None:
        fail("TRAINER_OPTION_NOT_OFFERED", "selectedOptionId", "The selected action was not offered for this decision.")

    highest = max(reference, key=lambda item: item.action_ev_bb)
    loss = highest.action_ev_bb - selected.action_ev_bb
    if loss < ZERO:
        fail("TRAINER_EV_LOSS_NEGATIVE", "evLossBb", "EV loss cannot be negative.")
    severity = severity_for(loss)
    material = [item for item in reference if item.frequency >= support_tolerance]
    if selected.frequency >= support_tolerance and loss <= Decimal("0.010"):
        if selected.frequency <= Decimal("0.05"):
            status = StrategyStatus.LOW_FREQUENCY_SUPPORTED
        elif len(material) > 1:
            status = StrategyStatus.SUPPORTED_MIX
        else:
            status = StrategyStatus.PURE_PREFERRED
    elif loss <= Decimal("0.010"):
        status = StrategyStatus.EV_EQUIVALENT_OUTSIDE_MIX
    else:
        status = StrategyStatus.COSTLY_DEVIATION
    return ScoredDecision(
        highest_ev_option_id=highest.option_id,
        ev_loss_bb=loss,
        severity=severity,
        strategy_status=status,
        interpretation=_interpretation(status, severity, selected.frequency),
    )


def severity_for(ev_loss_bb: Decimal | str | int) -> FeedbackSeverity:
    loss = as_decimal(ev_loss_bb, path="evLossBb")
    if loss < ZERO:
        fail("TRAINER_EV_LOSS_NEGATIVE", "evLossBb", "EV loss cannot be negative.")
    if loss <= Decimal("0.010"):
        return FeedbackSeverity.NO_MATERIAL_EV_LOSS
    if loss <= Decimal("0.050"):
        return FeedbackSeverity.SMALL_EV_LOSS
    if loss <= Decimal("0.250"):
        return FeedbackSeverity.SIGNIFICANT_MISTAKE
    return FeedbackSeverity.MAJOR_MISTAKE


def rng_bands(reference: Sequence[ReferenceAction]) -> tuple[RngBand, ...]:
    """Assign the integers 1..100 with largest remainders and stable ties."""

    if not reference:
        fail("TRAINER_REFERENCE_EMPTY", "referenceSnapshot", "RNG mapping requires at least one action.")
    total = sum((item.frequency for item in reference), ZERO)
    if abs(total - ONE) > FREQUENCY_NORMALIZATION_TOLERANCE:
        fail("TRAINER_FREQUENCY_NOT_NORMALIZED", "referenceSnapshot", "RNG frequencies must sum to one.")
    raw = [item.frequency * Decimal(100) for item in reference]
    counts = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in raw]
    remaining = 100 - sum(counts)
    order = sorted(range(len(reference)), key=lambda index: (-(raw[index] - counts[index]), index))
    for index in order[:remaining]:
        counts[index] += 1
    bands: list[RngBand] = []
    cursor = 1
    for item, count in zip(reference, counts, strict=True):
        if count:
            bands.append(RngBand(item.option_id, cursor, cursor + count - 1))
            cursor += count
    if cursor != 101:
        fail("TRAINER_RNG_MAPPING_INVALID", "rngMapping", "RNG mapping must assign every integer from 1 through 100.")
    return tuple(bands)


def weighted_index(weights: Sequence[Decimal | str | int], randomizer: RandomIndexSource) -> int:
    """Choose an index from exact decimal weights without binary floating point."""

    parsed = [as_decimal(value, path=f"weights[{index}]") for index, value in enumerate(weights)]
    if any(value < ZERO for value in parsed):
        fail("TRAINER_SAMPLING_WEIGHT_NEGATIVE", "weights", "Sampling weights cannot be negative.")
    places = max((max(0, -value.as_tuple().exponent) for value in parsed), default=0)
    multiplier = Decimal(10) ** places
    integer_weights = [int(value * multiplier) for value in parsed]
    total = sum(integer_weights)
    if total <= 0:
        fail("TRAINER_SAMPLING_RANGE_EMPTY", "weights", "At least one sampling weight must be positive.")
    roll = randomizer.randbelow(total)
    if roll < 0 or roll >= total:
        fail("TRAINER_RANDOM_INDEX_INVALID", "randomizer", "The random source returned an out-of-range index.")
    cumulative = 0
    for index, weight in enumerate(integer_weights):
        cumulative += weight
        if roll < cumulative:
            return index
    fail("TRAINER_SAMPLING_FAILED", "weights", "A valid weighted sample could not be selected.")


def _interpretation(status: StrategyStatus, severity: FeedbackSeverity, frequency: Decimal) -> str:
    if status == StrategyStatus.LOW_FREQUENCY_SUPPORTED:
        return (
            f"This action appears at {normalized_decimal(frequency * 100)}% in the reference mix. "
            "Its rarity is not itself a mistake; EV loss determines the training priority."
        )
    if status == StrategyStatus.SUPPORTED_MIX:
        return "This action is part of the reference mix; the EV difference determines whether it needs review."
    if status == StrategyStatus.PURE_PREFERRED:
        return "This is the reference strategy's material action for this exact combo."
    if status == StrategyStatus.EV_EQUIVALENT_OUTSIDE_MIX:
        return "This action is not used materially in the reference mix, but its EV is equivalent within policy tolerance."
    if severity == FeedbackSeverity.MAJOR_MISTAKE:
        return "This deviation has a large source-model EV cost and is a priority for review."
    if severity == FeedbackSeverity.SIGNIFICANT_MISTAKE:
        return "This deviation has a meaningful source-model EV cost and should be reviewed."
    return "This action is outside the material reference mix and has measurable source-model EV loss."
