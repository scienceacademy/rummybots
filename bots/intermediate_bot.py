"""IntermediateBot — a more strategic bot for students to compete against.

This bot demonstrates several intermediate strategies:
- Evaluates the discard pile card before deciding where to draw
- Tracks which cards have been discarded to avoid helping the opponent
- Makes strategic knock decisions based on deadwood level
- Uses the utility library for hand analysis
"""

from collections import defaultdict
from typing import Set

from engine.card import Card, Rank
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
    get_unmelded_cards,
)


class IntermediateBot(Bot):
    """A bot with intermediate-level strategy.

    Strategies:
    - Takes from discard pile when it clearly improves the hand
    - Avoids discarding cards the opponent might want
    - Only knocks with low deadwood to reduce undercut risk
    """

    KNOCK_THRESHOLD = 5  # Only knock when deadwood is this low

    @property
    def name(self) -> str:
        return "IntermediateBot"

    def __init__(self):
        self._seen_discards: Set[Card] = set()
        self._opponent_picks: Set[Card] = set()
        self._last_discard_len = 0
        self._drew_from_discard = None

    def on_game_start(self, player_index: int, view: PlayerView) -> None:
        self._seen_discards = set()
        self._opponent_picks = set()
        self._last_discard_len = len(view.discard_pile)

    def on_turn_end(self, view: PlayerView) -> None:
        current_len = len(view.discard_pile)
        # If discard pile shrank, opponent picked up from it
        if current_len < self._last_discard_len:
            # We can't know exactly which card, but we track the event
            pass
        # Track all discarded cards
        for card in view.discard_pile:
            self._seen_discards.add(card)
        self._last_discard_len = current_len

    def draw_decision(self, view: PlayerView) -> str:
        if view.top_of_discard is None:
            self._drew_from_discard = None
            return "deck"

        # Evaluate if taking the discard improves our hand
        current_dw = calculate_deadwood(view.hand)
        if_take = evaluate_discard_draw(view.hand, view.top_of_discard)

        # Only take from discard if it meaningfully improves our hand
        if if_take < current_dw - 2:
            self._drew_from_discard = view.top_of_discard
            return "discard"

        self._drew_from_discard = None
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        hand = view.hand
        unmelded = get_unmelded_cards(hand)

        # Exclude the card we just drew from the discard pile
        excluded = self._drew_from_discard

        if not unmelded:
            # All cards are melded — discard any allowed card
            choices = [c for c in hand if c != excluded] if excluded else hand
            return best_discard(choices) if choices else hand[0]

        # Among unmelded cards, prefer discarding ones that are
        # less likely to help the opponent (already seen in discards,
        # or isolated high cards)
        candidates = unmelded
        if excluded is not None:
            candidates = [c for c in candidates if c != excluded]
            if not candidates:
                candidates = [c for c in hand if c != excluded]

        scored = []
        for card in candidates:
            score = card.deadwood_value  # higher = more want to discard

            # Bonus for discarding cards whose rank has been seen
            # (opponent less likely to need them)
            rank_seen = sum(
                1 for c in self._seen_discards if c.rank == card.rank
            )
            score += rank_seen * 2

            scored.append((score, card))

        # Discard the highest-scored card
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def knock_decision(self, view: PlayerView) -> bool:
        deadwood = calculate_deadwood(view.hand)
        # Always knock on gin
        if deadwood == 0:
            return True
        # Only knock with low deadwood to reduce undercut risk
        return deadwood <= self.KNOCK_THRESHOLD
