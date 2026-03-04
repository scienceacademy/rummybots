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

class Martin_bot(Bot):
    def __init__(self):
        self.drew_from_discard = None

    @property
    def name(self) -> str:
        # Give your bot a name!
        return "Martin_bot"
    def draw_decision(self, view: PlayerView) -> str:
        self.drew_from_discard = None

        current_dw = calculate_deadwood(view.hand)
        new_dw = evaluate_discard_draw(view.hand, view.top_of_discard)

        if new_dw < current_dw:
            self.drew_from_discard = view.top_of_discard
            return "discard"
        else:
            return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        choices_filtered = []
        #see if best discard is safe
        #if is_provably_safe_discard(best_discard(view.hand), view.hand + view.discard_pile) and best_discard(view.hand) != dont_touch:
        for c in view.hand:
            if c != self.drew_from_discard:
                choices_filtered.append(c)
        return best_discard(choices_filtered)




    def knock_decision(self, view: PlayerView) -> bool:
        """Decide whether to knock (called when deadwood <= 10).

        Tip: Knocking with very low deadwood is safer. Knocking
        with high deadwood (close to 10) risks being undercut.
        """
        # --- Your strategy here ---
        # Example: always knock when eligible
        if view.deck_size <= 15 and calculate_deadwood(view.hand) <= 10:
            return True
        elif calculate_deadwood(view.hand) <= 8 and view.deck_size <= 30:
            return True
        elif calculate_deadwood(view.hand) <= 6:
            return True
        else:
            return False

