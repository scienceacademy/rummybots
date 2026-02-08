"""Game state management and engine for Gin Rummy."""

import os
import random
import signal
from enum import Enum, auto
from typing import List, Optional

from engine.card import Card, Deck
from engine import rules

# Timeout in seconds for each bot decision call
BOT_TIMEOUT_SECONDS = 5

# Whether signal-based timeouts are available (Unix only)
_HAS_SIGALRM = hasattr(signal, "SIGALRM") and os.name != "nt"


class BotTimeoutError(Exception):
    """Raised when a bot exceeds the allowed time for a decision."""
    pass


def _call_bot_method(method, view, timeout=BOT_TIMEOUT_SECONDS):
    """Call a bot method with timeout and frame isolation.

    This is a standalone function (not a GameEngine method) so that
    the engine's ``self`` is NOT in the immediate caller's frame.
    This prevents bots from using inspect.currentframe().f_back.f_locals
    to access game internals directly.

    Uses signal.alarm on Unix for zero-overhead timeout enforcement.
    """
    if _HAS_SIGALRM:
        def _timeout_handler(signum, frame):
            raise BotTimeoutError(
                f"Bot method {method.__name__} exceeded {timeout}s time limit"
            )
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)

    try:
        result = method(view)
    finally:
        if _HAS_SIGALRM:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    return result


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

    def setup(self, dealer: int = 0, rng: random.Random = None) -> None:
        """Initialize a new game: shuffle, deal, flip first discard."""
        self.deck = Deck(rng=rng)
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


class DrawChoice(Enum):
    DECK = "deck"
    DISCARD = "discard"


class InvalidMoveError(Exception):
    """Raised when a bot attempts an illegal move."""
    pass


class GameResult:
    """Results from a completed game."""

    def __init__(
        self,
        winner: Optional[int],
        score: int,
        result_type: str,
        knocker: Optional[int] = None,
    ):
        self.winner = winner
        self.score = score
        self.result_type = result_type
        self.knocker = knocker

    def __repr__(self) -> str:
        return (
            f"GameResult(winner={self.winner}, score={self.score}, "
            f"result_type='{self.result_type}', knocker={self.knocker})"
        )


