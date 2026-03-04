from framework.bot_interface import Bot
from framework.utilities import (
    calculate_deadwood,
    is_gin,
    can_knock,
    get_best_melds,
    get_unmelded_cards,
    best_discard,
    deadwood_after_discard,
    evaluate_discard_draw,
    card_deadwood_contribution,
    count_meld_outs,
    is_provably_safe_discard,
    score_discard_safety,
    calculate_hand_strength,
)


class Eugenebot(Bot):

    @property
    def name(self):
        return "Eugenebot"

    def __init__(self):
        self._drew_from_discard = None
        self._seen_cards = set()

    # -------------------------
    # LIFECYCLE
    # -------------------------

    def on_game_start(self, player_index, view):
        self._drew_from_discard = None
        self._seen_cards = set()

    def on_turn_end(self, view):
        self._seen_cards = set(view.hand + view.discard_pile)

    # -------------------------
    # DRAW DECISION
    # -------------------------

    def draw_decision(self, view):

        self._drew_from_discard = None

        if view.top_of_discard is None:
            return "deck"

        current_dw = calculate_deadwood(view.hand)
        new_dw = evaluate_discard_draw(view.hand, view.top_of_discard)

        # Only take discard if REAL improvement
        if new_dw < current_dw:
            self._drew_from_discard = view.top_of_discard
            return "discard"

        # Take discard if it creates immediate meld
        temp_hand = view.hand + [view.top_of_discard]
        melds, unmelded = get_best_melds(temp_hand)
        if len(unmelded) < len(get_unmelded_cards(view.hand)):
            self._drew_from_discard = view.top_of_discard
            return "discard"

        return "deck"

    # -------------------------
    # DISCARD DECISION
    # -------------------------

    def discard_decision(self, view):

        candidates = list(view.hand)

        if self._drew_from_discard is not None:
            candidates = [c for c in candidates if c != self._drew_from_discard]

        best_card = None
        best_score = float("-inf")

        strength = calculate_hand_strength(view.hand)
        late_game = view.deck_size <= 10

        for card in candidates:

            new_dw = deadwood_after_discard(view.hand, card)
            contribution = card_deadwood_contribution(view.hand, card)
            outs = count_meld_outs(card, view.hand, self._seen_cards)
            safety = score_discard_safety(card, view.discard_pile, self._seen_cards)

            # Core idea:
            # Minimize deadwood
            # Keep high-out cards
            # Avoid unsafe late-game discards

            score = 0

            # Deadwood is primary objective
            score -= new_dw * 8

            # Remove cards that contribute heavily to deadwood
            score += contribution * 3

            # Keep flexible improvement cards
            score -= outs * 5

            # Safety matters more late game
            score += safety * (15 if late_game else 6)

            # Guaranteed safe discard bonus
            if is_provably_safe_discard(card, self._seen_cards):
                score += 12

            # When strong, protect structure
            if strength > 0.8:
                if outs > 0:
                    score -= 8

            if score > best_score:
                best_score = score
                best_card = card

        if best_card is None:
            return best_discard(candidates)

        return best_card

    # -------------------------
    # KNOCK DECISION
    # -------------------------

    def knock_decision(self, view):

        deadwood = calculate_deadwood(view.hand)

        if is_gin(view.hand):
            return True

        if not can_knock(view.hand):
            return False

        strength = calculate_hand_strength(view.hand)
        late_game = view.deck_size <= 10

        # Late game: avoid draw
        if late_game:
            return True

        # Strong hand knock
        if strength > 0.85:
            return True

        # Only knock low deadwood midgame
        if deadwood <= 4:
            return True

        return False
