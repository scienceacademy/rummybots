"""Abstract base class for Gin Rummy bots.

Students should subclass Bot and implement the three required methods:
- draw_decision(): Choose to draw from the deck or discard pile
- discard_decision(): Choose which card to discard
- knock_decision(): Decide whether to knock

Example:
    from framework.bot_interface import Bot

    class MyBot(Bot):
        @property
        def name(self):
            return "My Bot"

        def draw_decision(self, view):
            return "deck"

        def discard_decision(self, view):
            return view.hand[0]

        def knock_decision(self, view):
            return True
"""

from abc import ABC, abstractmethod
from typing import List

from engine.card import Card
from engine.game import PlayerView


class Bot(ABC):
    """Abstract base class for Gin Rummy bots.

    Subclass this and implement draw_decision(), discard_decision(),
    and knock_decision() to create your bot.

    The game engine will call your methods in this order each turn:
    1. draw_decision() - choose where to draw from
    2. discard_decision() - choose which card to discard
    3. knock_decision() - decide whether to knock (only if eligible)

    You receive a PlayerView object with:
    - view.hand: your current cards
    - view.discard_pile: all discarded cards (full history)
    - view.top_of_discard: the top card of the discard pile
    - view.deck_size: number of cards remaining in the deck
    - view.opponent_hand_size: number of cards in opponent's hand
    - view.phase: current game phase
    """

    @property
    def name(self) -> str:
        """Return the display name of this bot.

        Override to give your bot a custom name.
        Defaults to the class name.
        """
        return self.__class__.__name__

    @abstractmethod
    def draw_decision(self, view: PlayerView) -> str:
        """Choose to draw from the deck or the discard pile.

        Args:
            view: Current game state. Check view.top_of_discard
                to see what card is available from the discard pile.

        Returns:
            "deck" to draw from the deck (unknown card), or
            "discard" to take the top card from the discard pile.
        """
        pass

    @abstractmethod
    def discard_decision(self, view: PlayerView) -> Card:
        """Choose which card to discard from your hand.

        After drawing, your hand has 11 cards. You must discard one
        to get back to 10 cards.

        Important: If you drew from the discard pile, you cannot
        immediately discard that same card.

        Args:
            view: Current game state. view.hand contains your
                11 cards (including the one you just drew).

        Returns:
            A Card object from your hand to discard.
        """
        pass

    @abstractmethod
    def knock_decision(self, view: PlayerView) -> bool:
        """Decide whether to knock.

        This is only called when your deadwood is 10 or less,
        meaning you are eligible to knock.

        If your deadwood is 0, knocking results in "gin" for a
        bonus of 25 points plus the opponent's deadwood.

        Args:
            view: Current game state (after your discard).

        Returns:
            True to knock and end the hand, False to continue.
        """
        pass

    def on_game_start(self, player_index: int, view: PlayerView) -> None:
        """Called when a new game begins (optional).

        Override this to initialize any tracking state your bot needs,
        such as tracking which cards have been discarded.

        Args:
            player_index: Your player number (0 or 1).
            view: Initial game state view.
        """
        pass

    def on_turn_end(self, view: PlayerView) -> None:
        """Called after each turn completes (optional).

        Override this to update any tracking state, such as
        monitoring what the opponent discarded.

        Args:
            view: Game state after the turn.
        """
        pass
