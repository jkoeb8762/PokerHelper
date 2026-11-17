"""Immutable cards, exact starting-hand combos, decks, and boards."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from typing import Iterable, Iterator

from .errors import fail


class Rank(str, Enum):
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "T"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"

    @property
    def strength(self) -> int:
        return RANK_STRENGTH[self]

    @classmethod
    def parse(cls, value: str, *, path: str = "card.rank") -> "Rank":
        try:
            return cls(value.upper())
        except (ValueError, AttributeError):
            fail(
                "SCHEMA_CARD_RANK_INVALID",
                path,
                "Card rank must be one of 2-9, T, J, Q, K, or A.",
                details={"received": value},
            )


RANKS_DESCENDING: tuple[Rank, ...] = (
    Rank.ACE,
    Rank.KING,
    Rank.QUEEN,
    Rank.JACK,
    Rank.TEN,
    Rank.NINE,
    Rank.EIGHT,
    Rank.SEVEN,
    Rank.SIX,
    Rank.FIVE,
    Rank.FOUR,
    Rank.THREE,
    Rank.TWO,
)
RANK_STRENGTH = {rank: 14 - index for index, rank in enumerate(RANKS_DESCENDING)}


class Suit(str, Enum):
    SPADES = "s"
    HEARTS = "h"
    DIAMONDS = "d"
    CLUBS = "c"

    @classmethod
    def parse(cls, value: str, *, path: str = "card.suit") -> "Suit":
        try:
            return cls(value.lower())
        except (ValueError, AttributeError):
            fail(
                "SCHEMA_CARD_SUIT_INVALID",
                path,
                "Card suit must be s, h, d, or c.",
                details={"received": value},
            )


SUITS: tuple[Suit, ...] = (Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS)
SUIT_ORDER = {suit: index for index, suit in enumerate(SUITS)}
SUIT_SYMBOL = {
    Suit.SPADES: "♠",
    Suit.HEARTS: "♥",
    Suit.DIAMONDS: "♦",
    Suit.CLUBS: "♣",
}


@dataclass(frozen=True, slots=True)
class Card:
    rank: Rank
    suit: Suit

    @classmethod
    def parse(cls, value: str, *, path: str = "card") -> "Card":
        if not isinstance(value, str) or len(value) != 2:
            fail(
                "SCHEMA_CARD_NOTATION_INVALID",
                path,
                "Canonical card notation must contain exactly two characters, such as As.",
                details={"received": value},
            )
        return cls(
            Rank.parse(value[0], path=f"{path}.rank"),
            Suit.parse(value[1], path=f"{path}.suit"),
        )

    @property
    def unicode(self) -> str:
        return f"{self.rank.value}{SUIT_SYMBOL[self.suit]}"

    @property
    def sort_key(self) -> tuple[int, int]:
        return (-self.rank.strength, SUIT_ORDER[self.suit])

    def __str__(self) -> str:
        return f"{self.rank.value}{self.suit.value}"


@dataclass(frozen=True, slots=True)
class ExactCombo:
    first: Card
    second: Card

    def __post_init__(self) -> None:
        if self.first == self.second:
            fail(
                "POKER_RULE_DUPLICATE_CARD",
                "combo",
                "A starting-hand combo must contain two distinct cards.",
                details={"card": str(self.first)},
            )
        ordered = sorted((self.first, self.second), key=lambda card: card.sort_key)
        if (self.first, self.second) != (ordered[0], ordered[1]):
            object.__setattr__(self, "first", ordered[0])
            object.__setattr__(self, "second", ordered[1])

    @classmethod
    def parse(cls, value: str, *, path: str = "combo") -> "ExactCombo":
        if not isinstance(value, str) or len(value) != 4:
            fail(
                "SCHEMA_COMBO_NOTATION_INVALID",
                path,
                "Exact combo notation must contain two canonical cards, such as AsKs.",
                details={"received": value},
            )
        return cls(
            Card.parse(value[:2], path=f"{path}.first"),
            Card.parse(value[2:], path=f"{path}.second"),
        )

    @property
    def grouped_class(self) -> str:
        high = self.first.rank.value
        low = self.second.rank.value
        if self.first.rank == self.second.rank:
            return f"{high}{low}"
        suffix = "s" if self.first.suit == self.second.suit else "o"
        return f"{high}{low}{suffix}"

    @property
    def cards(self) -> tuple[Card, Card]:
        return self.first, self.second

    def __str__(self) -> str:
        return f"{self.first}{self.second}"


@dataclass(frozen=True, slots=True)
class Board:
    cards: tuple[Card, ...] = ()

    def __post_init__(self) -> None:
        cards = tuple(self.cards)
        object.__setattr__(self, "cards", cards)
        if len(cards) not in {0, 3, 4, 5}:
            fail(
                "POKER_RULE_BOARD_SIZE_INVALID",
                "board.cards",
                "A Hold'em board must contain 0, 3, 4, or 5 cards.",
                details={"count": len(cards)},
            )
        _require_unique(cards, path="board.cards")

    @classmethod
    def parse(cls, values: Iterable[str]) -> "Board":
        return cls(tuple(Card.parse(value, path=f"board.cards[{index}]") for index, value in enumerate(values)))


def _require_unique(cards: Iterable[Card], *, path: str) -> None:
    seen: set[Card] = set()
    for index, card in enumerate(cards):
        if card in seen:
            fail(
                "POKER_RULE_DUPLICATE_CARD",
                f"{path}[{index}]",
                "The same physical card cannot appear more than once.",
                details={"card": str(card)},
            )
        seen.add(card)


def all_cards() -> tuple[Card, ...]:
    return tuple(Card(rank, suit) for rank in RANKS_DESCENDING for suit in SUITS)


def all_exact_combos() -> tuple[ExactCombo, ...]:
    return tuple(sorted((ExactCombo(first, second) for first, second in combinations(all_cards(), 2)), key=str))


class Deck:
    """A deterministic canonical deck; randomization belongs to an adapter."""

    def __init__(self, cards: Iterable[Card] | None = None) -> None:
        self._cards = tuple(cards) if cards is not None else all_cards()
        if len(self._cards) != 52:
            fail(
                "POKER_RULE_DECK_SIZE_INVALID",
                "deck.cards",
                "A canonical Hold'em deck must contain exactly 52 cards.",
                details={"count": len(self._cards)},
            )
        _require_unique(self._cards, path="deck.cards")

    @property
    def cards(self) -> tuple[Card, ...]:
        return self._cards

    def __len__(self) -> int:
        return len(self._cards)

    def __iter__(self) -> Iterator[Card]:
        return iter(self._cards)

