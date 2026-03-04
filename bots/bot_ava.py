from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    evaluate_discard_draw,
    get_best_melds,
    can_knock,
)


class StudentBot(Bot):

    def __init__(self):
        self.just_drew_discard = None  # Track illegal discard prevention

    @property
    def name(self) -> str:
        return "avabot"

    def draw_decision(self, view: PlayerView) -> str:
        """
        Strategy:
        - Take discard only if it improves deadwood
        - Prefer discard if it helps form runs (same suit sequences)
        """
        top_card = view.top_of_discard

        if top_card is None:
            return "deck"

        current_deadwood = calculate_deadwood(view.hand)
        improved_deadwood = evaluate_discard_draw(view.hand, top_card)

        # Only take discard if it improves hand
        if improved_deadwood < current_deadwood:
            self.just_drew_discard = top_card
            return "discard"

        return "deck"

    def discard_decision(self, view: PlayerView) -> Card:
        """
        Strategy:
        1. Never discard the card just drawn from discard pile
        2. Prefer discarding highest deadwood contribution
        3. Prefer breaking pairs over breaking potential runs
        4. Prefer keeping low cards
        """
        hand = view.hand.copy()

        # Get best meld structure
        melds, unmelded = get_best_melds(hand)

        # Remove illegal discard
        candidates = [
            c for c in hand
            if c != self.just_drew_discard
        ]

        # Sort candidates by:
        # 1. Deadwood contribution (high first)
        # 2. Card rank value (high first)
        # 3. Prefer discarding cards not part of runs
        def discard_priority(card):
            rank_value = min(card.rank.value, 10)

            # Penalize breaking runs (same suit consecutive cards)
            run_bonus = 0
            for other in hand:
                if other == card:
                    continue
                if other.suit == card.suit and abs(other.rank.value - card.rank.value) == 1:
                    run_bonus += 5  # discourage discarding run cards

            return (rank_value + run_bonus)

        candidates.sort(key=discard_priority, reverse=True)

        chosen = candidates[0]

        # Reset discard memory after decision
        self.just_drew_discard = None

        return chosen

    def knock_decision(self, view: PlayerView) -> bool:
        return True
