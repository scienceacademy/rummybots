from engine.card import Card, Suit, Rank
from engine.game import PlayerView
from statistics import mean
from framework.bot_interface import Bot
from itertools import combinations
from math import log, exp
from framework.utilities import (
    calculate_deadwood,
    get_best_melds,
    get_melds,
    get_unmelded_cards,
)

#KNOCK_THRESHOLD = 4

class bot_kaiV2(Bot):
    def __init__(self):
        self._seen_discards = set()
        self._opponent_picks = set()
        self._last_discard_len = 0
        self._last_discard_list = []
        self._drew_from_discard = None
        self.deck = set()
        self._last_hand = set()

    def heuristic(self, hand):
        melds, unmelded = get_best_melds(hand)
        return -calculate_deadwood(hand) + 2 * len(melds)

    def on_game_start(self, player_index: int, view: PlayerView):
        self.deck = {Card(rank, suit) for suit in Suit for rank in Rank}
        for card in view.hand:
            self.deck.remove(card)
        self.discard = view.top_of_discard
        self.turn = 0
        self._seen_discards = set()
        self._opponent_picks = set()
        self._last_discard_len = len(view.discard_pile)
        self._last_discard_list = list(view.discard_pile)
        self._drew_from_discard = None
        self._last_hand = set(view.hand)

    def on_turn_end(self, view: PlayerView) -> None:
        current_len = len(view.discard_pile)
        if current_len < self._last_discard_len:
            missing = [c for c in self._last_discard_list if c not in view.discard_pile]
            if missing:
                for c in missing:
                    self._opponent_picks.add(c.rank)
            else:
                self._opponent_picks.add(None)
        for card in view.discard_pile:
            self._seen_discards.add(card)
            if card in self.deck:
                self.deck.discard(card)
        # update deck for any newly drawn cards
        new_cards = set(view.hand) - self._last_hand
        for card in new_cards:
            if card in self.deck:
                self.deck.discard(card)
        self._last_hand = set(view.hand)
        self._last_discard_len = current_len
        self._last_discard_list = list(view.discard_pile)

    @property
    def name(self) -> str:
        return "kaiV2bot"

    def draw_decision(self, view: PlayerView) -> str:
        if view.top_of_discard in self.deck:
            self.deck.remove(view.top_of_discard)

        best = []
        for draw in self.deck:
            hand = view.hand + [draw]
            best_score = -float("inf")
            for discard in hand:
                hand_after_discard = [c for c in hand if c != discard]
                score = self.heuristic(hand_after_discard)
                if score > best_score:
                    best_score = score
            best.append(best_score)

        deckEV = mean(best)

        hand = view.hand + [view.top_of_discard]
        discardEV = -float("inf")
        for discard in view.hand:
            hand_after_discard = [c for c in hand if c != discard]
            score = self.heuristic(hand_after_discard)
            if score > discardEV:
                discardEV = score

        if deckEV > discardEV:
            self._drew_from_discard = None
            return "deck"
        self._drew_from_discard = view.top_of_discard
        return "discard"

    def discard_decision(self, view: PlayerView) -> Card:
        best = -float("inf")
        for discard in view.hand:
                hand_after_discard = [c for c in view.hand if c != discard]
                base = self.heuristic(hand_after_discard)
                score = base + 0.5 * self.potential_scoring(hand_after_discard)
                if score > best and discard != self._drew_from_discard:
                    best = score
                    self.discard = discard
        self.turn += 1
        return self.discard

    def unmelded_pair(self, hand):
        unmelded = get_unmelded_cards(hand)
        rank_groups = {}
        for card in unmelded:
            rank_groups.setdefault(card.rank, []).append(card)
        pairs = set()
        for rank, cards in rank_groups.items():
            if len(cards) >= 2:
                pairs.update(cards)
        return pairs

    def unmelded_runs(self, hand):
        unmelded = get_unmelded_cards(hand)
        suit_groups = {}
        for card in unmelded:
            suit_groups.setdefault(card.suit, []).append(card)
        potential_runs = set()
        for suit, cards in suit_groups.items():
            cards_sorted = sorted(cards, key=lambda c: c.rank.value)
            for i in range(len(cards_sorted) - 1):
                if cards_sorted[i + 1].rank.value - cards_sorted[i].rank.value == 1:
                    potential_runs.add(cards_sorted[i])
                    potential_runs.add(cards_sorted[i + 1])
        return potential_runs

    def card_potential(self, hand, card):
        potential = 0
        if card in self.unmelded_pair(hand):
            seen_ranks = {c.rank for c in self._seen_discards}
            if card.rank in self._opponent_picks or card.rank in seen_ranks:
                potential += 1
            else:
                potential += 3
        if card in self.unmelded_runs(hand):
            potential += 1
        return potential

    def potential_scoring(self, hand):
        melds = get_best_melds(hand)
        score = len(melds) * 0.5  # bonus
        for card in get_unmelded_cards(hand):
            score += self.card_potential(hand, card)
        return score

    def knock_decision(self, view: PlayerView) -> bool:
        deadwood = calculate_deadwood(view.hand)
        return True