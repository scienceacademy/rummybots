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
    count_meld_outs,
    card_deadwood_contribution
)


class jackS2(Bot):
    """Your custom Gin Rummy bot!

    Implement your strategy by modifying the three methods below.
    You can also override on_game_start() and on_turn_end() to
    track game state between turns.
    """

    @property
    def name(self) -> str:
        # Give your bot a name!
        return "jackS2"

    def __init__(self):
        self._drew_from_discard = None

    def draw_decision(self, view: PlayerView) -> str:
        """Choose where to draw from: "deck" or "discard".

        Tip: Use evaluate_discard_draw() to check if the discard
        pile card would improve your hand.

        Important: If you draw from the discard pile, remember the
        card (e.g., save view.top_of_discard) so you don't try to
        discard it — that's an illegal move!
        """
        # remember if drew from discard to try to not break things
        if view.top_of_discard is None:
            self._drew_from_discard = None
            return "deck"
        current = calculate_deadwood(view.hand)
        if_take = evaluate_discard_draw(view.hand, view.top_of_discard)
        if if_take < current - 2:
              self._drew_from_discard = view.top_of_discard
              return "discard"
        else:
            self._drew_from_discard = None
            return "deck"

#draw from discard if it makes the hand better (but more than just a 2 point difference)
#draw from normal if else

    def discard_decision(self, view: PlayerView) -> Card:
        """Choose which card to discard from your 11-card hand.

        Tip: Use best_discard() to find the card that minimizes
        your deadwood, or implement your own logic.

        Important: You cannot discard a card you just drew from
        the discard pile on the same turn.
        """
        hand = view.hand
        # don't discard the card drawn from the discard pile
        # (from intermediate bot)
        excluded = self._drew_from_discard
        choices = [c for c in hand if c != excluded] if excluded else hand

# earlier, discard the cards with few outs, but keep in mind deadwood value and if they help complete melds and stuff
#later, discard the ones adding the most to the hand?
        seen = set(hand + view.discard_pile)
        if view.deck_size > 23:
            return max(choices, key=lambda card: card.deadwood_value + card_deadwood_contribution(hand, card) - (count_meld_outs(card, hand, seen) * 2))

        return best_discard(view.hand)
    def knock_decision(self, view: PlayerView) -> bool:
        """Decide whether to knock (called when deadwood <= 10).

        Tip: Knocking with very low deadwood is safer. Knocking
        with high deadwood (close to 10) risks being undercut.
        """
        # in the early game, knock as soon as possible.
        # later, knock if there is a low deadwood

        current_dw = calculate_deadwood(view.hand)
        if current_dw == 0:
            return True
        # deck should start at 31 cards?
        if view.deck_size > 25:
            return True
        if view.deck_size > 10:
            return current_dw < 7

        return current_dw <= 3