"""BasicBot — simple heuristic strategy.

This bot uses straightforward rules:
- Always draws from the deck (safe, no information given)
- Discards the card that minimizes deadwood
- Knocks whenever eligible (deadwood <= 10)

A good starting point for students to understand and improve upon.
"""

from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import best_discard


class BasicBot(Bot):
    """A bot that uses simple heuristics.

    Always draws from deck, discards to minimize deadwood,
    and knocks at every opportunity.
    """

    @property
    def name(self) -> str:
        return "BasicBot"

    def draw_decision(self, view: PlayerView) -> str:
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        return best_discard(view.hand)

    def knock_decision(self, view: PlayerView) -> bool:
        return True
