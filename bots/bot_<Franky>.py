from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
)

class Franky_bot(Bot):

    def __init__(self):
        super().__init__()

        self._drew_from_discard = None

    @property
    def name(self) -> str:
        return "Franky_bot"

    def on_game_start(self, player_index, view):

        self._drew_from_discard = None

    def draw_decision(self, view: PlayerView) -> str:

        if view.top_of_discard is not None:
            current_dw = calculate_deadwood(view.hand)

            if_take_dw = evaluate_discard_draw(view.hand, view.top_of_discard)

            if if_take_dw < current_dw:
                self._drew_from_discard = view.top_of_discard
                return "discard"

        self._drew_from_discard = None
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:

        choices = view.hand

        if self._drew_from_discard is not None:
            choices = [c for c in choices if c != self._drew_from_discard]

        return best_discard(choices)

    def knock_decision(self, view: PlayerView) -> bool:

        return calculate_deadwood(view.hand) <= 4
