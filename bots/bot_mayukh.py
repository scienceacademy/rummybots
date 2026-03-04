from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
    deadwood_after_discard,
)

class StudentBot(Bot):
    def __init__(self):
        super().__init__()
        self._drew_from_discard = None
        self.opponent_picked = []
        self.last_discard_len = 0
        self.last_top = None

    @property
    def name(self) -> str:
        return "mayukh"

    def on_game_start(self, player_index, view):
        self._drew_from_discard = None
        self.opponent_picked = []
        self.last_discard_len = 0
        self.last_top = None

    def on_turn_end(self, view: PlayerView):
        self.last_discard_len = len(view.discard_pile)
        self.last_top = view.top_of_discard

    def draw_decision(self, view: PlayerView) -> str:
        current_len = len(view.discard_pile)
        if current_len == self.last_discard_len and self.last_top is not None:
            self.opponent_picked.append(self.last_top)
        if not view.top_of_discard:
            return "deck"
        current_dw = calculate_deadwood(view.hand)
        if_take = evaluate_discard_draw(view.hand, view.top_of_discard)
        improvement = current_dw - if_take
        if if_take <= 2 or improvement >= 5:
            self._drew_from_discard = view.top_of_discard
            return "discard"
        if view.deck_size < 12 and improvement >= 2:
            self._drew_from_discard = view.top_of_discard
            return "discard"
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        choices = view.hand
        if self._drew_from_discard is not None:
            choices = [c for c in choices if c != self._drew_from_discard]
        if not choices:
            return view.hand[0]
        min_dw = min(deadwood_after_discard(view.hand, c) for c in choices)
        candidates = [c for c in choices if deadwood_after_discard(view.hand, c) == min_dw]
        def danger_score(card):
            score = 0
            for p in self.opponent_picked:
                if p.rank == card.rank:
                    score += 2
                if p.suit == card.suit and abs(p.rank.value - card.rank.value) == 1:
                    score += 1
            return score
        return min(candidates, key=danger_score)

    def knock_decision(self, view: PlayerView) -> bool:
        dw = calculate_deadwood(view.hand)
        if dw == 0:
            return True
        if dw <= 3:
            return True
        if view.deck_size < 8 and dw <= 6:
            return True
        return False