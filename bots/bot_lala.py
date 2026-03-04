"""Student Bot Template — start building your bot here!

Instructions:
1. Rename this file to something like "bot_<name>.py"
2. Rename the class to something like "MyBot"
3. Implement your strategy in the three required methods
4. Test your bot by running it against the sample bots

Available information in 'view' (a PlayerView object):
- view.hand:              Your current cards (list of Card objects)
- view.discard_pile:      All discarded cards so far (list)
- view.top_of_discard:    The top card of the discard pile (or None)
- view.deck_size:         Number of cards left in the deck
- view.opponent_hand_size: Number of cards in opponent's hand
- view.phase:             Current game phase

Useful utility functions (import from framework.utilities):
- calculate_deadwood(hand)         → Your total deadwood points
- is_gin(hand)                     → True if deadwood is 0
- can_knock(hand)                  → True if deadwood <= 10
- get_melds(hand)                  → All possible melds in your hand
- get_best_melds(hand)             → (melds, unmelded) optimal arrangement
- get_unmelded_cards(hand)         → Cards not part of any meld
- best_discard(hand)               → The card to discard for min deadwood
- deadwood_after_discard(hand, c)  → Deadwood if you discard card c
- evaluate_discard_draw(hand, c)   → Best deadwood if you take card c
- card_deadwood_contribution(hand, c) → How much card c hurts your hand

Strategy ideas to try:
- Take from the discard pile when the card completes a meld
- Track what your opponent discards to avoid giving them useful cards
- Only knock when your deadwood is very low (reduces undercut risk)
- Consider which cards are "near" melds (e.g., two of a kind, partial runs)
- Be more aggressive about knocking when the deck is running low
"""

from collections import Counter #from ChatGPT
from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
    get_best_melds,
    get_unmelded_cards
)


class StudentBot(Bot):
    """Your custom Gin Rummy bot!"""

    @property
    def name(self) -> str:
        return "LalaBot"

    def __init__(self):
        super().__init__()
        self.picked_up = None
        self._seen_discards = set()

    def draw_decision(self, view: PlayerView) -> str:
        """Choose where to draw from: "deck" or "discard".

        Tip: Use evaluate_discard_draw() to check if the discard
        pile card would improve your hand.

        Important: If you draw from the discard pile, remember the
        card (e.g., save view.top_of_discard) so you don't try to
        discard it — that's an illegal move!
        """
        if view.top_of_discard is not None:
            melds, unmelded = get_best_melds(view.hand + [view.top_of_discard])
            if view.top_of_discard not in unmelded:
                self.picked_up = view.top_of_discard
                return "discard"
            deadwood = calculate_deadwood(view.hand)
            deadwood_if_taken = evaluate_discard_draw(view.hand, view.top_of_discard)
            if deadwood_if_taken < deadwood - 2:
                self.picked_up = view.top_of_discard
                return "discard"

        self.picked_up = None
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        """Choose which card to discard from your 11-card hand.

        Tip: Use best_discard() to find the card that minimizes
        your deadwood, or implement your own logic.

        Important: You cannot discard a card you just drew from
        the discard pile on the same turn.

        """
        # The validator was being annoying so I added this if statement
        if view.top_of_discard is not None:
            self._seen_discards.add(view.top_of_discard)

        hand = view.hand
        excluded = self.picked_up
        unmelded = get_unmelded_cards(hand)
        candidates = unmelded

        if excluded is not None:
            candidates = [c for c in candidates if c != excluded]

        #ChatGPT said this would debug an index out of range error, but honeslty, I don't really get how
        if not candidates:
            candidates = view.hand

        rank_counts = Counter(c.rank for c in hand)

        scored = []
        for card in candidates:
            score = card.deadwood_value

            if rank_counts[card.rank] >= 2:
                score -= 6

            same_suit = [c for c in hand if c.suit == card.suit and c != card]
            run_neighbors = 0

            for c in same_suit:
                if abs(c.rank.value - card.rank.value) == 1:
                    run_neighbors += 1

            if run_neighbors == 2:
                score -= 8
            elif run_neighbors == 1:
                score -= 4

            rank_seen = 0
            for c in self._seen_discards:
                if c.rank == card.rank:
                    rank_seen += 1
            score += rank_seen * 2

            scored.append((score, card))

        scored.sort(key=lambda x: x[0], reverse=True)

        choice = scored[0][1]
        self.picked_up = None
        return choice

    def knock_decision(self, view: PlayerView) -> bool:
        """Decide whether to knock (called when deadwood <= 10).

        Tip: Knocking with very low deadwood is safer. Knocking
        with high deadwood (close to 10) risks being undercut.
        """
        deadwood = calculate_deadwood(view.hand)
        if deadwood == 0:
            return True
        if view.deck_size < 8:
            return deadwood <= 7
        return deadwood <= 6