class GameEngine:
    """Manages the flow and rules of a single Gin Rummy game.

    Handles game initialization, turn management, move validation,
    and scoring. Interfaces with two bot instances that implement
    draw_decision(), discard_decision(), and knock_decision().
    """

    def __init__(self):
        self.state = GameState()
        self._drawn_from_discard: Optional[Card] = None

    def play_game(self, bot0, bot1, dealer: int = 0, rng: random.Random = None) -> GameResult:
        """Run a complete game between two bots.

        Args:
            bot0: First bot instance (player 0).
            bot1: Second bot instance (player 1).
            dealer: Which player deals (0 or 1).
            rng: Dedicated Random instance for shuffling. If None, a new one is created.

        Returns:
            GameResult with winner, score, and result type.

        Raises:
            InvalidMoveError: If a bot makes an illegal move.
        """
        if rng is None:
            rng = random.Random(random.getrandbits(128))
        self.state.setup(dealer, rng=rng)
        self._drawn_from_discard = None
        bots = [bot0, bot1]

        # Notify bots of game start
        for i, bot in enumerate(bots):
            if hasattr(bot, "on_game_start"):
                bot.on_game_start(i, self.state.get_player_view(i))

        while self.state.phase != GamePhase.END:
            player = self.state.current_player
            bot = bots[player]

            # Draw phase — call via trampoline for frame isolation + timeout
            view = self.state.get_player_view(player)
            draw_choice = _call_bot_method(bot.draw_decision, view)
            if not isinstance(draw_choice, (str, DrawChoice)):
                raise InvalidMoveError(
                    f"draw_decision() must return str or DrawChoice, "
                    f"got {type(draw_choice).__name__}"
                )
            self._execute_draw(player, draw_choice)

            # Discard phase
            view = self.state.get_player_view(player)
            discard_card = _call_bot_method(bot.discard_decision, view)
            if not isinstance(discard_card, Card):
                raise InvalidMoveError(
                    f"discard_decision() must return a Card, "
                    f"got {type(discard_card).__name__}"
                )
            self._execute_discard(player, discard_card)

            # Check for deck exhaustion
            if self.state.deck.remaining < 2:
                self.state.phase = GamePhase.END
                return GameResult(
                    winner=None, score=0, result_type="draw"
                )

            # Knock phase (only if eligible)
            if rules.can_knock(self.state.hands[player]):
                self.state.phase = GamePhase.KNOCK
                view = self.state.get_player_view(player)
                knock = _call_bot_method(bot.knock_decision, view)
                if not isinstance(knock, bool):
                    raise InvalidMoveError(
                        f"knock_decision() must return bool, "
                        f"got {type(knock).__name__}"
                    )
                if knock:
                    return self._execute_knock(player)

            # Notify bots of turn end
            for i, b in enumerate(bots):
                if hasattr(b, "on_turn_end"):
                    b.on_turn_end(self.state.get_player_view(i))

            # Switch to other player
            self.state.current_player = 1 - player
            self.state.phase = GamePhase.DRAW

        return GameResult(winner=None, score=0, result_type="draw")

    def _execute_draw(self, player: int, choice) -> None:
        """Execute and validate a draw action."""
        if self.state.phase != GamePhase.DRAW:
            raise InvalidMoveError("Not in draw phase")
        if self.state.current_player != player:
            raise InvalidMoveError("Not your turn")

        # Accept string or DrawChoice enum
        if isinstance(choice, str):
            try:
                choice = DrawChoice(choice.lower())
            except ValueError:
                raise InvalidMoveError(
                    f"Invalid draw choice: '{choice}'. "
                    "Use 'deck' or 'discard'."
                )
        elif not isinstance(choice, DrawChoice):
            raise InvalidMoveError(
                f"Invalid draw choice type: {type(choice).__name__}"
            )

        if choice == DrawChoice.DECK:
            if self.state.deck.is_empty():
                raise InvalidMoveError("Cannot draw from empty deck")
            card = self.state.deck.draw()
            self.state.hands[player].append(card)
            self._drawn_from_discard = None

        elif choice == DrawChoice.DISCARD:
            if not self.state.discard_pile:
                raise InvalidMoveError("Cannot draw from empty discard pile")
            card = self.state.discard_pile.pop()
            self.state.hands[player].append(card)
            self._drawn_from_discard = card

        self.state.phase = GamePhase.DISCARD

    def _execute_discard(self, player: int, card: Card) -> None:
        """Execute and validate a discard action."""
        if self.state.phase != GamePhase.DISCARD:
            raise InvalidMoveError("Not in discard phase")
        if self.state.current_player != player:
            raise InvalidMoveError("Not your turn")
        if len(self.state.hands[player]) != 11:
            raise InvalidMoveError(
                f"Must have 11 cards to discard, "
                f"have {len(self.state.hands[player])}"
            )
        if card not in self.state.hands[player]:
            raise InvalidMoveError(f"Card {card} is not in your hand")
        if (
            self._drawn_from_discard is not None
            and card == self._drawn_from_discard
        ):
            raise InvalidMoveError(
                "Cannot discard the card just drawn from the discard pile"
            )

        self.state.hands[player].remove(card)
        self.state.discard_pile.append(card)
        self.state.phase = GamePhase.KNOCK

    def _execute_knock(self, player: int) -> GameResult:
        """Execute a knock and score the hand."""
        hand = self.state.hands[player]
        opponent = 1 - player
        opponent_hand = self.state.hands[opponent]

        gin = rules.is_gin(hand)
        points, result_type = rules.score_with_layoffs(
            hand, opponent_hand, is_gin=gin
        )

        self.state.phase = GamePhase.END

        if result_type == "undercut":
            winner = opponent
            score = abs(points)
        else:
            winner = player
            score = points

        self.state.winner = winner
        self.state.score = score
        self.state.result_type = result_type

        return GameResult(
            winner=winner,
            score=score,
            result_type=result_type,
            knocker=player,
        )
