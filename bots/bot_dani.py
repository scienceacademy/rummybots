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
    is_gin,
    get_best_melds,
    get_unmelded_cards,
    evaluate_discard_draw,
    calculate_hand_strength,
    count_near_melds
)


class DaniBot(Bot):
    """Your custom Gin Rummy bot!

    Implement your strategy by modifying the three methods below.
    You can also override on_game_start() and on_turn_end() to
    track game state between turns.
    """

    @property
    def name(self) -> str:
        # Give your bot a name!
        return "DaniBot"

    def draw_decision(self, view: PlayerView) -> str:
        """Choose where to draw from: "deck" or "discard".

        Tip: Use evaluate_discard_draw() to check if the discard
        pile card would improve your hand.

        Important: If you draw from the discard pile, remember the
        card (e.g., save view.top_of_discard) so you don't try to
        discard it — that's an illegal move!
        """
        # --- Your strategy here ---

        # if there is no card on discard, then draw from deck
        if view.top_of_discard is None:
            self._drew_from_discard = None
            return "deck"

        discard_card = view.top_of_discard
        melds = get_best_melds(view.hand)
        unmelds = get_unmelded_cards(view.hand)

        unmelds.sort()
        # print(f"sorted unmelds: {unmelds}")
        # print(f"discard card: {discard_card}")
        # determine if card in discard completes set
        ranks_left = []
        doubles = []
        for card in unmelds:
            # print(card)
            if card.rank in ranks_left:
                doubles.append(card.rank)
            ranks_left.append(card.rank)

        if discard_card.rank in doubles:
            # print("DRAW FROM DISCARD TO MAKE SET")
            self._drew_from_discard = view.top_of_discard
            return "discard"

        # determine if card in discard creates run
        prev_card = unmelds[0]
        possible_melds = []

        for card in unmelds:
            if card.suit == prev_card.suit and card != prev_card:
                if abs(card.rank.value - prev_card.rank.value) < 3:
                    possible_melds.append([card, prev_card])
            prev_card = card

        for possible_run in possible_melds:
            possible_run.sort()
            if possible_run[0].suit == discard_card.suit:
                if (possible_run[0].rank.value + 1 == discard_card.rank.value) and (possible_run[1].rank.value - 1 == discard_card.rank.value):
                    # print("DRAW FROM DISCARD TO MAKE RUN")
                    self._drew_from_discard = discard_card
                    return "discard"
                elif (possible_run[0].rank.value + 1 == possible_run[1].rank.value) and (possible_run[1].rank.value + 1 == discard_card.rank.value):
                    # print("DRAW FROM DISCARD TO MAKE RUN")
                    self._drew_from_discard = discard_card
                    return "discard"

        # take cards to add to set or run
        for meld in melds[0]:
            meld.sort()
            # print(f"Meld: {meld}")
            # print(f"Meld one rank: {meld[0]}")
            if meld[0].rank == meld[1].rank:
                if discard_card.rank == meld[0].rank:
                    self._drew_from_discard = discard_card
                    # print("TAKE TO ADD TO SET")
                    # print(f"Meld: {meld}")
                    # print(f"Discard: {discard_card}")
                    return "discard"
            if discard_card.suit == meld[0].suit:
                if (discard_card.rank.value == meld[0].rank.value - 1) or (discard_card.rank.value == meld[-1].rank.value + 1):
                    self._drew_from_discard = discard_card
                    # print("TAKE TO ADD TO RUN")
                    # print(f"Meld: {meld}")
                    # print(f"Discard: {discard_card}")
                    return "discard"

        discarded_cards = view.discard_pile

        # grab card if it completes a possible meld with two cards
        for card in unmelds:
            if card.suit == discard_card.suit:
                if abs(card.rank.value - discard_card.rank.value) == 1:
                    possible_meld = [card, discard_card]
                    possible_meld.sort()
                    yes = 0
                    if possible_meld[0].rank.value > 3 and possible_meld[0].rank.value < 7:
                        self._drew_from_discard = discard_card
                        for discard in discarded_cards:
                            if discard == discard_card:
                                continue
                            elif discard.suit == possible_meld[0].suit:
                                if (discard.rank.value == possible_meld[0].rank.value - 1) or (discard.rank.value == possible_meld[1].rank.value + 1):
                                    yes += 1

                    if yes == 0:
                        self._drew_from_discard = discard_card
                        return "discard"

        # grab card if its rank matches one of the ranks in my hand
        for card in unmelds:
            if card.rank == discard_card.rank and card.rank.value < 7:
                possible_meld = [card, discard_card]
                possible_meld.sort()
                yes = 0
                for discard in discarded_cards:
                    if discard == discard_card:
                        continue
                    elif discard.rank == card.rank:
                        yes += 1
                if yes == 0:
                    self._drew_from_discard = discard_card
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
        # Example: discard the card that minimizes deadwood

        discarded_cards = view.discard_pile

        discard_rank = []
        for card in discarded_cards:
            discard_rank.append(card.rank)

        unmelds = get_unmelded_cards(view.hand)

        # if we have no unmelds, then remove best discard
        if len(unmelds) == 0:
            return best_discard(view.hand)

        # remove card that we drew discard
        exclude = self._drew_from_discard
        if exclude in unmelds:
            unmelds.remove(exclude)
        unmelds.sort()

        # find the near melds
        near_melds = []
        unmelds.sort()
        # print(f"final unmelds: {unmelds}")

        # find cards that have same rank
        for card in unmelds:
            for card_2 in unmelds:
                if card_2.rank == card.rank and card != card_2 and card.rank.value < 8:
                    if card_2 not in near_melds:
                        near_melds.append(card_2)
                    if card not in near_melds:
                        near_melds.append(card)

        # find possible runs
        for i in range(len(unmelds) - 1):
            card = unmelds[i]
            card_2 = unmelds[i + 1]
            if abs(card.rank.value - card_2.rank.value) == 1 and card.suit == card_2.suit:
                if card_2.rank.value < 8 and card.rank.value > 3:
                    if card_2 not in near_melds:
                        near_melds.append(card_2)
                    if card not in near_melds:
                        near_melds.append(card)

        # make new list of unmelds that are not possible melds
        new_unmelds = []
        for card in unmelds:
            if card not in near_melds:
                new_unmelds.append(card)

        # return best discard from the new list of unmelds
        if len(new_unmelds) == 0:
            return best_discard(unmelds)

        return best_discard(new_unmelds)


        # discarded_cards = view.discard_pile

        # discard_rank = []
        # for card in discarded_cards:
        #     discard_rank.append(card.rank)

        # unmelds = get_unmelded_cards(view.hand)
        # unmelds.sort()

        # # Check to see if we have any pairs
        # ranks_left = []
        # doubles = []
        # new_hand = []
        # for card in unmelds:
        #     # print(card)
        #     if card.rank in ranks_left:
        #         doubles.append(card)
        #         # if this pair already has a card that has been discarded, allow it to get discarded
        #         if card.rank in discard_rank:
        #             new_hand.append(card)
        #     ranks_left.append(card.rank)

        # exclude = self._drew_from_discard
        # if exclude in unmelds:
        #     unmelds.remove(exclude)
        # # go though all cards again, and if it is not in a double, then add it so it can get discarded
        # for card in unmelds:
        #     if card not in doubles:
        #         new_hand.append(card)
        #     elif card.rank.value == 10 and card != exclude:
        #         return card

        # if exclude in new_hand:
        #     new_hand.remove(exclude)

        # # print(f"Number in Hand: {len(new_hand)}")
        # melds = get_best_melds(view.hand)
        # # print(f"melds: {melds}")
        # if len(new_hand) == 0:
        #     # print("length is 0")
        #     # print(view.hand)
        #     # print(f"Unmelds: {unmelds}")
        #     for meld in melds[0]:
        #         if len(meld) == 4:
        #             meld.sort()
        #             # print(f"Meld that has length four {meld}")
        #             # print(f"Discard {meld[-1]}")
        #             return meld[-1]

        # return best_discard(new_hand)


    def knock_decision(self, view: PlayerView) -> bool:
        """Decide whether to knock (called when deadwood <= 10).

        Tip: Knocking with very low deadwood is safer. Knocking
        with high deadwood (close to 10) risks being undercut.
        """
        # --- Your strategy here ---
        deadwood = calculate_deadwood(view.hand)
        strength = calculate_hand_strength(view.hand)

        if is_gin(view.hand):
            return True
        elif strength > 0.7:
            return True
        elif deadwood < 5:
            return True
        elif deadwood < 7 and view.deck_size < 12:
            return True
        elif view.deck_size < 6:
            return True
        return False