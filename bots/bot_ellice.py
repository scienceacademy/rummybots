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
from framework.utilities import(
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
    get_melds,
    deadwood_after_discard,
    is_gin,
    can_knock,
)


class EllicesRummyKimmy(Bot):
    """Your custom Gin Rummy bot!

    Implement your strategy by modifying the three methods below.
    You can also override on_game_start() and on_turn_end() to
    track game state between turns.
    """
    @property
    def name(self) -> str:
        # Give your bot a name!
        return "EllicesRummyKimmy_bot"

    def __init__(self):
        self.just_drew_discard = None
        self.seen_cards = set()

    def on_turn_end(self, view: PlayerView):
        if view.top_of_discard:
            self.seen_cards.add(view.top_of_discard)


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
        discard = view.top_of_discard

        if discard is None:
            return "deck"

        current_deadwood = calculate_deadwood(view.hand)
        new_deadwood = evaluate_discard_draw(view.hand, discard)

        if new_deadwood <= current_deadwood - 2:
            self.just_drew_discard = discard
            return "discard"

        test_hand = view.hand + [discard]
        if len(get_melds(test_hand)) > len(get_melds(view.hand)):
            self.just_drew_discard = discard
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
        best_card = None
        best_score = float("inf")

        for card in view.hand:

            if card == self.just_drew_discard:
                continue

            deadwood = deadwood_after_discard(view.hand, card)

            danger_penalty = 0
            if 3 <= card.rank.value <= 10:
                danger_penalty += 1

            score = deadwood + danger_penalty

            if score < best_score:
                best_score = score
                best_card = card

        if best_card is None:
            best_card = best_discard(view.hand)

        self.just_drew_discard = None
        return best_card

    def knock_decision(self, view: PlayerView) -> bool:
        """Decide whether to knock (called when deadwood <= 10).

        Tip: Knocking with very low deadwood is safer. Knocking
        with high deadwood (close to 10) risks being undercut.
        """
        # --- Your strategy here ---
        # Example: always knock when eligible
        deadwood = calculate_deadwood(view.hand)

        if is_gin(view.hand):
            return True

        if not can_knock(view.hand):
            return False

        if deadwood <= 3:
            return True

        if view.deck_size <= 8 and deadwood <= 6:
            return True

        if deadwood <= 6:
            return True

        return False
