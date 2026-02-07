"""Game state management for Gin Rummy."""

from enum import Enum, auto
from typing import List, Optional

from engine.card import Card, Deck


class GamePhase(Enum):
    DRAW = auto()
    DISCARD = auto()
    KNOCK = auto()
    END = auto()


class PlayerView:
    """An immutable view of the game state for a specific player.

    This is what bots receive — they can see their own hand, the
    discard pile, and deck size, but not the opponent's hand.
    """

    def __init__(
        self,
        hand: List[Card],
        discard_pile: List[Card],
        deck_size: int,
        phase: GamePhase,
        is_my_turn: bool,
        opponent_hand_size: int,
    ):
        self._hand = list(hand)
        self._discard_pile = list(discard_pile)
        self._deck_size = deck_size
        self._phase = phase
        self._is_my_turn = is_my_turn
        self._opponent_hand_size = opponent_hand_size

    @property
    def hand(self) -> List[Card]:
        return list(self._hand)

    @property
    def discard_pile(self) -> List[Card]:
        return list(self._discard_pile)

    @property
    def top_of_discard(self) -> Optional[Card]:
        if self._discard_pile:
            return self._discard_pile[-1]
        return None

    @property
    def deck_size(self) -> int:
        return self._deck_size

    @property
    def phase(self) -> GamePhase:
        return self._phase

    @property
    def is_my_turn(self) -> bool:
        return self._is_my_turn

    @property
    def opponent_hand_size(self) -> int:
        return self._opponent_hand_size


class GameState:
    """Tracks the full state of a Gin Rummy game."""

    def __init__(self):
        self.deck: Optional[Deck] = None
        self.hands: List[List[Card]] = [[], []]
        self.discard_pile: List[Card] = []
        self.current_player: int = 0  # 0 or 1
        self.phase: GamePhase = GamePhase.DRAW
        self.dealer: int = 0
        self.winner: Optional[int] = None
        self.score: int = 0
        self.result_type: Optional[str] = None

    def setup(self, dealer: int = 0) -> None:
        """Initialize a new game: shuffle, deal, flip first discard."""
        self.deck = Deck()
        self.dealer = dealer
        self.hands = [[], []]
        self.discard_pile = []
        self.winner = None
        self.score = 0
        self.result_type = None

        # Deal 10 cards to each player, non-dealer first
        non_dealer = 1 - dealer
        self.hands[non_dealer] = self.deck.deal(10)
        self.hands[dealer] = self.deck.deal(10)

        # Flip the top card to start the discard pile
        self.discard_pile.append(self.deck.draw())

        # Non-dealer goes first
        self.current_player = non_dealer
        self.phase = GamePhase.DRAW

    def get_player_view(self, player: int) -> PlayerView:
        """Return an immutable view of the game for the given player."""
        opponent = 1 - player
        return PlayerView(
            hand=self.hands[player],
            discard_pile=self.discard_pile,
            deck_size=self.deck.remaining if self.deck else 0,
            phase=self.phase,
            is_my_turn=(self.current_player == player),
            opponent_hand_size=len(self.hands[opponent]),
        )
