from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    is_gin,
    get_best_melds,
)




class TristanBot(Bot):


    def __init__(self):
        self._drew_from_discard = None
        self._turn_count = 0


    @property
    def name(self):
        return "TristanBot"


    def on_game_start(self, player_index, view):
        self._drew_from_discard = None
        self._turn_count = 0


    def on_turn_end(self, view):
        self._turn_count += 1


    # -------------------
    # Helper
    # -------------------
    def rank_value(self, card):
        return card.rank.value


    # -------------------
    # DRAW DECISION
    # -------------------
    def draw_decision(self, view):
        self._drew_from_discard = None


        if view.top_of_discard is None:
            return "deck"


        top = view.top_of_discard
        top_rank = self.rank_value(top)


        for card in view.hand:
            card_rank = self.rank_value(card)


            # Pair
            if card_rank == top_rank:
                self._drew_from_discard = top
                return "discard"


            # Sequential run
            if (
                card.suit == top.suit and
                abs(card_rank - top_rank) == 1
            ):
                self._drew_from_discard = top
                return "discard"


        return "deck"


    # -------------------
    # DISCARD DECISION
    # -------------------
    def discard_decision(self, view):
        hand = list(view.hand)


        if self._drew_from_discard is not None:
            hand = [c for c in hand if c != self._drew_from_discard]


        melds, _ = get_best_melds(hand)


        protected_cards = set()
        for meld in melds:
            if len(meld) >= 3:
                protected_cards.update(meld)


        def deadwood_value(card):
            return min(self.rank_value(card), 10)


        def run_strength(card):
            lower = False
            upper = False
            r = self.rank_value(card)


            for other in hand:
                if other == card:
                    continue
                if other.suit == card.suit:
                    other_r = self.rank_value(other)
                    if other_r == r - 1:
                        lower = True
                    if other_r == r + 1:
                        upper = True


            if lower and upper:
                return 2
            if lower or upper:
                return 1
            return 0


        def has_pair(card):
            r = self.rank_value(card)
            for other in hand:
                if other != card and self.rank_value(other) == r:
                    return True
            return False


        candidates = [c for c in hand if c not in protected_cards]
        if not candidates:
            candidates = hand


        def discard_score(card):
            score = 0
            score += deadwood_value(card) * 3


            if has_pair(card):
                score -= 15


            score -= run_strength(card) * 10


            return score


        return max(candidates, key=discard_score)


    # -------------------
    # KNOCK DECISION
    # -------------------
    def knock_decision(self, view):
        deadwood = calculate_deadwood(view.hand)


        if is_gin(view.hand):
            return True


        # Turn-based knock thresholds
        if self._turn_count <= 4:
            return deadwood < 9
        elif self._turn_count <= 8:
            return deadwood < 6
        else:
            return deadwood < 3
