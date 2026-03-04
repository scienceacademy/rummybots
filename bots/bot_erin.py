from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    can_knock,
    evaluate_discard_draw,
    deadwood_after_discard,
    get_best_melds,
    best_discard,
)


class ErinBot(Bot):

    @property
    def name(self):
        return "ErinBot"

    def __init__(self):
        self._drew_from_discard = None

    def on_game_start(self, player_index, view):
        self._drew_from_discard = None

    def draw_decision(self, view):
        top = view.top_of_discard
        if top is None:
            return "deck"

        current_dw = calculate_deadwood(view.hand)
        new_dw = evaluate_discard_draw(view.hand, top)

        if new_dw < current_dw:
            self._drew_from_discard = top
            return "discard"

        return "deck"

    def discard_decision(self, view):
        melds, unmelded = get_best_melds(view.hand)

        best_card_choice = None
        best_score = float("-inf")

        for card in view.hand:

            if card == self._drew_from_discard:
                continue

            temp_hand = [c for c in view.hand if c != card]
            new_melds, new_unmelded = get_best_melds(temp_hand)

            new_deadwood = calculate_deadwood(temp_hand)

            meld_score = len(new_melds) * 12
            unmelded_score = -len(new_unmelded) * 4
            deadwood_score = -new_deadwood * 2

            if card not in unmelded:
                meld_score -= 15

            same_rank_count = sum(1 for c in temp_hand if c.rank == card.rank)
            if same_rank_count >= 1:
                meld_score += 3

            score = meld_score + unmelded_score + deadwood_score

            if score > best_score:
                best_score = score
                best_card_choice = card

        if best_card_choice is None:
            best_card_choice = best_discard(view.hand)

        self._drew_from_discard = None
        return best_card_choice

    def knock_decision(self, view):
        if not can_knock(view.hand):
            return False

        deadwood = calculate_deadwood(view.hand)

        if deadwood == 0:
            return True

        if deadwood <= 3:
            return True

        if view.opponent_hand_size <= 2:
            return True

        if view.deck_size <= 5:
            return True

        if deadwood <= 6 and view.deck_size < 10:
            return True

        return False