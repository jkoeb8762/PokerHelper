"""Exact five-to-seven-card No-Limit Hold'em hand evaluation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import IntEnum
from itertools import combinations
from typing import Iterable

from .cards import Card
from .errors import fail


class HandCategory(IntEnum):
    HIGH_CARD = 0
    ONE_PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8


@dataclass(frozen=True, order=True, slots=True)
class HandRank:
    category: HandCategory
    tiebreak: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class HandEvaluation:
    rank: HandRank
    best_five: tuple[Card, ...]


def evaluate_five(cards: Iterable[Card]) -> HandRank:
    hand = tuple(cards)
    _validate_cards(hand, expected=5)

    strengths = [card.rank.strength for card in hand]
    counts = Counter(strengths)
    ordered_counts = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    flush = len({card.suit for card in hand}) == 1
    straight_high = _straight_high(set(strengths))

    if flush and straight_high is not None:
        return HandRank(HandCategory.STRAIGHT_FLUSH, (straight_high,))

    if ordered_counts[0][1] == 4:
        quad = ordered_counts[0][0]
        kicker = max(rank for rank, count in counts.items() if count == 1)
        return HandRank(HandCategory.FOUR_OF_A_KIND, (quad, kicker))

    if sorted(counts.values()) == [2, 3]:
        trip = max(rank for rank, count in counts.items() if count == 3)
        pair = max(rank for rank, count in counts.items() if count == 2)
        return HandRank(HandCategory.FULL_HOUSE, (trip, pair))

    if flush:
        return HandRank(HandCategory.FLUSH, tuple(sorted(strengths, reverse=True)))

    if straight_high is not None:
        return HandRank(HandCategory.STRAIGHT, (straight_high,))

    if ordered_counts[0][1] == 3:
        trip = ordered_counts[0][0]
        kickers = sorted((rank for rank, count in counts.items() if count == 1), reverse=True)
        return HandRank(HandCategory.THREE_OF_A_KIND, (trip, *kickers))

    pairs = sorted((rank for rank, count in counts.items() if count == 2), reverse=True)
    if len(pairs) == 2:
        kicker = max(rank for rank, count in counts.items() if count == 1)
        return HandRank(HandCategory.TWO_PAIR, (pairs[0], pairs[1], kicker))

    if len(pairs) == 1:
        kickers = sorted((rank for rank, count in counts.items() if count == 1), reverse=True)
        return HandRank(HandCategory.ONE_PAIR, (pairs[0], *kickers))

    return HandRank(HandCategory.HIGH_CARD, tuple(sorted(strengths, reverse=True)))


def evaluate(cards: Iterable[Card]) -> HandEvaluation:
    available = tuple(cards)
    if len(available) not in {5, 6, 7}:
        fail(
            "POKER_RULE_EVALUATION_CARD_COUNT_INVALID",
            "cards",
            "Hold'em evaluation requires five, six, or seven cards.",
            details={"count": len(available)},
        )
    _validate_cards(available, expected=None)

    ranked: list[tuple[HandRank, tuple[str, ...], tuple[Card, ...]]] = []
    for candidate in combinations(available, 5):
        canonical_cards = tuple(sorted(candidate, key=lambda card: card.sort_key))
        notation = tuple(str(card) for card in canonical_cards)
        ranked.append((evaluate_five(candidate), notation, canonical_cards))
    best_rank = max(item[0] for item in ranked)
    tied = [item for item in ranked if item[0] == best_rank]
    _, _, best_five = min(tied, key=lambda item: item[1])
    return HandEvaluation(best_rank, best_five)


def _straight_high(strengths: set[int]) -> int | None:
    if len(strengths) != 5:
        return None
    if strengths == {14, 5, 4, 3, 2}:
        return 5
    low = min(strengths)
    high = max(strengths)
    return high if high - low == 4 else None


def _validate_cards(cards: tuple[Card, ...], *, expected: int | None) -> None:
    if expected is not None and len(cards) != expected:
        fail(
            "POKER_RULE_EVALUATION_CARD_COUNT_INVALID",
            "cards",
            f"Expected exactly {expected} cards.",
            details={"count": len(cards)},
        )
    seen: set[Card] = set()
    for index, card in enumerate(cards):
        if card in seen:
            fail(
                "POKER_RULE_DUPLICATE_CARD",
                f"cards[{index}]",
                "The same physical card cannot be evaluated twice.",
                details={"card": str(card)},
            )
        seen.add(card)

