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
    calculate_deadwood,      # Total deadwood points for a hand
    is_gin,                  # True if deadwood is 0
    can_knock,               # True if deadwood <= 10
    get_melds,               # All possible melds in a hand
    get_best_melds,          # Optimal melds + leftover cards
    get_unmelded_cards,      # Cards not in any meld
    best_discard,            # Card to discard for minimum deadwood
    deadwood_after_discard,  # Deadwood if you discard a specific card
    evaluate_discard_draw,   # Best deadwood if you take the discard card
    card_deadwood_contribution,  # How much a card hurts your hand
    count_meld_outs,           # How many unseen cards complete melds with this card
    is_provably_safe_discard,  # True if opponent can't use this card in any meld
    score_discard_safety,      # Rate how safe it is to discard (0=dangerous, 1=safe)
    calculate_hand_strength,   # Overall hand strength (0.0=weak, 1.0=gin)
    count_near_melds,
)

class MilanBot(Bot):
    """Your custom Gin Rummy bot!

    Implement your strategy by modifying the three methods below.
    You can also override on_game_start() and on_turn_end() to
    track game state between turns.
    """

    @property
    def name(self) -> str:
        # Give your bot a name!
        return "Dani is an NPC"

    def draw_decision(self, view: PlayerView) -> str:
        """Choose where to draw from: "deck" or "discard".

        Tip: Use evaluate_discard_draw() to check if the discard
        pile card would improve your hand.

        Important: If you draw from the discard pile, remember the
        card (e.g., save view.top_of_discard) so you don't try to
        discard it — that's an illegal move!
        """

        self._drew_from_discard = None
        melds, unmelded = get_best_melds(view.hand)
        possiblehand = []
        possiblehand.append(view.top_of_discard)
        for card in view.hand:
            possiblehand.append(card)
        #if adds to existing meld or creates new meld
        if view.top_of_discard is not None:
            if card_deadwood_contribution(possiblehand, view.top_of_discard) == 0:
                self._drew_from_discard = view.top_of_discard
                return "discard"
            #to get into knock zone
            elif len(unmelded) <= 4 or calculate_deadwood(view.hand) <= 10:
                for card in unmelded:
                    if deadwood_after_discard(view.hand, card) < card_deadwood_contribution(possiblehand, view.top_of_discard):
                        self._drew_from_discard = view.top_of_discard
                        return "discard"
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

        legal_choices = [c for c in view.hand if c!= self._drew_from_discard]
        melded, choices = get_best_melds(legal_choices)
        if len(choices) != 0:
            if view.deck_size <= 22 or len(choices) <= 5 or calculate_deadwood(view.hand) <= 10:
                return best_discard(choices)
            keep = []
            for c in choices:
                possibility = [card for card in choices if card != c]
                if count_near_melds(possibility) < count_near_melds(choices):
                    keep.append(c)
            if len(keep) != 0 and len(keep) != len(choices):
                final_choices = [card for card in choices if card not in keep]
                return best_discard(final_choices)
            else:
                return best_discard(choices)
        return best_discard(legal_choices)

    def knock_decision(self, view: PlayerView) -> bool:
        """Decide whether to knock (called when deadwood <= 10).

        Tip: Knocking with very low deadwood is safer. Knocking
        with high deadwood (close to 10) risks being undercut.
        """
        deadwood = calculate_deadwood(view.hand)
        if is_gin(view.hand):
            return True
        if view.deck_size >= 22:
            return True
        if view.deck_size >= 11 and deadwood <= 6:
            return True
        return deadwood <= 2