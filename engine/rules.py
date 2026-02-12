"""Gin Rummy rule validation, meld detection, and scoring."""

from collections import defaultdict
from functools import lru_cache
from itertools import combinations
from typing import List, Tuple

from engine.card import Card


# Type alias for a meld (a group of cards forming a set or run)
Meld = List[Card]


def is_valid_set(cards: List[Card]) -> bool:
    """Check if cards form a valid set (3-4 cards of the same rank)."""
    if len(cards) not in (3, 4):
        return False
    ranks = {c.rank for c in cards}
    suits = {c.suit for c in cards}
    return len(ranks) == 1 and len(suits) == len(cards)


def is_valid_run(cards: List[Card]) -> bool:
    """Check if cards form a valid run (3+ consecutive same suit)."""
    if len(cards) < 3:
        return False
    suits = {c.suit for c in cards}
    if len(suits) != 1:
        return False
    values = sorted(c.rank.value for c in cards)
    for i in range(1, len(values)):
        if values[i] != values[i - 1] + 1:
            return False
    return True


def is_valid_meld(cards: List[Card]) -> bool:
    """Check if cards form a valid meld (set or run)."""
    return is_valid_set(cards) or is_valid_run(cards)


def find_sets(hand: List[Card]) -> List[Meld]:
    """Find all possible sets (3-4 of same rank) in a hand."""
    by_rank = defaultdict(list)
    for card in hand:
        by_rank[card.rank].append(card)

    sets = []
    for rank, cards in by_rank.items():
        if len(cards) >= 3:
            # Add 3-card sets
            for combo in combinations(cards, 3):
                sets.append(list(combo))
            # Add 4-card set if possible
            if len(cards) == 4:
                sets.append(list(cards))
    return sets


def find_runs(hand: List[Card]) -> List[Meld]:
    """Find all possible runs (3+ consecutive same suit) in a hand."""
    by_suit = defaultdict(list)
    for card in hand:
        by_suit[card.suit].append(card)

    runs = []
    for suit, cards in by_suit.items():
        sorted_cards = sorted(cards, key=lambda c: c.rank.value)
        values = [c.rank.value for c in sorted_cards]

        # Find all consecutive sequences of length >= 3
        for start in range(len(sorted_cards)):
            for end in range(start + 3, len(sorted_cards) + 1):
                subseq = sorted_cards[start:end]
                subvals = values[start:end]
                # Check consecutive
                is_consecutive = all(
                    subvals[i] == subvals[i - 1] + 1
                    for i in range(1, len(subvals))
                )
                if is_consecutive:
                    runs.append(subseq)
    return runs


def find_all_melds(hand: List[Card]) -> List[Meld]:
    """Find all possible melds (sets and runs) in a hand."""
    return find_sets(hand) + find_runs(hand)


def _find_best_melds_recursive(
    remaining: List[Card],
    all_melds: List[Meld],
    current_melds: List[Meld],
    best: List[List[Meld]],
    best_deadwood: List[int],
    start_idx: int = 0,
) -> None:
    """Recursively find the combination of non-overlapping melds
    that minimizes deadwood."""
    remaining_set = set(remaining)
    current_dw = sum(c.deadwood_value for c in remaining_set)

    if current_dw < best_deadwood[0]:
        best_deadwood[0] = current_dw
        best[0] = list(current_melds)

    # Only consider melds at or after start_idx to avoid
    # exploring the same combination in different orderings.
    for i in range(start_idx, len(all_melds)):
        meld = all_melds[i]
        meld_set = set(meld)
        if meld_set.issubset(remaining_set):
            new_remaining = [c for c in remaining if c not in meld_set]
            _find_best_melds_recursive(
                new_remaining,
                all_melds,
                current_melds + [meld],
                best,
                best_deadwood,
                start_idx=i + 1,
            )


@lru_cache(maxsize=1024)
def _find_best_melds_cached(hand_tuple: Tuple[Card, ...]) -> Tuple[Tuple[Tuple[Card, ...], ...], Tuple[Card, ...]]:
    """Cached version of find_best_melds using tuples for hashability.

    Args:
        hand_tuple: Tuple of cards (sorted for cache consistency)

    Returns:
        Tuple of (melds_tuple, unmelded_tuple) where melds_tuple is a tuple
        of meld tuples and unmelded_tuple is a tuple of unmelded cards.
    """
    hand = list(hand_tuple)
    all_melds = find_all_melds(hand)
    if not all_melds:
        return tuple(), hand_tuple

    best: List[List[Meld]] = [[]]
    best_deadwood = [sum(c.deadwood_value for c in hand)]

    _find_best_melds_recursive(
        list(hand), all_melds, [], best, best_deadwood
    )

    melded_cards: set = set()
    for meld in best[0]:
        melded_cards.update(meld)
    unmelded = [c for c in hand if c not in melded_cards]

    # Convert to tuples for return
    melds_tuple = tuple(tuple(meld) for meld in best[0])
    unmelded_tuple = tuple(unmelded)

    return melds_tuple, unmelded_tuple


