from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    evaluate_discard_draw,
    deadwood_after_discard,
    can_knock,
    is_gin,
    card_deadwood_contribution,
    count_meld_outs,
    score_discard_safety,
    calculate_hand_strength,
)


class ethan_bot(Bot):

    @property
    def name(self) -> str:
        return "ethan_bot"

    def __init__(self):
        self._drew_from_discard = None
        self._turn_count = 0
        self._seen_opponent_picks = set()

    def on_game_start(self, player_index, view):
        self._drew_from_discard = None
        self._turn_count = 0
        self._seen_opponent_picks.clear()

    def draw_decision(self, view: PlayerView) -> str:
        self._turn_count += 1
        self._drew_from_discard = None

        if view.top_of_discard is None:
            return "deck"

        current_dw = calculate_deadwood(view.hand)
        new_dw = evaluate_discard_draw(view.hand, view.top_of_discard)
        seen = set(view.hand + view.discard_pile)
        discard_safety = score_discard_safety(view.top_of_discard, view.discard_pile, seen)
        potential_gain = current_dw - new_dw

        if potential_gain > 0 or discard_safety >= 3:
            self._drew_from_discard = view.top_of_discard
            return "discard"

        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        seen = set(view.hand + view.discard_pile)
        candidates = list(view.hand)

        if self._drew_from_discard is not None:
            candidates = [c for c in candidates if c != self._drew_from_discard]

        best_score = float("-inf")
        best_card = candidates[0]

        hand_strength = calculate_hand_strength(view.hand)

        for card in candidates:
            new_dw = deadwood_after_discard(view.hand, card)
            contribution = card_deadwood_contribution(view.hand, card)
            outs = count_meld_outs(card, view.hand, seen)
            safety = score_discard_safety(card, view.discard_pile, seen)

            if self._turn_count <= 5:
                score = -new_dw * 3 + outs * 3 + safety * 6 + contribution * 1.5
            else:
                score = -new_dw * 5 + outs * 3 + safety * 4 + contribution * 1.5

            if card.rank.value >= 10 and self._turn_count > 5:
                score += 5

            if self._turn_count <= 3 and card.rank.value <= 5:
                score -= 2

            if card in self._seen_opponent_picks:
                score -= 4

            if hand_strength > 0.85:
                score -= outs * 2

            if score > best_score:
                best_score = score
                best_card = card

        return best_card

    def knock_decision(self, view: PlayerView) -> bool:
        deadwood = calculate_deadwood(view.hand)

        if is_gin(view.hand):
            return True

        if not can_knock(view.hand):
            return False

        hand_strength = calculate_hand_strength(view.hand)

        if self._turn_count <= 3 and deadwood <= 7:
            return True

        if deadwood <= 5 or hand_strength > 0.85:
            return True

        if view.deck_size <= 6 and deadwood <= 10:
            return True

        return False

    def on_opponent_draw(self, card: Card):
        self._seen_opponent_picks.add(card)