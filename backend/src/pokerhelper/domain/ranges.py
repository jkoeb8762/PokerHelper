"""Exact-combo preflop classes and sparse weighted ranges."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping

from .cards import Card, ExactCombo, RANKS_DESCENDING, all_exact_combos
from .decimal_utils import ONE, ZERO, as_decimal
from .errors import fail


@dataclass(frozen=True, slots=True)
class RangeEntry:
    combo: ExactCombo
    weight: Decimal

    def __post_init__(self) -> None:
        weight = as_decimal(self.weight, path=f"range.entries[{self.combo}].weight")
        if weight < ZERO or weight > ONE:
            fail(
                "STRATEGY_RANGE_WEIGHT_OUT_OF_BOUNDS",
                f"range.entries[{self.combo}].weight",
                "Range weight must be between 0 and 1.",
                details={"weight": str(weight)},
            )
        object.__setattr__(self, "weight", weight)


@dataclass(frozen=True, slots=True)
class WeightedRange:
    entries: tuple[RangeEntry, ...]

    def __post_init__(self) -> None:
        entries = tuple(sorted(tuple(self.entries), key=lambda entry: str(entry.combo)))
        seen: set[ExactCombo] = set()
        for index, entry in enumerate(entries):
            if entry.combo in seen:
                fail(
                    "STRATEGY_DUPLICATE_COMBO",
                    f"range.entries[{index}].combo",
                    "A range can contain an exact combo only once.",
                    details={"combo": str(entry.combo)},
                )
            seen.add(entry.combo)
        object.__setattr__(self, "entries", entries)

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[ExactCombo | str, Decimal | int | str],
    ) -> "WeightedRange":
        entries = []
        for combo, weight in values.items():
            exact = ExactCombo.parse(combo) if isinstance(combo, str) else combo
            entries.append(RangeEntry(exact, as_decimal(weight, path=f"range[{exact}]")))
        return cls(tuple(entries))

    @classmethod
    def full(cls) -> "WeightedRange":
        return cls(tuple(RangeEntry(combo, ONE) for combo in all_exact_combos()))

    @property
    def total_weight(self) -> Decimal:
        return sum((entry.weight for entry in self.entries), ZERO)

    def normalized(self) -> "WeightedRange":
        positive = [entry for entry in self.entries if entry.weight > ZERO]
        total = sum((entry.weight for entry in positive), ZERO)
        if total == ZERO:
            fail(
                "STRATEGY_RANGE_EMPTY",
                "range.entries",
                "A zero-weight range cannot be normalized.",
            )
        normalized: list[RangeEntry] = []
        assigned = ZERO
        for entry in positive[:-1]:
            weight = entry.weight / total
            assigned += weight
            normalized.append(RangeEntry(entry.combo, weight))
        last_weight = ONE - assigned
        normalized.append(RangeEntry(positive[-1].combo, last_weight))
        return WeightedRange(tuple(normalized))

    def remove_cards(self, blocked: Iterable[Card]) -> "WeightedRange":
        blocked_cards = tuple(blocked)
        if len(set(blocked_cards)) != len(blocked_cards):
            fail(
                "POKER_RULE_DUPLICATE_CARD",
                "blockedCards",
                "Blocked cards must be distinct.",
            )
        blocked_set = set(blocked_cards)
        return WeightedRange(
            tuple(
                entry
                for entry in self.entries
                if entry.combo.first not in blocked_set and entry.combo.second not in blocked_set
            )
        )

    def grouped_weights(self) -> dict[str, Decimal]:
        result = {label: ZERO for label in grouped_classes()}
        for entry in self.entries:
            result[entry.combo.grouped_class] += entry.weight
        return result

    def weight_for(self, combo: ExactCombo | str) -> Decimal:
        target = ExactCombo.parse(combo) if isinstance(combo, str) else combo
        return next((entry.weight for entry in self.entries if entry.combo == target), ZERO)


def grouped_classes() -> tuple[str, ...]:
    labels: list[str] = []
    for row, first in enumerate(RANKS_DESCENDING):
        for column, second in enumerate(RANKS_DESCENDING):
            if row == column:
                labels.append(f"{first.value}{second.value}")
            elif row < column:
                labels.append(f"{first.value}{second.value}s")
            else:
                labels.append(f"{second.value}{first.value}o")
    return tuple(labels)


def combos_by_class() -> dict[str, tuple[ExactCombo, ...]]:
    grouped: dict[str, list[ExactCombo]] = {label: [] for label in grouped_classes()}
    for combo in all_exact_combos():
        grouped[combo.grouped_class].append(combo)
    return {label: tuple(sorted(combos, key=str)) for label, combos in grouped.items()}

