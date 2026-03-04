from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    evaluate_discard_draw,
    deadwood_after_discard,
    count_meld_outs,
    count_near_melds,
    is_gin,
    can_knock,
)


class CarynBot(Bot):

    def __init__(self):
        self._drew_from_discard = None

    @property
    def name(self) -> str:
        return "caryn_bot"

    def draw_decision(self, view: PlayerView) -> str:
        self._drew_from_discard = None

        if view.top_of_discard is None:
            return "deck"

        current_dw = calculate_deadwood(view.hand)
        dw_if_take = evaluate_discard_draw(view.hand, view.top_of_discard)

        if dw_if_take < current_dw:
            self._drew_from_discard = view.top_of_discard
            return "discard"

        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        hand = list(view.hand)

        if self._drew_from_discard in hand:
            hand.remove(self._drew_from_discard)

        seen = set(view.hand + view.discard_pile)

        best_card = None
        best_score = float("-inf")

        for card in hand:
            new_dw = deadwood_after_discard(view.hand, card)
            outs = count_meld_outs(card, view.hand, seen)

            score = (-new_dw * 3) - (outs * 2) + card.deadwood_value

            if score > best_score:
                best_score = score
                best_card = card

        return best_card

    def knock_decision(self, view: PlayerView) -> bool:
        deadwood = calculate_deadwood(view.hand)

        if is_gin(view.hand):
            return True

        if not can_knock(view.hand):
            return False

        if deadwood <= 3:
            return True

        if view.deck_size <= 8 and deadwood <= 6:
            return True

        if count_near_melds(view.hand) <= 1 and deadwood <= 6:
            return True

        return False