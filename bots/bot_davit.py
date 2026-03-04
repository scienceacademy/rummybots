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
)

class DavitBOT(Bot):

    def __init__(self):
        self._drew_from_discard = None

    @property
    def name(self) -> str:
        return "DavitBOT"

    # This helps with removing the discarded card. The deadwood needs to be as small as possible.
    def draw_decision(self, view: PlayerView) -> str:
        self._drew_from_discard = None
        top = view.top_of_discard

        if top:
            if evaluate_discard_draw(view.hand, top) < calculate_deadwood(view.hand):
                self._drew_from_discard = top
                return "discard"

        return "deck"

    # This tries to protect melded and cards that are close to a 3 of a kind. It also tries to protect pairs.
    def discard_decision(self, view: PlayerView) -> Card:
        hand = list(view.hand)
        excluded = self._drew_from_discard

        #This is so I cant get rid of the card I just picked up
        ALLOWTHISFOREVER = [c for c in hand if c != excluded] if excluded else hand

        melds, _ = get_best_melds(hand)
        melded = {card for meld in melds for card in meld}
        unmelded = [c for c in get_unmelded_cards(hand) if c != excluded]

        # This is for protecting pairs
        rank_counts = {}
        for c in hand:
            rank_counts[c.rank] = rank_counts.get(c.rank, 0) + 1

        # Un melded cards arent the best., so it is good to get rid of them.
        SUPERIMPORTANTUNMELDTHING = unmelded if unmelded else ALLOWTHISFOREVER

        def score(card):
            value = card_deadwood_contribution(hand, card) * 10
            if card in melded:
                value -= 10
            if rank_counts[card.rank] >= 2:
                value -= 0
            return value

        return max(SUPERIMPORTANTUNMELDTHING, key=score)

    # I need to knock ASAP. I dont want to save up for a gin, I jsut need to knock as soon as possible
    # Even though it is risky, it is better than waiting.
    def knock_decision(self, view: PlayerView) -> bool:
        return can_knock(view.hand)