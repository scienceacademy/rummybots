from engine.card import Card, Suit, Rank
from engine.game import PlayerView
from statistics import mean
from framework.bot_interface import Bot
from collections import defaultdict
from itertools import combinations
from math import log, exp, prod
from framework.utilities import (
    calculate_deadwood,
    get_best_melds,
)

class Opponent():
    def __init__(self):
        self.in_hand = set()
        self.out_of_hand = set()
        self.generate_deck()
        self.generate_melds()
    
    def generate_melds(self):
        sets = []
        for rank in Rank:
            cards_of_rank = [Card(rank, suit) for suit in Suit]
            # Generate all 3-card and 4-card combinations
            for combo in combinations(cards_of_rank, 3):
                sets.append(list(combo))
            for combo in combinations(cards_of_rank, 4):
                sets.append(list(combo))

        runs = []
        for suit in Suit:
            # Sort ranks numerically
            ranks_sorted = sorted(Rank, key=lambda r: r.value)
            # Generate all sequences of length 3 or more
            for i in range(len(ranks_sorted) - 2):
                for j in range(i + 3, len(ranks_sorted) + 1):
                    run = [Card(r, suit) for r in ranks_sorted[i:j]]
                    runs.append(run)
        self.melds = frozenset(tuple(m) for m in runs + sets)

        self.card2meld = {c : [] for c in self.all_cards}
        for m in self.melds:
            for c in m:
                self.card2meld[c].append(tuple(m))

    def generate_deck(self):
        self.all_cards = frozenset({Card(rank, suit) for suit in Suit for rank in Rank})

    def calculate_likelihoods(self, cards_in, cards_out):
        self.in_hand -= cards_out
        self.in_hand |= cards_in
        self.out_of_hand |= cards_out

        cards_p = defaultdict(int)
        N = len(self.all_cards - self.in_hand - self.out_of_hand)
        for c in self.all_cards:
            if c in self.out_of_hand: continue
            for m in self.card2meld[c]:
                n = len(self.card2meld[c])
                if any(c2 in self.out_of_hand for c2 in m):
                     continue
                cards_p[c] += 1 / (n * len(m)) if c in self.in_hand else 1 / (n * N * len(m))

        for c in self.out_of_hand:
            cards_p[c] = 0

        total = max(cards_p.values())
        if total != 0:
            for c in cards_p:
                cards_p[c] /= total

        return cards_p

    
class FinnBot(Bot):
    def __init__(self):
        self.generate_deck()
        self.generate_melds()

    def heuristic(self, hand):
        melds, unmelded = get_best_melds(hand)
        deadwood_mag = - calculate_deadwood(hand)
        turns_remaining = max(15 - self.turn, 2) 
        meld_mag = 2 * sum([len(m) for m in melds]) + 2 * self.count_almost_melds(unmelded)
        avg_turn_factor = (self.turn + max(15 - self.turn, 1)) / 2
        score = 2 * deadwood_mag * (self.turn ** 2) + meld_mag * turns_remaining # reward forming melds
        return score / avg_turn_factor

    def count_almost_melds(self, unmelded):
        count = 0

        # Count "almost sets" (pairs among unmelded)
        rank_counts = defaultdict(int)
        for c in unmelded:
            rank_counts[c.rank] += 1
        count += sum(1 for v in rank_counts.values() if v == 2)  # pairs

        # Count "almost runs" (consecutive in same suit among unmelded)
        suits = defaultdict(list)
        for c in unmelded:
            suits[c.suit].append(c.rank.value)
        for ranks in suits.values():
            ranks.sort()
            for i in range(len(ranks) - 1):
                if ranks[i+1] - ranks[i] == 1:
                    count += 1

        return count
        
    def on_game_start(self, player_index: int, view: PlayerView):
        self.deck = {Card(rank, suit) for suit in Suit for rank in Rank}
        self.discard = view.top_of_discard
        for card in view.hand:
            self.deck.remove(card)
        self.turn = 0
        self.opp = Opponent()
    
    @property
    def name(self) -> str:
        return "FinnBot"

    def generate_deck(self):
        self.all_cards = frozenset({Card(rank, suit) for suit in Suit for rank in Rank})

    def generate_melds(self):
        sets = []
        for rank in Rank:
            cards_of_rank = [Card(rank, suit) for suit in Suit]
            # Generate all 3-card and 4-card combinations
            for combo in combinations(cards_of_rank, 3):
                sets.append(list(combo))
            for combo in combinations(cards_of_rank, 4):
                sets.append(list(combo))

        runs = []
        for suit in Suit:
            # Sort ranks numerically
            ranks_sorted = sorted(Rank, key=lambda r: r.value)
            # Generate all sequences of length 3 or more
            for i in range(len(ranks_sorted) - 2):
                for j in range(i + 3, len(ranks_sorted) + 1):
                    run = [Card(r, suit) for r in ranks_sorted[i:j]]
                    runs.append(run)
        self.melds = frozenset(tuple(m) for m in runs + sets)

        self.card2meld = {c : [] for c in self.all_cards}
        for m in self.melds:
            for c in m:
                self.card2meld[c].append(tuple(m))

    def draw_decision(self, view: PlayerView) -> str:
        # update game model
        opp_in = set()
        opp_out = set()
        if self.discard not in view.discard_pile:
            opp_in.add(self.discard)
        else:
            opp_out.add(self.discard)
        if view.top_of_discard in self.deck:
            self.deck.remove(view.top_of_discard)
        opp_out.add(view.top_of_discard)
        
        self.opponent_likelihoods = self.opp.calculate_likelihoods(opp_in, opp_out)

        # Calculate EV for deck draw
        best = []

        for draw in self.deck:
            hand = view.hand + [draw]  # list of cards after drawing
            best_score = -float("inf")
            for discard in hand:
                hand_after_discard = [c for c in hand if c != discard]  # safe copy
                score = self.heuristic(hand_after_discard) - self.opponent_likelihoods[discard] * 9
                if score > best_score:
                    best_score = score
            best.append(best_score)

        deckEV = mean(best)

        # Calculate EV for discard draw
        hand = view.hand + [view.top_of_discard]
        discardEV = -float("inf")
        for discard in view.hand:
                hand_after_discard = [c for c in hand if c != discard]
                score = self.heuristic(hand_after_discard) - self.opponent_likelihoods[discard] * 9
                if score > discardEV:
                    discardEV = score
        
        # Use best option
        if deckEV > discardEV:
            self._drew_from_discard = None
            return "deck"
        self._drew_from_discard = view.top_of_discard
        return "discard"

    def discard_decision(self, view: PlayerView) -> Card:
        best = -float("inf")
        for discard in view.hand:
                hand_after_discard = [c for c in view.hand if c != discard] 
                score = self.heuristic(hand_after_discard) - self.opponent_likelihoods[discard] * 9
                if score > best and discard != self._drew_from_discard:
                    best = score
                    self.discard = discard
        self.turn += 1
        return self.discard
    
    def knock_decision(self, view: PlayerView) -> bool:
        deadwood = calculate_deadwood(view.hand)
        return True