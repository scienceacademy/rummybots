"""AdvancedBot — a strong Gin Rummy bot with multi-factor strategy.

Key advantages over simpler bots:
- Meld-aware draw: always takes from discard when it completes a meld
- Defensive discarding: tracks opponent picks, avoids feeding them cards
- Near-meld preservation: keeps pairs and partial runs with live outs
- Card counting: uses seen cards to evaluate safety and meld potential
- Conservative knock: avoids undercuts by waiting for low deadwood
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
        if len(view.discard_pile) < self._prev_discard_len:
            if self._prev_discard_top is not None:
                self._opponent_picks.append(self._prev_discard_top)
        self._prev_discard_top = view.top_of_discard
        self._prev_discard_len = len(view.discard_pile)

    # --- Draw ---

    def draw_decision(self, view: PlayerView) -> str:
        if view.top_of_discard is None:
            self._drew_from_discard = None
            return "deck"

        discard_card = view.top_of_discard
        hand = view.hand
        current_dw = calculate_deadwood(hand)

        # Always take if it completes a new meld
        old_melds = len(find_best_melds(hand)[0])
        new_melds = len(find_best_melds(hand + [discard_card])[0])
        if new_melds > old_melds:
            self._drew_from_discard = discard_card
            return "discard"

        # Take if it significantly improves deadwood
        if_take = evaluate_discard_draw(hand, discard_card)
        if if_take <= current_dw - 2:
            self._drew_from_discard = discard_card
            return "discard"

        self._drew_from_discard = None
        return "deck"

    # --- Discard ---

    def discard_decision(self, view: PlayerView) -> Card:
        hand = view.hand
        excluded = self._drew_from_discard
        self._drew_from_discard = None

        melds, unmelded = find_best_melds(hand)
        melded_cards = set()
        for m in melds:
            melded_cards.update(m)

        # Score all non-excluded cards
        candidates = [c for c in hand if c != excluded]
        if not candidates:
            candidates = list(hand)

        current_dw = calculate_deadwood(hand)
        best_card = candidates[0]
        best_score = float("-inf")

        for card in candidates:
            score = 0.0

            # Deadwood reduction (primary)
            after_dw = deadwood_after_discard(hand, card)
            score += (current_dw - after_dw) * 15

            if card in melded_cards:
                # Heavy penalty for breaking melds
                score -= 25
            else:
                # Penalty for near-meld cards (keep them)
                score -= self._near_meld_value(card, hand) * 5

            # Safety: prefer cards opponent doesn't want
            score += self._safety_score(card) * 3

            # Tiebreaker: prefer discarding high deadwood
            score += card.deadwood_value * 0.5

            if score > best_score:
                best_score = score
                best_card = card

        return best_card

    def _near_meld_value(self, card: Card, hand: List[Card]) -> float:
        """How valuable is this card for future melds? Higher = keep."""
        others = [c for c in hand if c != card]
        value = 0.0

        # Same rank: working toward a set
        same_rank = sum(1 for c in others if c.rank == card.rank)
        if same_rank >= 2:
            value += 4
        elif same_rank == 1:
            # Pair: bonus scaled by unseen completing cards
            needed_suits = (
                {Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES}
                - {card.suit}
                - {c.suit for c in others if c.rank == card.rank}
            )
            available = sum(
                1 for s in needed_suits
                if Card(card.rank, s) not in self._seen_cards
            )
            value += 1.5 + available * 0.5

        # Same suit neighbors: working toward a run
        same_suit = [c for c in others if c.suit == card.suit]
        adjacent = sum(
            1 for c in same_suit
            if abs(c.rank.value - card.rank.value) == 1
        )

        if adjacent >= 2:
            value += 4  # Middle of 3-card run sequence
        elif adjacent == 1:
            value += 2
            # Bonus if completing card is still unseen
            for c in same_suit:
                if abs(c.rank.value - card.rank.value) == 1:
                    low = min(card.rank.value, c.rank.value)
                    high = max(card.rank.value, c.rank.value)
                    for v in [low - 1, high + 1]:
                        if 1 <= v <= 13:
                            needed = Card(Rank(v), card.suit)
                            if needed not in self._seen_cards:
                                value += 1
                                break
                    break

        return value

    def _safety_score(self, card: Card) -> float:
        """How safe is discarding this card? Higher = safer."""
        safety = 0.0

        for pick in self._opponent_picks:
            if pick.rank == card.rank:
                safety -= 4
            if (pick.suit == card.suit
                    and abs(pick.rank.value - card.rank.value) <= 2):
                safety -= 2

        seen_same_rank = sum(
            1 for c in self._seen_cards
            if c.rank == card.rank and c != card
        )
        safety += seen_same_rank * 1.5

        return safety

    # --- Knock ---

    def knock_decision(self, view: PlayerView) -> bool:
        dw = calculate_deadwood(view.hand)

        if dw == 0:
            return True

        deck_size = view.deck_size

        if deck_size < 4:
            return True
        else:
            return dw <= 5
