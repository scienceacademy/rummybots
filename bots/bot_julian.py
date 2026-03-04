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
import random


class JulianBot(Bot):
    """A bot that uses simple heuristics.

    Always draws from deck, discards to minimize deadwood,
    and knocks at every opportunity.
    """

    def __init__(self):
        self.last_draw_from_discard = None

    @property
    def name(self) -> str:
        return "JulianBot"

    def draw_decision(self, view: PlayerView) -> str:
        top = view.top_of_discard

        if top is None:
            self.last_draw_from_discard = None
            return "deck"

        for card in view.hand:
            if card.rank == top.rank:
                self.last_draw_from_discard = top
                return "discard"

        self.last_draw_from_discard = None
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        discard = best_discard(view.hand)

        if self.last_draw_from_discard is not None and discard == self.last_draw_from_discard:
            for card in view.hand:
                if card != self.last_draw_from_discard:
                    return card

        return discard

    def knock_decision(self, view: PlayerView) -> bool:
        return True
