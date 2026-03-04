from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
    can_knock,
)


class AbbyBot(Bot):

    @property
    def name(self) -> str:
        return "AbbyBot"

    def __init__(self):
        self._drew_from_discard = None

    def draw_decision(self, view: PlayerView) -> str:
        if view.top_of_discard is None:
            return "deck"

        current = calculate_deadwood(view.hand)
        if_take = evaluate_discard_draw(view.hand, view.top_of_discard)

        if if_take < current:
            self._drew_from_discard = view.top_of_discard
            return "discard"

        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        discard = best_discard(view.hand)

        # Cannot discard the card just picked up from discard pile
        if discard == self._drew_from_discard:
            for card in view.hand:
                if card != self._drew_from_discard:
                    discard = card
                    break

        self._drew_from_discard = None
        return discard

    def knock_decision(self, view: PlayerView) -> bool:
        return can_knock(view.hand)
