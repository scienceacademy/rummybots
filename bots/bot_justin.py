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
    can_knock,
    card_deadwood_contribution,
    count_meld_outs,
    count_near_melds,
    deadwood_after_discard,
    evaluate_discard_draw,
    get_best_melds,
    get_unmelded_cards,
    is_gin,
    is_provably_safe_discard,
    score_discard_safety,
    calculate_hand_strength,
)

class bot_justin(Bot):
    def __init__(self) -> None:
        self._drew_from_discard: Card | None = None
        self._seen_cards: set[Card] = set()

    @property
    def name(self) -> str:
        return "bot_justin"

    # ---- Lifecycle ---------------------------------------------------------

    def on_game_start(self, player_index: int, view: PlayerView) -> None:
        self._drew_from_discard = None
        self._seen_cards = set(view.hand) | set(view.discard_pile)

    def on_turn_end(self, view: PlayerView) -> None:
        # We only reliably "see" our hand and the discard history.
        # Treat those as seen for outs / safety heuristics.
        self._seen_cards = set(view.hand) | set(view.discard_pile)
        self._drew_from_discard = None  # reset each turn

    # ---- Helpers -----------------------------------------------------------

    @staticmethod
    def _would_be_in_meld(hand: list[Card], add_card: Card) -> bool:
        melds, _unmelded = get_best_melds(hand + [add_card])
        for meld in melds:
            if add_card in meld:
                return True
        return False

    @staticmethod
    def _near_meld_boost(hand: list[Card], add_card: Card) -> int:
        # Compare "one-away" structure before/after adding the card.
        before = count_near_melds(hand)
        after = count_near_melds(hand + [add_card])
        return after - before

    # ---- Decisions ---------------------------------------------------------

    def draw_decision(self, view: PlayerView) -> str:
        # --- Your strategy here ---
        # Example: always draw from the deck (safe but basic)
        top = view.top_of_discard
        if top is None:
            return "deck"

        current_dw = calculate_deadwood(view.hand)
        if_take_dw = evaluate_discard_draw(view.hand, top)
        dw_drop = current_dw - if_take_dw

        # Strong reasons to take:
        # 1) It completes/joins a meld in the optimal arrangement.
        completes_meld = self._would_be_in_meld(view.hand, top)

        # 2) It meaningfully improves the hand by deadwood.
        meaningful_deadwood_gain = dw_drop >= 2  # avoid revealing info for tiny gain

        # 3) It improves near-meld structure / hand strength noticeably.
        near_boost = self._near_meld_boost(view.hand, top)
        strength_before = calculate_hand_strength(view.hand)
        strength_after = calculate_hand_strength(view.hand + [top])
        strength_gain = strength_after - strength_before

        # 4) Late in the deck, be a bit more willing to lock improvements.
        late_game = view.deck_size <= 14

        take = (
            completes_meld
            or meaningful_deadwood_gain
            or (near_boost >= 1 and strength_gain >= 0.05)
            or (late_game and dw_drop >= 1)
        )

        if take:
            self._drew_from_discard = top
            return "discard"
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
         # --- Your strategy here ---
        # Example: discard the card that minimizes deadwood
        legal_cards = list(view.hand)
        if self._drew_from_discard is not None:
            legal_cards = [c for c in legal_cards if c != self._drew_from_discard]
            # Fallback safety: if something went weird, still return a valid card.
            if not legal_cards:
                return best_discard(view.hand)

        legal_cards.sort(
            key=lambda c: (
                c.deadwood_value,
                card_deadwood_contribution(view.hand, c),
            ),
            reverse=True,
        )
        return legal_cards[0] if legal_cards else best_discard(view.hand)

    def knock_decision(self, view: PlayerView) -> bool:
        #No need to knock
        return is_gin(view.hand)

#Help of Narek and ai