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
    get_best_melds,
    can_knock
)


class MyBot(Bot):
    """Your custom Gin Rummy bot!

    Implement your strategy by modifying the three methods below.
    You can also override on_game_start() and on_turn_end() to
    track game state between turns.
    """

    @property
    def name(self) -> str:
        # Give your bot a name!
        return "wwjd"

    def on_game_start(self, player_id, starting_player):
        self._drew_from_discard = None

    def draw_decision(self, view: PlayerView) -> str:
        #strat
        #1. make sure discard deck isnt empty
        #2. if taking it reduces dw or makes meld, take it
        #* make sure it doesnt discard a card from discard pile
        if view.top_of_discard is None:
            self._drew_from_discard = None
            return "deck"

        current_dw = calculate_deadwood(view.hand)
        if_take = evaluate_discard_draw(view.hand, view.top_of_discard)

        if if_take < current_dw:
            self._drew_from_discard = view.top_of_discard
            return "discard"

        # if i draw from deck, its ok to drop)
        self._drew_from_discard = None

        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        #strat: identify melds, if a card is in a meld dont consider it, discard royal
        melds, unmelded = get_best_melds(view.hand)
        candidates = unmelded if unmelded else view.hand

        # used ai, how to make card rank into a value that i can compare to an int
        def get_n(c): return c.rank.value

        # sorting my cards by rank value, prioritizing looking at higher ranked cards
        candidates.sort(key=get_n, reverse=True)

        # getting cardvalue for each card in hand
        for card in candidates:
            cardvalue = get_n(card)

            # look specifically at royals
            if cardvalue >= 10:
                # checking what are the near melds --> similar rank, nearby numbers
                # needed ai help here
                near_meld = any(
                    (card.rank == other.rank or
                     (card.suit == other.suit and abs(cardvalue - get_n(other)) <= 2))
                    for other in view.hand if card != other
                )

                if not near_meld:
                    return card

        # dont drop discard
        choices = view.hand
        if self._drew_from_discard is not None:
            choices = [c for c in choices if c != self._drew_from_discard]

        #cant discard any lonely royals? just discard best discard card man
        return best_discard(view.hand)

    def knock_decision(self, view: PlayerView) -> bool:
        #strat: to avoid undercut, be conservative and only knock at 5
        if can_knock(view.hand):
            if calculate_deadwood(view.hand) <= 5:
                return True
        return False
