from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    best_discard,
    evaluate_discard_draw,
    can_knock
)

class TaraBot(Bot):

    def __init__(self):
        self._drew_from_discard = None

    @property
    def name(self):
        return "TaraBot"

    def on_game_start(self, player_index, view):
        # reset each game
        self._drew_from_discard = None

    def draw_decision(self, view):
        # if there is no discard card, must draw from deck
        if view.top_of_discard is None:
            return "deck"

        current_deadwood = calculate_deadwood(view.hand)
        new_deadwood = evaluate_discard_draw(view.hand, view.top_of_discard)

        # take discard only if it improves hand
        if new_deadwood < current_deadwood:
            self._drew_from_discard = view.top_of_discard
            return "discard"

        return "deck"

    def discard_decision(self, view):
        hand = view.hand

        # cannot discard the same card you just picked up
        if self._drew_from_discard is not None:               #GOT HELP FROM AI HERE!
            possible_cards = [c for c in hand if c != self._drew_from_discard]
        else:
            possible_cards = hand

        discard_card = best_discard(possible_cards)

        # AFTER YOU DISCARD, RESET
        self._drew_from_discard = None    #GOT HELP HERE FROM CLASSMATE

        return discard_card

    def knock_decision(self, view):
        # only knock if allowed
        if not can_knock(view.hand):
            return False

        deadwood = calculate_deadwood(view.hand)

        if deadwood <= 5:
            return True

        return False