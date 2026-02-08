"""Card and Deck classes for Gin Rummy."""

import random
from enum import Enum
from typing import List


class Suit(Enum):
    CLUBS = "C"
    DIAMONDS = "D"
    HEARTS = "H"
    SPADES = "S"


class Rank(Enum):
    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13


RANK_NAMES = {
    Rank.ACE: "A",
    Rank.TWO: "2",
    Rank.THREE: "3",
    Rank.FOUR: "4",
    Rank.FIVE: "5",
    Rank.SIX: "6",
    Rank.SEVEN: "7",
    Rank.EIGHT: "8",
    Rank.NINE: "9",
    Rank.TEN: "10",
    Rank.JACK: "J",
    Rank.QUEEN: "Q",
    Rank.KING: "K",
}


class Card:
    """A playing card with a rank and suit."""

    __slots__ = ("rank", "suit")

    def __init__(self, rank: Rank, suit: Suit):
        self.rank = rank
        self.suit = suit

    @property
    def deadwood_value(self) -> int:
        """Return the deadwood point value of this card.

        Face cards (J, Q, K) are worth 10, Ace is worth 1,
        number cards are worth their face value.
        """
        return min(self.rank.value, 10)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self) -> int:
        return hash((self.rank, self.suit))

    def __lt__(self, other: "Card") -> bool:
        if self.suit == other.suit:
            return self.rank.value < other.rank.value
        return self.suit.value < other.suit.value

    def __le__(self, other: "Card") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Card") -> bool:
        return not self <= other

    def __ge__(self, other: "Card") -> bool:
        return not self < other

    def __repr__(self) -> str:
        return f"Card({RANK_NAMES[self.rank]}{self.suit.value})"

    def __str__(self) -> str:
        return f"{RANK_NAMES[self.rank]}{self.suit.value}"


class Deck:
    """A standard 52-card deck with shuffle, deal, and draw operations."""

    def __init__(self, rng: random.Random = None):
        self._rng = rng or random.Random()
        self._cards: List[Card] = [
            Card(rank, suit) for suit in Suit for rank in Rank
        ]
        self.shuffle()

    def shuffle(self) -> None:
        """Shuffle the deck in place."""
        self._rng.shuffle(self._cards)

    def draw(self) -> Card:
        """Draw and return the top card from the deck.

        Raises:
            IndexError: If the deck is empty.
        """
        if not self._cards:
            raise IndexError("Cannot draw from an empty deck")
        return self._cards.pop()

    def deal(self, num_cards: int) -> List[Card]:
        """Deal a number of cards from the top of the deck.

        Args:
            num_cards: Number of cards to deal.

        Returns:
            List of dealt cards.

        Raises:
            ValueError: If requesting more cards than remain in the deck.
        """
        if num_cards > len(self._cards):
            raise ValueError(
                f"Cannot deal {num_cards} cards, "
                f"only {len(self._cards)} remain"
            )
        dealt = [self._cards.pop() for _ in range(num_cards)]
        return dealt

    @property
    def remaining(self) -> int:
        """Return the number of cards remaining in the deck."""
        return len(self._cards)

    def is_empty(self) -> bool:
        """Return True if no cards remain in the deck."""
        return len(self._cards) == 0

    def __len__(self) -> int:
        return len(self._cards)
