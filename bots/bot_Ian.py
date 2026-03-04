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

from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw, get_best_melds, get_unmelded_cards
)


class StudentBot(Bot):
    """Your custom Gin Rummy bot!

    Implement your strategy by modifying the three methods below.
    You can also override on_game_start() and on_turn_end() to
    track game state between turns.
    """

    @property
    def name(self) -> str:
        # Give your bot a name!
        return "IanBot"

    def draw_decision(self, view: PlayerView) -> str:
        """Choose where to draw from: "deck" or "discard".

        Tip: Use evaluate_discard_draw() to check if the discard
        pile card would improve your hand.

        Important: If you draw from the discard pile, remember the
        card (e.g., save view.top_of_discard) so you don't try to
        discard it — that's an illegal move!
        """
        # --- Your strategy here ---

        if view.top_of_discard is None:
            self._drew_from_discard = None
            return "deck"

        current_dw = calculate_deadwood(view.hand)
        if_take = evaluate_discard_draw(view.hand, view.top_of_discard)
     # Current meld info
        current_melds, _ = get_best_melds(view.hand)
        current_melded_cards = sum(len(m) for m in current_melds)
        current_max_meld_size = max([len(m) for m in current_melds], default=0)

    # Simulate adding discard
        new_hand = list(view.hand)
        new_hand.append(view.top_of_discard)
        new_melds, _ = get_best_melds(new_hand)
        new_melded_cards = sum(len(m) for m in new_melds)
        new_max_meld_size = max([len(m) for m in new_melds], default=0)

    #  creates a new meld
        creates_new_meld = new_melded_cards > current_melded_cards

    #  extends a meld to 4+ cards
        extends_to_four = (
            new_max_meld_size >= 4 and
            new_max_meld_size > current_max_meld_size
        )

        if creates_new_meld or extends_to_four:
            self._drew_from_discard = view.top_of_discard
            return "discard"

        elif if_take < current_dw - 2:
            self._drew_from_discard = view.top_of_discard
            return "discard"
        self._drew_from_discard = None
        return "deck"



    def discard_decision(self, view: PlayerView) -> Card:
        """Choose which card to discard from your 11-card hand.

        Tip: Use best_discard() to find the card that minimizes
        your deadwood, or implement your own logic.

        Important: You cannot discard a card you just drew from
        the discard pile on the same turn.
        """
                # --- Your strategy here ---
        hand = view.hand

        unmelded = get_unmelded_cards(hand)

        excluded = self._drew_from_discard

        rank_counts = {}

        for card in hand:
            rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1

        def card_value(card):
            """Gin deadwood value (face cards = 10)."""
            return min(card.rank, 10)

        def discard_score(card):
            score = 0

        # High card value (higher = more likely to discard)
            score += card_value(card) * 10

        # Prevent cards close to melds from getting discarded
            if rank_counts[card.rank] >= 2:
                score -= 25  # protect pairs

        # prevent melded cards from getting discarded
            discard = max(key=discard_score)
            melds, _ = get_best_melds(hand)
            for meld in melds:
                if card in meld:
                    score -= 40

            return score
        if not unmelded:
            choices = [c for c in hand if c != excluded] if excluded else hand
            return best_discard(choices) if choices else hand[0]
        return best_discard(view.hand)

    def knock_decision(self, view: PlayerView) -> bool:

        deadwood = calculate_deadwood(view.hand)

    # Always knock for gin
        if deadwood == 0:
            return True

    # Early game
        if view.deck_size > 27:
           return deadwood <= 4

    # Mid game
        if view.deck_size > 18:
            return deadwood <= 6

    # Late game
        return deadwood <= 10
