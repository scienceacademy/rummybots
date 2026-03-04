
from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
    is_gin,
)


class Eerobot(Bot):

    @property
    def name(self) -> str:
        return "Eerobot"

    def draw_decision(self, view: PlayerView) -> str:

        current_deadwood = calculate_deadwood(view.hand)
        new_deadwood = evaluate_discard_draw(view.hand, view.top_of_discard)

        if new_deadwood < current_deadwood:
            return "discard"
        else:
            return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        return best_discard(view.hand)

    def knock_decision(self, view: PlayerView) -> bool:
        if is_gin(view.hand):
            return True
        return False


