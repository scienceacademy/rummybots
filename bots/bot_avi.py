from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
    find_best_melds,
)


class RummyBot(Bot):
    """Your custom Gin Rummy bot!

    Implement your strategy by modifying the three methods below.
    You can also override on_game_start() and on_turn_end() to
    track game state between turns.
    """

    def __init__(self):
        self.decision = ""
        self.discarded = []
        self.nonocard = Card(rank=None, suit=None)
        self.turn = 0


    @property
    def name(self) -> str:
        return "Avi's_Counterstrike"

    def draw_decision(self, view: PlayerView) -> str:
        self.turn += 1

        count = 0
        for card in view.hand:
            if card.rank == view.top_of_discard.rank:
                count += 1
        if count > 1:
            self.decision = "discard"
            self.nonocard = view.top_of_discard
        else:
            behind = False
            for card in view.hand:
                if (card.rank.value == view.top_of_discard.rank.value - 1) and card.suit == view.top_of_discard.suit:
                    behind = True
                elif (card.rank.value == view.top_of_discard.rank.value + 1) and card.suit == view.top_of_discard.suit:
                    behind = False

            for card in view.hand:
                # Fix: update CardRank for each card
                if (card.rank.value == view.top_of_discard.rank.value - 2) and behind == True and card.suit == view.top_of_discard.suit:
                    self.decision = "discard"
                    self.nonocard = view.top_of_discard
                elif ((card.rank.value == view.top_of_discard.rank.value - 1) and behind == False) and card.suit == view.top_of_discard.suit:
                    self.decision = "discard"
                    self.nonocard = view.top_of_discard
                elif ((card.rank.value == view.top_of_discard.rank.value + 1) and behind == True) and card.suit == view.top_of_discard.suit:
                    self.decision = "discard"
                    self.nonocard = view.top_of_discard
                elif ((card.rank.value == view.top_of_discard.rank.value + 2) and behind == False) and card.suit == view.top_of_discard.suit:
                    self.decision = "discard"
                    self.nonocard = view.top_of_discard
                else:
                    self.decision = "deck"

        return self.decision


    def discard_decision(self, view: PlayerView) -> Card:
        meld_sets, deadwood = find_best_melds(view.hand)
        if self.decision == "discard" and self.nonocard in deadwood:
            deadwood.remove(self.nonocard)
        return best_discard(deadwood)

    def knock_decision(self, view: PlayerView) -> bool:
        return True if calculate_deadwood(view.hand) <= 8 else False