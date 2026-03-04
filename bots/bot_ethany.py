from __future__ import annotations

from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    deadwood_after_discard,
    evaluate_discard_draw,
    get_unmelded_cards,
    is_gin,
)


class EthanyBot(Bot):
    def __init__(self):
        self._took_discard_this_turn: bool = False
        self._discard_card_taken: Card | None = None

    @property
    def name(self) -> str:
        return "EthanyBot"

    def on_turn_end(self, view: PlayerView) -> None:
        self._took_discard_this_turn = False
        self._discard_card_taken = None

    def draw_decision(self, view: PlayerView) -> str:
        top = view.top_of_discard
        if top is None:
            return "deck"

        current_deadwood = calculate_deadwood(view.hand)
        best_deadwood_if_take = evaluate_discard_draw(view.hand, top)

        if best_deadwood_if_take < current_deadwood:
            self._took_discard_this_turn = True
            self._discard_card_taken = top
            return "discard"

        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        hand = list(view.hand)

        illegal = self._took_discard_this_turn and (self._discard_card_taken is not None)

        candidates = list(get_unmelded_cards(hand))
        if not candidates:
            candidates = hand[:]

        best_card = None
        best_score = float("inf")

        for c in candidates:
            if illegal and (c is self._discard_card_taken):
                continue
            score = deadwood_after_discard(hand, c)
            if score < best_score:
                best_score = score
                best_card = c

        if best_card is None:
            c = best_discard(view.hand)
            if illegal and (c is self._discard_card_taken):
                for alt in hand:
                    if alt is not self._discard_card_taken:
                        return alt
            return c

        return best_card

    def knock_decision(self, view: PlayerView) -> bool:
        if is_gin(view.hand):
            return True

        deadwood = calculate_deadwood(view.hand)
        deck_size = getattr(view, "deck_size", 20)

        if deck_size > 18:
            return deadwood <= 2
        if deck_size > 12:
            return deadwood <= 3
        if deck_size > 8:
            return deadwood <= 4
        return deadwood <= 6
