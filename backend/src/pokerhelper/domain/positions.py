"""Six-max positions and deterministic preflop traversal."""

from __future__ import annotations

from enum import Enum
from typing import Iterable

from .errors import fail


class Position(str, Enum):
    UTG = "UTG"
    HJ = "HJ"
    CO = "CO"
    BTN = "BTN"
    SB = "SB"
    BB = "BB"


SIX_MAX_POSITIONS: tuple[Position, ...] = (
    Position.UTG,
    Position.HJ,
    Position.CO,
    Position.BTN,
    Position.SB,
    Position.BB,
)


def clockwise_from(position: Position, *, include_start: bool = False) -> tuple[Position, ...]:
    try:
        index = SIX_MAX_POSITIONS.index(position)
    except ValueError:
        fail(
            "POKER_RULE_POSITION_UNSUPPORTED",
            "position",
            "Position is not part of the six-max MVP table.",
            details={"position": str(position)},
        )
    offset = index if include_start else index + 1
    return tuple(SIX_MAX_POSITIONS[(offset + step) % len(SIX_MAX_POSITIONS)] for step in range(len(SIX_MAX_POSITIONS)))


def next_eligible(after: Position | None, eligible: Iterable[Position]) -> Position | None:
    candidates = set(eligible)
    if not candidates:
        return None
    traversal = SIX_MAX_POSITIONS if after is None else clockwise_from(after)
    return next((position for position in traversal if position in candidates), None)

