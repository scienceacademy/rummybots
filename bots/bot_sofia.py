from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    get_melds,
    best_discard,
    card_deadwood_contribution,
)

class StudentBot(Bot):
    @property
    def name(self) -> str:
        return "SofiaBot"

    def draw_decision(self, view: PlayerView) -> str:
        if view.top_of_discard is None:
            return "deck"

        melds_with = get_melds(view.hand + [view.top_of_discard])
        melds_without = get_melds(view.hand)

        if len(melds_with) > len(melds_without):
            return "discard"

        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        melds = get_melds(view.hand)
        meld_cards = set(card for meld in melds for card in meld)

        candidates = [c for c in view.hand if c not in meld_cards]
        if not candidates:
            candidates = view.hand

        return max(
            candidates,
            key=lambda c: card_deadwood_contribution(view.hand, c)
        )

    def knock_decision(self, view: PlayerView) -> bool:
        return calculate_deadwood(view.hand) <= 10
