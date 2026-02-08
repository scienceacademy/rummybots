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
    evaluate_discard_draw,
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
        return "StudentBot"

    def draw_decision(self, view: PlayerView) -> str:
        """Choose where to draw from: "deck" or "discard".

        Tip: Use evaluate_discard_draw() to check if the discard
        pile card would improve your hand.

        Important: If you draw from the discard pile, remember the
        card (e.g., save view.top_of_discard) so you don't try to
        discard it — that's an illegal move!
        """
        # --- Your strategy here ---
        # Example: always draw from the deck (safe but basic)
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        """Choose which card to discard from your 11-card hand.

        Tip: Use best_discard() to find the card that minimizes
        your deadwood, or implement your own logic.

        Important: You cannot discard a card you just drew from
        the discard pile on the same turn.
        """
        # --- Your strategy here ---
        # Example: discard the card that minimizes deadwood
        return best_discard(view.hand)

    def knock_decision(self, view: PlayerView) -> bool:
        """Decide whether to knock (called when deadwood <= 10).

        Tip: Knocking with very low deadwood is safer. Knocking
        with high deadwood (close to 10) risks being undercut.
        """
        # --- Your strategy here ---
        # Example: always knock when eligible
        return True
