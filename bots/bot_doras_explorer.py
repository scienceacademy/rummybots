from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    Meld, Suit, Rank,
    get_melds,               # All possible melds in a hand
    get_best_melds,          # Optimal melds + leftover cards
)
from copy import deepcopy

ALL_CARDS = list(Card(rank, suit) for suit in Suit for rank in Rank)
ALL_MELDS = get_melds(ALL_CARDS)

def print_hand(hand: list[Card], values: list[float]):
    handstring = ""
    for card in hand:
        handstring += str(card)
        handstring += " " * (4 - len(handstring) % 4)
    valuestring = ""
    for value in values:
        valuestring += str(int(round(value, 2) * 100)) + "  "
    print(handstring)
    print(valuestring)

def unlist(list):
    return [n for sublist in list for n in sublist]

def calc_possibles(hand: list[Card]) -> list[Meld]:
    handset = set(hand)
    possibles: list[Meld] = []
    for meld in ALL_MELDS:
        if len(meld) > 4:
            continue
        if len(set(meld) & handset) == 2:
            # print(f"{set(meld) & handset} matched {meld}")
            possibles.append(meld)
    return possibles

def calc_enemelds(rejected: list[Card]) -> list[Meld]:
    enemy_cards = deepcopy(ALL_CARDS)
    for card in rejected:
        if card in enemy_cards:
            enemy_cards.remove(card)
    return calc_possibles(enemy_cards)

def value(card: Card, melds: list[Meld], bests: list[Meld], possibles: list[Meld], enemelds: list[Meld]) -> float:
    if card in unlist(bests):
        return 1. - card.deadwood_value / 100
    elif card in unlist(melds):
        return 0.9 - card.deadwood_value / 100
    else:
        value = 0
        unlisted_possibles = unlist(possibles)
        if card in unlisted_possibles:
            value = 0.2 + 0.1 * unlisted_possibles.count(card) - card.deadwood_value / 200
        return min(value, 0.79)
    return 0.

def value_hand(hand: list[Card], enemelds: list[Meld]) -> list[float]:
    melds = get_melds(hand)
    bests = get_best_melds(hand)[0]
    values: list[float] = [0.] * len(hand)
    possibles = calc_possibles(hand)

    for (i, card) in enumerate(hand):
        values[i] = value(card, melds, bests, possibles, enemelds)
    return values

class DoraBot(Bot):
    values: list[float] = []
    rejected: list[Card] = []
    player_index: int = 0
    enemelds: list[Meld] = []
    decision = ""

    def on_game_start(self, player_index: int, view: PlayerView) -> None:
        self.player_index = player_index
        if player_index == 1 and view.top_of_discard is not None:
            self.rejected.append(view.top_of_discard)


    @property
    def name(self) -> str:
        return "Dora's Explorer"

    def draw_decision(self, view: PlayerView) -> str:
        # print("")
        if view.top_of_discard is None:
            return "deck"
        if len(self.rejected) != 0:
            if self.rejected[-1] != view.top_of_discard:
                self.rejected.append(view.top_of_discard)
                self.enemelds = calc_enemelds(self.rejected)
        hand = view.hand
        hand.append(view.top_of_discard)
        self.values = value_hand(hand, self.enemelds)
        # print_hand(hand, self.values)
        discard_value = self.values[-1]
        threshold = 0.35
        self.decision = "discard" if discard_value > threshold else "deck"
        # print(f"drawing from {self.decision}")
        return self.decision

    def discard_decision(self, view: PlayerView) -> Card:
        min = 1.
        mindex = 0
        for i in range(11 if self.decision == "deck" else 10):
            if self.values[i] < min:
                min = self.values[i]
                mindex = i
        return view.hand[mindex]

    def knock_decision(self, view: PlayerView) -> bool:
        return True

