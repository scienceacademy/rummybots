from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import calculate_deadwood, evaluate_discard_draw


class LuisBot(Bot):
    def __init__(self):
        super().__init__()
        self.just_drew_from_discard = None
        self.seen_discards = set()

    @property
    def name(self) -> str:
        return "LuisBot"

    def on_game_start(self, player_index: int, view: PlayerView) -> None:
        self.just_drew_from_discard = None
        self.seen_discards = set()

    def on_turn_end(self, view: PlayerView) -> None:
        if hasattr(view, 'discard_pile'):
            for card in view.discard_pile:
                self.seen_discards.add(card)

    def draw_decision(self, view: PlayerView) -> str:
        top_discard = view.top_of_discard if hasattr(
            view, 'top_of_discard') else None
        if not top_discard and hasattr(view, 'discard_pile') and view.discard_pile:
            top_discard = view.discard_pile[-1]

        if not top_discard:
            self.just_drew_from_discard = None
            return "deck"

        helps_hand = False
        for card in view.hand:
            if card.rank == top_discard.rank:
                helps_hand = True
            elif card.suit == top_discard.suit and abs(card.rank.value - top_discard.rank.value) <= 2:
                helps_hand = True

        current_dw = calculate_deadwood(view.hand)
        dw_if_taken = evaluate_discard_draw(view.hand, top_discard)

        if dw_if_taken < current_dw - 2 or (helps_hand and top_discard.rank.value <= 7):
            self.just_drew_from_discard = top_discard
            return "discard"

        self.just_drew_from_discard = None
        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        valid_discards = []

        for card in view.hand:
            if self.just_drew_from_discard:
                if card.rank == self.just_drew_from_discard.rank and card.suit == self.just_drew_from_discard.suit:
                    continue
            valid_discards.append(card)

        if not valid_discards:
            valid_discards = view.hand

        best_card = valid_discards[0]
        best_score = -float('inf')

        for card in valid_discards:
            temp_hand = list(view.hand)
            temp_hand.remove(card)

            dw = calculate_deadwood(temp_hand)

            score = -dw

            rank_seen_count = sum(
                1 for c in self.seen_discards if c.rank == card.rank)
            score += (rank_seen_count * 3)

            if card.rank.value >= 10:
                score += 0.5

            if score > best_score:
                best_score = score
                best_card = card

        self.just_drew_from_discard = None
        return best_card

    def knock_decision(self, view: PlayerView) -> bool:
        current_deadwood = calculate_deadwood(view.hand)
        return current_deadwood <= 10
