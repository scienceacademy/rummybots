from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
    deadwood_after_discard,
    card_deadwood_contribution,
    get_unmelded_cards,
    is_gin,
    can_knock,
)


"""Student Bot Template — start building your bot here!

Instructions:
1. Rename this file to something like "bot_<name>.py"
2. Rename the class to something like "MyBot"
3. Implement your strategy in the three required methods
4. Test your bot by running it against the sample bots

Available information in 'view' (a PlayerView object):
- view.hand:              Your current cards (list of Card objects)
- view.discard_pile:      All discarded cards so far (list)
- view.top_of_discard:    The top card of the discard pile (or None)
- view.deck_size:         Number of cards left in the deck
- view.opponent_hand_size: Number of cards in opponent's hand
- view.phase:             Current game phase

Useful utility functions (import from framework.utilities):
- calculate_deadwood(hand)         → Your total deadwood points
- is_gin(hand)                     → True if deadwood is 0
- can_knock(hand)                  → True if deadwood <= 10
- get_melds(hand)                  → All possible melds in your hand
- get_best_melds(hand)             → (melds, unmelded) optimal arrangement
- get_unmelded_cards(hand)         → Cards not part of any meld
- best_discard(hand)               → The card to discard for min deadwood
- deadwood_after_discard(hand, c)  → Deadwood if you discard card c
- evaluate_discard_draw(hand, c)   → Best deadwood if you take card c
- card_deadwood_contribution(hand, c) → How much card c hurts your hand

Strategy ideas to try:
- Take from the discard pile when the card completes a meld
- Track what your opponent discards to avoid giving them useful cards
- Only knock when your deadwood is very low (reduces undercut risk)
- Consider which cards are "near" melds (e.g., two of a kind, partial runs)
- Be more aggressive about knocking when the deck is running low
"""

from engine.card import Card
from engine.game import PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    evaluate_discard_draw,
)


class lilybot(Bot):

    def __init__(self):
        super().__init__()
        self.cannot_discard = None
        self.last_seen_top = None
        self.opponent_likely_took = None

    @property
    def name(self) -> str:
        # Give your bot a name!
        return "lilybot"

    def rank_num(self, c: Card) -> int:

        return c.rank.value if hasattr(c.rank, "value") else int(c.rank)

    def is_high_card(self, c: Card) -> bool:
        return self.rank_num(c) >= 10

    def is_low_card(self, c: Card) -> bool:
        return self.rank_num(c) in (1, 2, 3)

    def run_neighbors(self, c: Card):
        r = self.rank_num(c)
        return [
            (r - 2, c.suit),
            (r - 1, c.suit),
            (r + 1, c.suit),
            (r + 2, c.suit),
    ]

    def run_potential(self, hand, c: Card) -> int:
        count = 0
        rc = self.rank_num(c)
        for x in hand:
            if x == c:
                continue
            rx = self.rank_num(x)
            if x.suit == c.suit and abs(rx - rc) in (1, 2):
                count += 1
        return count

    def set_potential(self, hand, c: Card) -> int:
        count = 0
        rc = self.rank_num(c)
        for x in hand:
            if x == c:
                continue
            if self.rank_num(x) == rc:
                count += 1
        return count

    def has_any_potential(self, hand: list[Card], c: Card) -> bool:
        return (self.run_potential(hand, c) > 0) or (self.set_potential(hand, c) > 0)

    def infer_opponent_pickup(self, view: PlayerView) -> None:
        if self.last_seen_top is None:
            self.opponent_likely_took = None
            return

        if self.last_seen_top not in view.discard_pile:
            self.opponent_likely_took = self.last_seen_top
        else:
            self.opponent_likely_took = None

    def would_help_opponent(self, c: Card) -> bool:

        take = self.opponent_likely_took
        if take is None:
            return False

        if c.rank == take.rank:
            return True

        for (r, s) in self.run_neighbors(take):
            if c.rank == r and c.suit == s:
                return True

        return False

    def discard_score(self, view: PlayerView, hand: list[Card], c: Card) -> float:

        dw_after = deadwood_after_discard(hand, c)
        contrib = card_deadwood_contribution(hand, c)

        early_game = view.deck_size >= 20
        late_game = view.deck_size <= 10

        run_p = self.run_potential(hand, c)
        set_p = self.set_potential(hand, c)

        score = float(dw_after)

        score -= 0.35 * float(contrib)

        score += 3.0 * float(run_p)
        score += 1.0 * float(set_p)


        if self.is_low_card(c):
            score += 2.5


        if early_game and self.is_high_card(c) and (not self.has_any_potential(hand, c)):
            score -= 6.0


        if late_game and self.is_high_card(c) and run_p > 0:
            score += 1.5

        if self.would_help_opponent(c):
            score += 8.0

        return score
    def draw_decision(self, view: PlayerView) -> str:


        self.infer_opponent_pickup(view)

        top = view.top_of_discard
        if top is None:
            return "deck"

        current_dw = calculate_deadwood(view.hand)
        best_dw_if_take = evaluate_discard_draw(view.hand, top)
        improvement = current_dw - best_dw_if_take

        if best_dw_if_take == 0:
            self.cannot_discard = top
            return "discard"

        hand = list(view.hand)
        run_gain = self.run_potential(hand + [top], top)

        early_game = view.deck_size >= 20
        late_game = view.deck_size <= 10

        if early_game:
            if improvement >= 2:
                self.cannot_discard = top
                return "discard"
            if run_gain > 0 and improvement >= 1:
                self.cannot_discard = top
                return "discard"
        else:
            if improvement >= 3:
                self.cannot_discard = top
                return "discard"
            if run_gain > 0 and improvement >= 2:
                self.cannot_discard = top
                return "discard"

        if late_game and improvement <= 1:
            return "deck"

        return "deck"



    def discard_decision(self, view: PlayerView) -> Card:
        hand = list(view.hand)

        candidates = []

        for c in hand:
            if self.cannot_discard is not None and c == self.cannot_discard:
                continue
            candidates.append(c)

        if len(candidates) == 0:
            return best_discard(hand)

        unmelded = set(get_unmelded_cards(hand))
        pool = [c for c in candidates if c in unmelded]
        if len(pool) == 0:
            pool = candidates

        best_card = pool[0]
        best_score = self.discard_score(view, hand, best_card)

        for c in pool[1:]:
            s = self.discard_score(view, hand, c)
            if s < best_score:
                best_score = s
                best_card = c

        return best_card




    def knock_decision(self, view: PlayerView) -> bool:
        if is_gin(view.hand):
            return True

        if not can_knock(view.hand):
            return False

        return True
