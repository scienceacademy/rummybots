from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    is_gin,
    can_knock,
    deadwood_after_discard,
    evaluate_discard_draw,
    score_discard_safety,
    count_meld_outs,
    calculate_hand_strength,
)


class jillian(Bot):

    def __init__(self):
        self._drew_from_discard = None

    @property
    def name(self) -> str:
        return "jillian"

    def on_game_start(self, player_index, view):
        self._drew_from_discard = None

    def draw_decision(self, view: PlayerView) -> str:
        self._drew_from_discard = None

        if view.top_of_discard is None:
            return "deck"

        current_deadwood = calculate_deadwood(view.hand)
        deadwood_if_taken = evaluate_discard_draw(
            view.hand, view.top_of_discard
        )

        if deadwood_if_taken < current_deadwood:
            self._drew_from_discard = view.top_of_discard
            return "discard"

        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        seen_cards = set(view.hand + view.discard_pile)

        candidates = view.hand
        if self._drew_from_discard is not None:
            candidates = [
                c for c in view.hand if c != self._drew_from_discard
            ]

        worst_card = None
        worst_score = float("-inf")

        for card in candidates:

            dw_after = deadwood_after_discard(view.hand, card)

            outs = count_meld_outs(card, view.hand, seen_cards)

            safety = score_discard_safety(
                card, view.discard_pile, seen_cards
            )

            score = (
                dw_after * 2
                - outs * 3
                - safety * 2
            )

            if score > worst_score:
                worst_score = score
                worst_card = card

        return worst_card

    def knock_decision(self, view: PlayerView) -> bool:
        deadwood = calculate_deadwood(view.hand)

        if is_gin(view.hand):
            return True

        if not can_knock(view.hand):
            return False

        hand_strength = calculate_hand_strength(view.hand)

        if deadwood <= 4:
            return True

        if view.deck_size < 8:
            return True

        if hand_strength > 0.75:
            return True

        return False