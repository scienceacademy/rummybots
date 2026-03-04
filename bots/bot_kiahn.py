from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
    is_gin,
    can_knock,
    deadwood_after_discard,
)


class kiahncode(Bot):

    def __init__(self):
        self.last = None

    @property
    def name(self) -> str:
        return "kiahncode"

    def draw_decision(self, view: PlayerView) -> str:
        self.last = None

        if view.top_of_discard == None:
            return "deck"

        dw_now = calculate_deadwood(view.hand)
        dw_if = evaluate_discard_draw(view.hand, view.top_of_discard)

        if dw_if < dw_now:
            self.last = view.top_of_discard
            return "discard"
        else:
            if view.deck_size <= 8:
                if dw_if <= dw_now:
                    self.last = view.top_of_discard
                    return "discard"
            return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        hand = []
        for c in view.hand:
            hand.append(c)

        if self.last != None:
            for i in range(len(hand)):
                if hand[i] == self.last:
                    hand.pop(i)
                    break

        lowest = 9999
        card_to_throw = None

        for i in range(len(hand)):
            c = hand[i]
            new_dw = deadwood_after_discard(view.hand, c)

            if new_dw < lowest:
                lowest = new_dw
                card_to_throw = c

        if card_to_throw == None:
            return best_discard(view.hand)

        return card_to_throw

    def knock_decision(self, view: PlayerView) -> bool:
        dw = calculate_deadwood(view.hand)

        if is_gin(view.hand):
            return True

        if can_knock(view.hand) == False:
            return False

        if dw <= 4:
            return True
        else:
            if view.deck_size <= 6:
                if dw <= 7:
                    return True

        return False