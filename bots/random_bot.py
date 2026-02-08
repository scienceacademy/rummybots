"""RandomBot — makes completely random legal moves.

This bot serves as a baseline. Any reasonable strategy should
beat RandomBot consistently.
"""

import random

from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot


class RandomBot(Bot):
    """A bot that makes random legal moves.

    - Randomly draws from deck or discard pile
    - Randomly discards a card from its hand
    - Randomly decides whether to knock
    """

    def __init__(self):
        self._drew_from_discard = None

    @property
    def name(self) -> str:
        return "RandomBot"

    def draw_decision(self, view: PlayerView) -> str:
        if view.top_of_discard is not None:
            choice = random.choice(["deck", "discard"])
            if choice == "discard":
                self._drew_from_discard = view.top_of_discard
            else:
                self._drew_from_discard = None
            return choice
        self._drew_from_discard = None
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        choices = view.hand
        if self._drew_from_discard is not None:
            choices = [c for c in choices if c != self._drew_from_discard]
        return random.choice(choices)

    def knock_decision(self, view: PlayerView) -> bool:
        return random.choice([True, False])
