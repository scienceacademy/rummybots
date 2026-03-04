from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    can_knock,
    score_discard_safety,
    calculate_hand_strength,
    count_near_melds,
)

class ParkBot(Bot):
    def __init__(self):
        super().__init__()
        self.drew_from_discard = None

    @property
    def name(self) -> str:
        return "ParkBot"

    def on_game_start(self, player_index, view: PlayerView):
        self.drew_from_discard = None

    def _best_discard_after_take(self, hand_with_card, cannot_discard: Card | None, view: PlayerView):
        best = None
        for c in hand_with_card:
            if cannot_discard is not None and c == cannot_discard:
                continue
            after = [x for x in hand_with_card if x != c]
            dw = calculate_deadwood(after)
            strength = calculate_hand_strength(after)
            near = count_near_melds(after)
            safety = score_discard_safety(c, view.discard_pile, set(after + view.discard_pile))
            key = (dw, -near, -strength, -safety)
            if best is None or key < best[0]:
                best = (key, c)
        return best

    def draw_decision(self, view: PlayerView) -> str:
        top = view.top_of_discard
        if top is None:
            self.drew_from_discard = None
            return "deck"

        hand = view.hand
        now_dw = calculate_deadwood(hand)

        take_eval = self._best_discard_after_take(hand + [top], cannot_discard=top, view=view)
        if take_eval is None:
            self.drew_from_discard = None
            return "deck"

        take_dw = take_eval[0][0]
        take_strength = calculate_hand_strength([x for x in (hand + [top]) if x != take_eval[1]])
        now_strength = calculate_hand_strength(hand)

        if take_dw <= now_dw - 1:
            self.drew_from_discard = top
            return "discard"

        if (take_strength >= now_strength + 0.06) and (take_dw <= now_dw + 1):
            self.drew_from_discard = top
            return "discard"

        self.drew_from_discard = None
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        hand = view.hand
        candidates = [c for c in hand if c != self.drew_from_discard]
        if not candidates:
            return best_discard(hand)

        seen_base = set(view.discard_pile)

        best = None
        for c in candidates:
            after = [x for x in hand if x != c]
            dw = calculate_deadwood(after)
            strength = calculate_hand_strength(after)
            near = count_near_melds(after)
            safety = score_discard_safety(c, view.discard_pile, set(after) | seen_base)
            key = (dw, -near, -strength, -safety)
            if best is None or key < best[0]:
                best = (key, c)

        return best[1]

    def knock_decision(self, view: PlayerView) -> bool:
        if not can_knock(view.hand):
            return False

        dw = calculate_deadwood(view.hand)
        strength = calculate_hand_strength(view.hand)

        if dw <= 6:
            return True

        if strength >= 0.72 and dw <= 8:
            return True

        if view.deck_size <= 10 and dw <= 10:
            return True

        return False