def find_best_melds(hand: List[Card]) -> Tuple[List[Meld], List[Card]]:
    """Find the optimal meld arrangement that minimizes deadwood.

    Returns:
        A tuple of (melds, unmelded_cards) where melds is the list
        of melds and unmelded_cards are the leftover cards.
    """
    if not hand:
        return [], []

    # Convert to sorted tuple for cache lookup
    hand_tuple = tuple(sorted(hand, key=lambda c: (c.suit.value, c.rank.value)))

    # Get cached result
    melds_tuple, unmelded_tuple = _find_best_melds_cached(hand_tuple)

    # Convert back to lists
    melds = [list(meld) for meld in melds_tuple]
    unmelded = list(unmelded_tuple)

    return melds, unmelded


# --- Scoring ---

def calculate_deadwood(hand: List[Card]) -> int:
    """Calculate the minimum deadwood points for a hand.

    Finds the optimal meld arrangement and returns the sum of
    deadwood values for unmelded cards.
    """
    _, unmelded = find_best_melds(hand)
    return sum(c.deadwood_value for c in unmelded)


def is_gin(hand: List[Card]) -> bool:
    """Check if a hand is gin (0 deadwood)."""
    return calculate_deadwood(hand) == 0


def can_knock(hand: List[Card]) -> bool:
    """Check if a hand can knock (deadwood <= 10)."""
    return calculate_deadwood(hand) <= 10


def score_hand(
    knocker_hand: List[Card],
    defender_hand: List[Card],
    is_gin: bool = False,
) -> Tuple[int, str]:
    """Score a completed hand after a knock or gin (without layoffs).

    NOTE: This function does NOT apply layoffs. The game engine uses
    ``score_with_layoffs()`` instead, which gives the defender credit
    for laying off unmelded cards onto the knocker's melds. Use this
    only if you want a raw score comparison without layoff handling.

    Args:
        knocker_hand: The hand of the player who knocked/ginned.
        defender_hand: The hand of the other player.
        is_gin: Whether the knocker achieved gin.

    Returns:
        A tuple of (points, result_type) where points is positive
        if the knocker wins and negative if undercut.
        result_type is one of: "gin", "knock", "undercut".
    """
    knocker_dw = calculate_deadwood(knocker_hand)
    defender_dw = calculate_deadwood(defender_hand)

    if is_gin:
        # Gin bonus: 25 points + defender's deadwood
        return defender_dw + 25, "gin"

    if defender_dw <= knocker_dw:
        # Undercut: defender gets bonus of 25 + difference
        diff = knocker_dw - defender_dw
        return -(diff + 25), "undercut"

    # Normal knock: knocker gets the difference
    return defender_dw - knocker_dw, "knock"


# --- Layoffs ---

def can_lay_off(card: Card, meld: Meld) -> bool:
    """Check if a card can be laid off onto an existing meld."""
    extended = list(meld) + [card]
    return is_valid_set(extended) or is_valid_run(extended)


def apply_layoffs(
    knocker_melds: List[Meld], defender_unmelded: List[Card]
) -> List[Card]:
    """Automatically lay off defender's unmelded cards onto knocker's melds.

    Modifies knocker_melds in place. Returns the remaining unmelded cards
    after all possible layoffs.
    """
    remaining = list(defender_unmelded)
    changed = True
    while changed:
        changed = False
        for card in list(remaining):
            for meld in knocker_melds:
                if can_lay_off(card, meld):
                    meld.append(card)
                    remaining.remove(card)
                    changed = True
                    break
    return remaining


def score_with_layoffs(
    knocker_hand: List[Card],
    defender_hand: List[Card],
    is_gin: bool = False,
) -> Tuple[int, str]:
    """Score a completed hand with automatic layoff handling.

    After a knock, the defender's unmelded cards are automatically
    laid off onto the knocker's melds where possible.

    Args:
        knocker_hand: The hand of the player who knocked.
        defender_hand: The hand of the other player.
        is_gin: Whether the knocker achieved gin (no layoffs allowed).

    Returns:
        A tuple of (points, result_type) where points is positive
        if the knocker wins and negative if undercut.
        result_type is one of: "gin", "knock", "undercut".
    """
    knocker_melds, knocker_unmelded = find_best_melds(knocker_hand)
    knocker_dw = sum(c.deadwood_value for c in knocker_unmelded)

    if is_gin:
        defender_dw = calculate_deadwood(defender_hand)
        return defender_dw + 25, "gin"

    # Find defender's own melds first
    _, defender_unmelded = find_best_melds(defender_hand)

    # Lay off defender's unmelded cards onto copies of knocker's melds
    knocker_melds_copy = [list(m) for m in knocker_melds]
    remaining = apply_layoffs(knocker_melds_copy, defender_unmelded)
    defender_dw = sum(c.deadwood_value for c in remaining)

    if defender_dw <= knocker_dw:
        diff = knocker_dw - defender_dw
        return -(diff + 25), "undercut"

    return defender_dw - knocker_dw, "knock"
