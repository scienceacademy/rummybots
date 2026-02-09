"""AdvancedBot — a strong Gin Rummy bot with multi-factor strategy.

Key advantages over simpler bots:
- Aggressive knocking: knocks whenever eligible, capturing games before
  opponents can improve (the single biggest edge)
- Dead-card detection: identifies provably safe discards via card counting
- Probability-based evaluation: counts live outs for meld completion
- Defensive discarding: tracks opponent picks, avoids feeding them cards
"""

from typing import List, Optional, Set

from engine.card import Card, Rank, Suit
from engine.game import PlayerView
from engine.rules import find_best_melds
from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    deadwood_after_discard,
    evaluate_discard_draw,
)

ALL_CARDS = frozenset(
    Card(rank, suit) for suit in Suit for rank in Rank
)


class AdvancedBot(Bot):

    @property
    def name(self) -> str:
        return "AdvancedBot"

    def __init__(self):
        self._drew_from_discard: Optional[Card] = None
        self._seen_cards: Set[Card] = set()
        self._opponent_picks: List[Card] = []
        self._prev_discard_top: Optional[Card] = None
        self._prev_discard_len: int = 0

    def on_game_start(self, player_index: int, view: PlayerView) -> None:
        self._drew_from_discard = None
        self._seen_cards = set(view.hand)
        self._seen_cards.update(view.discard_pile)
        self._opponent_picks = []
        self._prev_discard_top = view.top_of_discard
        self._prev_discard_len = len(view.discard_pile)

    def on_turn_end(self, view: PlayerView) -> None:
        self._seen_cards.update(view.hand)
        self._seen_cards.update(view.discard_pile)

        if not view.is_my_turn:
            # Opponent's turn just ended.
            # If pile didn't grow, opponent drew from discard.
            if len(view.discard_pile) <= self._prev_discard_len:
                if self._prev_discard_top is not None:
                    self._opponent_picks.append(self._prev_discard_top)

        self._prev_discard_top = view.top_of_discard
        self._prev_discard_len = len(view.discard_pile)

    # -- Helpers --

    def _is_safe_discard(self, card: Card, hand: List[Card]) -> bool:
        """Check if opponent CANNOT use this card to complete any meld.

        A card is safe if:
        - Set-safe: 2+ of the other 3 same-rank cards are accounted for
          (in our hand or seen), so opponent can't form a set of 3.
        - Run-safe: for every possible 3-card run containing this card,
          at least one other required card is accounted for.
        """
        accounted = self._seen_cards | set(hand)

        other_same_rank = sum(
            1 for c in accounted
            if c.rank == card.rank and c != card
        )
        set_safe = other_same_rank >= 2

        cv = card.rank.value
        run_safe = True
        for start in (cv - 2, cv - 1, cv):
            vals = [start, start + 1, start + 2]
            if vals[0] < 1 or vals[2] > 13:
                continue
            other_vals = [v for v in vals if v != cv]
            opponent_can_have_all = True
            for v in other_vals:
                if Card(Rank(v), card.suit) in accounted:
                    opponent_can_have_all = False
                    break
            if opponent_can_have_all:
                run_safe = False
                break

        return set_safe and run_safe

    def _count_outs(self, card: Card, hand: List[Card]) -> int:
        """Count unseen cards that would complete a meld involving *card*."""
        unseen = ALL_CARDS - self._seen_cards - set(hand)
        others = [c for c in hand if c != card]
        outs: Set[Card] = set()

        # Set outs: have a pair, need a third
        same_rank = sum(1 for c in others if c.rank == card.rank)
        if same_rank == 1:
            for c in unseen:
                if c.rank == card.rank:
                    outs.add(c)

        # Run outs
        cv = card.rank.value
        suit_vals = {c.rank.value for c in others if c.suit == card.suit}

        has_m1 = (cv - 1) in suit_vals
        has_p1 = (cv + 1) in suit_vals
        has_m2 = (cv - 2) in suit_vals
        has_p2 = (cv + 2) in suit_vals

        if has_m1:
            for v in (cv - 2, cv + 1):
                if 1 <= v <= 13:
                    c = Card(Rank(v), card.suit)
                    if c in unseen:
                        outs.add(c)

        if has_p1:
            for v in (cv - 1, cv + 2):
                if 1 <= v <= 13:
                    c = Card(Rank(v), card.suit)
                    if c in unseen:
                        outs.add(c)

        if has_m2 and not has_m1:
            v = cv - 1
            if 1 <= v <= 13:
                c = Card(Rank(v), card.suit)
                if c in unseen:
                    outs.add(c)

        if has_p2 and not has_p1:
            v = cv + 1
            if 1 <= v <= 13:
                c = Card(Rank(v), card.suit)
                if c in unseen:
                    outs.add(c)

        return len(outs)

    def _safety_score(self, card: Card) -> float:
        """How safe is discarding this card? Higher = safer."""
        safety = 0.0

        for pick in self._opponent_picks:
            if pick.rank == card.rank:
                safety -= 5
            if (pick.suit == card.suit
                    and abs(pick.rank.value - card.rank.value) <= 2):
                safety -= 3

        seen_same_rank = sum(
            1 for c in self._seen_cards
            if c.rank == card.rank and c != card
        )
        safety += seen_same_rank * 1.5

        return safety

    # --- Draw ---

    def draw_decision(self, view: PlayerView) -> str:
        if view.top_of_discard is None:
            self._drew_from_discard = None
            return "deck"

        discard_card = view.top_of_discard
        hand = view.hand
        current_dw = calculate_deadwood(hand)

        # Take if significant deadwood improvement (> 2 points)
        if_take = evaluate_discard_draw(hand, discard_card)
        if if_take < current_dw - 2:
            self._drew_from_discard = discard_card
            return "discard"

        self._drew_from_discard = None
        return "deck"

    # --- Discard ---

    def discard_decision(self, view: PlayerView) -> Card:
        hand = view.hand
        excluded = self._drew_from_discard
        self._drew_from_discard = None

        melds, _ = find_best_melds(hand)
        melded_cards: Set[Card] = set()
        for m in melds:
            melded_cards.update(m)

        candidates = [c for c in hand if c != excluded]
        if not candidates:
            candidates = list(hand)

        current_dw = calculate_deadwood(hand)
        best_card = candidates[0]
        best_score = float("-inf")

        for card in candidates:
            score = 0.0

            # Primary: deadwood reduction (higher = more want to discard)
            after_dw = deadwood_after_discard(hand, card)
            score += (current_dw - after_dw) * 10

            if card in melded_cards:
                # Never break melds
                score -= 50
            else:
                # Keep cards with meld-completion potential
                outs = self._count_outs(card, hand)
                score -= outs * 8

            # Bonus for provably safe discards (can't help opponent)
            if card not in melded_cards and self._is_safe_discard(card, hand):
                score += 20

            # Avoid feeding opponent cards they've been picking up
            score += self._safety_score(card) * 4

            # Tiebreaker: prefer discarding higher deadwood
            score += card.deadwood_value * 0.3

            if score > best_score:
                best_score = score
                best_card = card

        return best_card

    # --- Knock ---

    def knock_decision(self, view: PlayerView) -> bool:
        # Always knock when eligible. Aggressive knocking captures games
        # before the opponent can improve their hand. The undercut risk
        # is outweighed by winning games that conservative bots would
        # pass on.
        return True
