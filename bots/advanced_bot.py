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
    count_meld_outs,
    deadwood_after_discard,
    evaluate_discard_draw,
    is_provably_safe_discard,
    score_discard_safety,
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

    # -- Helper methods moved to framework.utilities --
    # is_provably_safe_discard(), count_meld_outs(), score_discard_safety()

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
                outs = count_meld_outs(card, hand, self._seen_cards)
                score -= outs * 8

            # Bonus for provably safe discards (can't help opponent)
            if card not in melded_cards and is_provably_safe_discard(card, self._seen_cards):
                score += 20

            # Avoid feeding opponent cards they've been picking up
            score += score_discard_safety(card, self._opponent_picks, self._seen_cards) * 4

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
