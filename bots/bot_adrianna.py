"""Student Bot Template — start building your bot here!

Instructions:
1. Rename this file to something like "bot_<name>.py"
2. Rename the class to something like "MyBot" *****************
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
    get_best_melds,
    can_knock,
)


class AdriannaBot(Bot):
    """Your custom Gin Rummy bot!

    Implement your strategy by modifying the three methods below.
    You can also override on_game_start() and on_turn_end() to
    track game state between turns.
    """

    @property
    def name(self) -> str:
        # Give your bot a name!
        return "Adrianna_bot"

    def draw_decision(self, view: PlayerView) -> str:

        self._drew_from_discard = None

        top = view.top_of_discard

        if top is None:
            return "deck"

        # current best meld possible

        current_unmelded = get_best_melds(view.hand)

        # adding top card

        new_hand = view.hand + [top]
        new_unmelded = get_best_melds(new_hand)

        # draw if its good for your meld, or an almost meld

        if len(new_unmelded) < len(current_unmelded):

            self._drew_from_discard = top
            return "discard"

        # basically does it balance high cards w low card?

        high_cards = [c for c in view.hand if c.deadwood_value >= 10]
        if top.deadwood_value <= 5 and len(high_cards) >= 2:

            self._drew_from_discard = top
            return "discard"

        return "deck"


        """Choose where to draw from: "deck" or "discard".

        Tip: Use evaluate_discard_draw() to check if the discard
        pile card would improve your hand.

        Important: If you draw from the discard pile, remember the
        card (e.g., save view.top_of_discard) so you don't try to
        discard it — that's an illegal move!
        """
        # --- Your strategy here ---
        # Example: always draw from the deck (safe but basic)

    def discard_decision(self, view: PlayerView) -> Card:

        """Choose which card to discard from your 11-card hand.

        Tip: Use best_discard() to find the card that minimizes
        your deadwood, or implement your own logic.

        Important: You cannot discard a card you just drew from
        the discard pile on the same turn.
        """

        legal_choices = [card for card in view.hand if card != self._drew_from_discard]

        # get best meld structure

        melds, unmelded = get_best_melds(legal_choices)

        # if everything is melded we should knock guys, but thats later

        if not unmelded:
            return best_discard(legal_choices)

        # identify near melds among your hand/non melds

        near_meld_cards = set()

        for card in unmelded:
            # check for a pair
            same_rank = [c for c in unmelded if c.deadwood_value == card.deadwood_value]
            if len(same_rank) == 2:
                near_meld_cards.update(same_rank)

            # check consecutive cards of the same suit
            """
            for other in unmelded:
                if (
                    other != card and
                    other.suit == card.suit and
                    abs(other.deadwood_value - card.deadwood_value) == 1
                ):
                    near_meld_cards.add(card)
                    near_meld_cards.add(other) """

            # discard cards NOT in melds (candidates)

            candidates = [c for c in unmelded if c not in near_meld_cards]

            if candidates:
                highest = candidates[0]

            for card in candidates:
                if card.deadwood_value > highest.deadwood_value:
                    highest = card

                return highest

            highest = unmelded[0]

            for card in unmelded:
                if card.deadwood_value > highest.deadwood_value:
                    highest = card

            return highest

    def knock_decision(self, view: PlayerView) -> bool:
        """Decide whether to knock (called when deadwood <= 10).

        Tip: Knocking with very low deadwood is safer. Knocking
        with high deadwood (close to 10) risks being undercut.
        """
        return can_knock(view.hand)
