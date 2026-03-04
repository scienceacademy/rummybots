"""OptimalBot — an advanced Gin Rummy bot using card counting and opponent modeling.

Strategies:
- Card counting: tracks all seen cards to inform safety analysis
- Opponent modeling: detects when opponent draws from discard to avoid feeding them
- Smart draw decisions: takes from discard when it improves deadwood
- Deadwood-optimal discards with safety tiebreaking
- Aggressive knocking: always knocks when eligible (empirically optimal)
"""

from typing import List, Optional, Set

from engine.card import Card, Rank, Suit
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    deadwood_after_discard,
    get_best_melds,
    is_provably_safe_discard,
)

ALL_CARDS = frozenset(
    Card(rank, suit) for suit in Suit for rank in Rank
)


class CBBot(Bot):

    @property
    def name(self) -> str:
        return "CBBot"

    def __init__(self):
        self._seen_cards: Set[Card] = set()
        self._opponent_pickups: List[Card] = []
        self._prev_discard_top: Optional[Card] = None
        self._prev_discard_len: int = 0
        self._drew_from_discard: Optional[Card] = None

    def on_game_start(self, player_index: int, view: PlayerView) -> None:
        self._seen_cards = set(view.hand) | set(view.discard_pile)
        self._opponent_pickups = []
        self._prev_discard_top = view.top_of_discard
        self._prev_discard_len = len(view.discard_pile)
        self._drew_from_discard = None

    def on_turn_end(self, view: PlayerView) -> None:
        # Detect opponent pickup: if discard pile shrank since last snapshot,
        # the opponent took from the discard pile
        current_len = len(view.discard_pile)
        if current_len < self._prev_discard_len:
            self._opponent_pickups.append(self._prev_discard_top)

        # Update seen cards (include opponent pickups — they
        # left the discard pile but we still saw them)
        self._seen_cards = (
            set(view.hand)
            | set(view.discard_pile)
            | set(self._opponent_pickups)
        )

        # Update snapshot
        self._prev_discard_top = view.top_of_discard
        self._prev_discard_len = current_len

    # --- Draw Decision ---

    @staticmethod
    def _hand_score(hand: List[Card]) -> float:
        """Score a hand for draw evaluation.

        Uses negative deadwood plus a small bonus per meld,
        which favors hands with more formed melds at equal
        deadwood (more flexible, faster to improve).
        """
        melds, _ = get_best_melds(hand)
        return -calculate_deadwood(hand) + 2.5 * len(melds)

    def _best_score_after_draw(
        self, hand: List[Card], drawn: Card,
        can_discard_drawn: bool = True,
    ) -> float:
        """Best hand score after drawing a card and discarding."""
        extended = hand + [drawn]
        discardable = extended if can_discard_drawn else hand
        return max(
            self._hand_score([c for c in extended if c != d])
            for d in discardable
        )

    def draw_decision(self, view: PlayerView) -> str:
        hand = view.hand
        discard_card = view.top_of_discard

        # EV of taking the discard (known card, can't discard back)
        discard_ev = self._best_score_after_draw(
            hand, discard_card, can_discard_drawn=False
        )

        # EV of drawing from deck: average over all unseen cards
        unseen = ALL_CARDS - self._seen_cards
        if unseen:
            deck_ev = sum(
                self._best_score_after_draw(hand, card)
                for card in unseen
            ) / len(unseen)
        else:
            deck_ev = discard_ev

        # Take the option with higher expected hand score
        if discard_ev >= deck_ev:
            self._drew_from_discard = discard_card
            return "discard"

        self._drew_from_discard = None
        return "deck"

    # --- Discard Decision ---

    def discard_decision(self, view: PlayerView) -> Card:
        hand = view.hand
        excluded = self._drew_from_discard
        seen = (
            set(hand)
            | set(view.discard_pile)
            | set(self._opponent_pickups)
        )
        my_hand_set = set(hand)

        # Build candidate list (exclude card just drawn from discard)
        candidates = (
            [c for c in hand if c != excluded]
            if excluded else list(hand)
        )
        if not candidates:
            candidates = list(hand)

        # Score each candidate
        best_card = candidates[0]
        best_score = float("-inf")

        # Precompute deadwood-after for all candidates
        dw_values = {c: deadwood_after_discard(hand, c) for c in candidates}

        for card in candidates:
            score = 0.0

            # 1. Deadwood after discarding (primary — this is
            # almost the entire signal in head-to-head testing)
            dw_after = dw_values[card]
            score -= dw_after

            # 2-3: Safety tiebreakers. Head-to-head testing shows
            # these are near-zero signal against current bots
            # (~50.8-51.2% edge), but kept as insurance against
            # smarter opponents who exploit discard information.

            # 2. Prefer provably safe discards
            if is_provably_safe_discard(card, seen, my_hand_set):
                score += 1.0

            # 3. Avoid feeding cards to opponent based on
            # what they picked up from the discard pile
            for pickup in self._opponent_pickups:
                if card.rank == pickup.rank:
                    score -= 1.0
                if (card.suit == pickup.suit
                        and abs(card.rank.value
                                - pickup.rank.value) <= 1):
                    score -= 0.5

            if score > best_score:
                best_score = score
                best_card = card

        return best_card

    # --- Knock Decision ---

    def knock_decision(self, view: PlayerView) -> bool:
        # Always knock when eligible — giving the opponent more
        # turns is worse than the risk of being undercut
        return True
