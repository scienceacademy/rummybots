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
from framework.utilities import *
from itertools import *
from collections import *
from math import *


class SuttBot(Bot):
    """Your custom Gin Rummy bot!

    Implement your strategy by modifying the three methods below.
    You can also override on_game_start() and on_turn_end() to
    track game state between turns.
    """
    def __init__(self):
        self.discardDrawn = None
    def setpairs(self, hand) -> list:
        """Find all possible sets (3-4 of same rank) in a hand."""
        by_rank = defaultdict(list)
        for card in get_unmelded_cards(hand):
            by_rank[card.rank].append(card)

        sets = []
        for rank, cards in by_rank.items():
            if len(cards) == 2:
                # Add 3-card sets
                for combo in combinations(cards, 2):
                    sets.append(list(combo))
        return sets


    def runpairs(self, hand) -> list:
        by_suit = defaultdict(list)
        for card in get_unmelded_cards(hand):
            by_suit[card.suit].append(card)

        runs = []
        for suit, cards in by_suit.items():
            sorted_cards = sorted(cards, key=lambda c: c.rank.value)
            values = [c.rank.value for c in sorted_cards]

            # Find all consecutive sequences of length >= 2
            for start in range(len(sorted_cards)):
                for end in range(start + 2, len(sorted_cards) + 1):
                    subseq = sorted_cards[start:end]
                    subvals = values[start:end]
                    # Check consecutive
                    is_consecutive = all(
                        subvals[i] == subvals[i - 1] + 1
                        for i in range(1, len(subvals))
                    )
                    if is_consecutive:
                        runs.append(subseq)
        return runs


    @property
    def name(self) -> str:
        # Give your bot a name!
        return "suttv2"

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
        for card in view.hand:
            if card.rank == view.top_of_discard.rank:
                # print("drawn " + str(view.top_of_discard))
                self.discardDrawn = view.top_of_discard
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
        # print("\nHand before discard: " + str(sorted(view.hand)))
        # print("\nDiscard before discard: " + str(view.discard_pile))
        setPairs = self.setpairs(view.hand)
        runPairs = self.runpairs(view.hand)
        # print("Sets: " + str(setPairs))

        hand = view.hand
        if(self.discardDrawn) in hand:
            hand.remove(self.discardDrawn)
        for pair in setPairs:
            for card in pair:
                if card in hand:
                    hand.remove(card)
        runPairs = self.runpairs(hand)
        # print("Runs of exc hand: " + str(runPairs))
        for pair in runPairs:
            for card in pair:
                if card in hand:
                    hand.remove(card)
        for set in get_best_melds(view.hand)[:-1][0]:
            for card in set:
                if card in hand:
                    hand.remove(card)
        tempHand = view.hand
        if self.discardDrawn in tempHand:
            tempHand.remove(self.discardDrawn)
        # print("best melds of excluded hand: " + str(get_best_melds(hand)))
        if not hand:
            # print("discarded " + str(best_discard(tempHand)))
            return best_discard(tempHand)
        else:
            # print("discarded " + str(best_discard(hand)))
            return best_discard(hand)

    def knock_decision(self, view: PlayerView) -> bool:
        """Decide whether to knock (called when deadwood <= 10).

        Tip: Knocking with very low deadwood is safer. Knocking
        with high deadwood (close to 10) risks being undercut.
        """
        # --- Your strategy here ---
        return True