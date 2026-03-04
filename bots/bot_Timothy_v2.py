from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
)

class bot_Timothy_v2(Bot):
    def __init__(self):
        self._drew_from_discard = None

    @property
    def name(self) -> str:
        return "bot_Timothy_v2"

    def draw_decision(self, view: PlayerView) -> str:
        hand = view.hand
        hand_after_draw = view.hand + [view.top_of_discard]
        if calculate_deadwood(hand_after_draw) < calculate_deadwood(hand):
            self._drew_from_discard = view.top_of_discard
            return "discard"
        else:
            return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        hand = view.hand
        if self._drew_from_discard != None:
            hand = [c for c in view.hand if c != self._drew_from_discard]
        return best_discard(hand)

    def knock_decision(self, view: PlayerView) -> bool:
        return True