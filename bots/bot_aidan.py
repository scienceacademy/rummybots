from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
    is_gin,
    can_knock,
    get_best_melds,
    get_unmelded_cards,
    count_meld_outs,
    is_provably_safe_discard,
    score_discard_safety,
    calculate_hand_strength,
    count_near_melds,
)


class aidanbot(Bot):

    @property
    def name(self) -> str:
        return "aidanbot"

    def on_game_start(self, player_index: int, view: PlayerView) -> None:
        self._drew_from_discard: Card | None = None
        self._opponent_picks: list[Card] = []
        self._last_discard_pile_len: int = 0

    def on_turn_end(self, view: PlayerView) -> None:
        """Detect if the opponent picked from the discard pile this turn."""
        current_len = len(view.discard_pile)
        self._last_discard_pile_len = current_len
        self._drew_from_discard = None

    def draw_decision(self, view: PlayerView) -> str:
        top = view.top_of_discard
        if top is None:
            return "deck"

        current_dw = calculate_deadwood(view.hand)
        projected_dw = evaluate_discard_draw(view.hand, top)
        improvement = current_dw - projected_dw

        if improvement >= 3:
            self._drew_from_discard = top
            return "discard"

        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:

        hand = view.hand
        seen = set(hand) | set(view.discard_pile)

        candidates = [c for c in hand if c != self._drew_from_discard]
        if not candidates:
            candidates = hand

        current_dw = calculate_deadwood(hand)

        def score(card: Card) -> float:
            dw_after = 0
            try:
                from framework.utilities import deadwood_after_discard
                dw_after = deadwood_after_discard(hand, card)
            except Exception:
                dw_after = current_dw
            dw_gain = current_dw - dw_after

            safety = score_discard_safety(card, view.discard_pile, seen)
            safety_norm = max(0.0, min(1.0, (safety + 5) / 10))

            outs = count_meld_outs(card, hand, seen)
            outs_penalty = min(outs, 6) / 6.0

            return 0.55 * dw_gain + 0.25 * safety_norm - 0.20 * outs_penalty

        return max(candidates, key=score)

    def knock_decision(self, view: PlayerView) -> bool:
        dw = calculate_deadwood(view.hand)
        deck = view.deck_size
        strength = calculate_hand_strength(view.hand)

        if dw <= 10:
            if dw == 0:
                return True

            if deck <= 5:
                return True

            if dw <= 3:
                return True

            if dw <= 6:
                return deck <= 15 or strength >= 0.65

            if dw <= 10:
                return deck <= 8

            return False