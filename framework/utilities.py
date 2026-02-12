"""Utility functions to help with bot strategy.

Import these functions in your bot to analyze hands and make decisions.

Example:
    from framework.utilities import calculate_deadwood, find_best_melds

    class MyBot(Bot):
        def knock_decision(self, view):
            deadwood = calculate_deadwood(view.hand)
            return deadwood <= 5  # only knock with low deadwood
"""

from typing import List, Set, Tuple

from engine.card import Card, Rank, Suit
from engine.rules import (
    Meld,
    calculate_deadwood,
    can_knock,
    find_all_melds,
    find_best_melds,
    is_gin,
    is_valid_meld,
)

# All 52 cards in a standard deck (for card counting)
ALL_CARDS = frozenset(
    Card(rank, suit) for suit in Suit for rank in Rank
)


# --- Hand analysis ---

def get_melds(hand: List[Card]) -> List[Meld]:
    """Find all possible melds (sets and runs) in a hand.

    A meld is either:
    - A set: 3-4 cards of the same rank (e.g., 5H, 5D, 5C)
    - A run: 3+ consecutive cards of the same suit (e.g., 3H, 4H, 5H)

    Args:
        hand: List of cards to analyze.

    Returns:
        List of all possible melds found.
    """
    return find_all_melds(hand)


def get_best_melds(hand: List[Card]) -> Tuple[List[Meld], List[Card]]:
    """Find the optimal meld arrangement that minimizes deadwood.

    Args:
        hand: List of cards to analyze.

    Returns:
        A tuple of (melds, unmelded_cards).
    """
    return find_best_melds(hand)


def get_unmelded_cards(hand: List[Card]) -> List[Card]:
    """Get the cards left over after optimal meld arrangement.

    These are the cards contributing to your deadwood score.

    Args:
        hand: List of cards to analyze.

    Returns:
        List of cards not part of any meld.
    """
    _, unmelded = find_best_melds(hand)
    return unmelded


# --- Strategy helpers ---

def deadwood_after_discard(hand: List[Card], card: Card) -> int:
    """Calculate what your deadwood would be after discarding a card.

    Useful for evaluating which card to discard. Call this for each
    card in your hand and discard the one that gives the lowest result.

    Args:
        hand: Your current hand (should have 11 cards after drawing).
        card: The card you're considering discarding.

    Returns:
        The deadwood value of the remaining 10 cards.

    Raises:
        ValueError: If the card is not in the hand.
    """
    remaining = list(hand)
    try:
        remaining.remove(card)
    except ValueError:
        raise ValueError(f"Card {card} is not in the hand")
    return calculate_deadwood(remaining)


def best_discard(hand: List[Card]) -> Card:
    """Find the card whose discard minimizes your deadwood.

    Evaluates every card in the hand and returns the one that,
    when discarded, leaves the lowest deadwood.

    Args:
        hand: Your current hand (should have 11 cards after drawing).

    Returns:
        The Card you should discard for minimum deadwood.
    """
    return min(hand, key=lambda c: deadwood_after_discard(hand, c))


def evaluate_discard_draw(
    hand: List[Card], discard_card: Card
) -> int:
    """Evaluate if taking the discard pile card would improve your hand.

    Simulates picking up the discard card and making the best possible
    discard from the resulting 11-card hand (excluding the card just
    drawn, per the rules).

    Compare the result to your current deadwood to decide whether
    to draw from the discard pile.

    Args:
        hand: Your current 10-card hand.
        discard_card: The card on top of the discard pile.

    Returns:
        The best possible deadwood after taking the card and
        discarding optimally.

    Example:
        current_dw = calculate_deadwood(view.hand)
        if_take = evaluate_discard_draw(view.hand, view.top_of_discard)
        if if_take < current_dw:
            return "discard"  # taking the card improves our hand
        else:
            return "deck"
    """
    new_hand = list(hand) + [discard_card]
    # Can only discard one of the original cards (not the one just drawn)
    best_dw = min(
        deadwood_after_discard(new_hand, card) for card in hand
    )
    return best_dw


def card_deadwood_contribution(hand: List[Card], card: Card) -> int:
    """Calculate how much a card contributes to your deadwood.

    Returns the difference in deadwood with and without the card.
    Higher values mean the card is hurting your hand more.

    Args:
        hand: Your current hand (should contain the card).
        card: The card to evaluate.

    Returns:
        Deadwood with the card minus deadwood without it.

    Raises:
        ValueError: If the card is not in the hand.
    """
    current_dw = calculate_deadwood(hand)
    remaining = list(hand)
    try:
        remaining.remove(card)
    except ValueError:
        raise ValueError(f"Card {card} is not in the hand")
    without_dw = calculate_deadwood(remaining)
    return current_dw - without_dw


# --- Advanced Strategy Utilities ---

def is_provably_safe_discard(
    card: Card,
    seen_cards: Set[Card],
    my_hand: Set[Card] = None,
) -> bool:
    """Check if a card is provably safe to discard.

    A card is "provably safe" if the opponent cannot use it to complete
    any meld because sufficient blocking cards are unavailable to them.

    Cards unavailable to the opponent are those in the discard pile or
    in your own hand (excluding the card being evaluated, since you're
    about to discard it). If ``my_hand`` is provided, it is subtracted
    from ``seen_cards`` so that cards in your hand are not counted as
    blocking the opponent — only cards truly out of play count.

    Set-safe: 2+ of the other 3 same-rank cards are unavailable to
    opponent, so they can't form a set of 3.

    Run-safe: For every possible 3-card run containing this card, at
    least one other required card is unavailable to opponent.

    Args:
        card: Card to check for safety.
        seen_cards: All cards you know about (your hand + discard pile).
        my_hand: Your hand as a set. If provided, cards in your hand
            (other than ``card``) are excluded from the blocking set,
            since the opponent could eventually acquire them.

    Returns:
        True if opponent cannot use this card in any meld.

    Example:
        >>> seen = set(view.hand + view.discard_pile)
        >>> my_hand = set(view.hand)
        >>> safe_cards = [c for c in view.hand
        ...               if is_provably_safe_discard(c, seen, my_hand)]
    """
    # Cards truly unavailable to the opponent: seen cards minus our
    # hand (we still hold those, opponent could get them later), but
    # including the card we're evaluating (we're discarding it, so it
    # won't stay in our hand).
    if my_hand is not None:
        unavailable = (seen_cards - my_hand) | {card}
    else:
        unavailable = seen_cards

    # Check set safety
    other_same_rank = sum(
        1 for c in unavailable
        if c.rank == card.rank and c != card
    )
    set_safe = other_same_rank >= 2

    # Check run safety
    cv = card.rank.value
    run_safe = True
    for start in (cv - 2, cv - 1, cv):
        vals = [start, start + 1, start + 2]
        if vals[0] < 1 or vals[2] > 13:
            continue
        other_vals = [v for v in vals if v != cv]
        opponent_can_have_all = True
        for v in other_vals:
            if Card(Rank(v), card.suit) in unavailable:
                opponent_can_have_all = False
                break
        if opponent_can_have_all:
            run_safe = False
            break

    return set_safe and run_safe


def count_meld_outs(card: Card, hand: List[Card], seen_cards: Set[Card]) -> int:
    """Count how many unseen cards would complete a meld with this card.

    This helps evaluate which cards have the most potential for improvement.
    Cards with more outs are more valuable to keep.

    Args:
        card: The card to evaluate.
        hand: Current hand including the card.
        seen_cards: Cards already seen (your hand + discard pile).

    Returns:
        Number of unseen cards that complete melds with this card.

    Example:
        >>> hand = [Card(Rank.FIVE, Suit.HEARTS),
        ...         Card(Rank.SIX, Suit.HEARTS), ...]
        >>> card = Card(Rank.FIVE, Suit.HEARTS)
        >>> seen = set(hand + view.discard_pile)
        >>> outs = count_meld_outs(card, hand, seen)
        >>> # Might return 6: three 5s (set) + 4H, 7H (run)
    """
    unseen = ALL_CARDS - seen_cards
    others = [c for c in hand if c != card]
    outs: Set[Card] = set()

    # Set outs: have a pair (need a third) or three-of-a-kind (need the fourth)
    same_rank = sum(1 for c in others if c.rank == card.rank)
    if same_rank >= 1:
        for c in unseen:
            if c.rank == card.rank:
                outs.add(c)

    # Run outs
    cv = card.rank.value
    suit_vals = {c.rank.value for c in others if c.suit == card.suit}

    has_m1 = (cv - 1) in suit_vals
    has_p1 = (cv + 1) in suit_vals
    has_m2 = (cv - 2) in suit_vals
    has_p2 = (cv + 2) in suit_vals

    if has_m1:
        for v in (cv - 2, cv + 1):
            if 1 <= v <= 13:
                c = Card(Rank(v), card.suit)
                if c in unseen:
                    outs.add(c)

    if has_p1:
        for v in (cv - 1, cv + 2):
            if 1 <= v <= 13:
                c = Card(Rank(v), card.suit)
                if c in unseen:
                    outs.add(c)

    if has_m2 and not has_m1:
        v = cv - 1
        if 1 <= v <= 13:
            c = Card(Rank(v), card.suit)
            if c in unseen:
                outs.add(c)

    if has_p2 and not has_p1:
        v = cv + 1
        if 1 <= v <= 13:
            c = Card(Rank(v), card.suit)
            if c in unseen:
                outs.add(c)

    return len(outs)


def score_discard_safety(
    card: Card,
    opponent_discards: List[Card],
    seen_cards: Set[Card]
) -> float:
    """Rate how safe it is to discard this card (0=dangerous, 1=safe).

    This function considers opponent behavior to estimate safety:
    - Penalizes cards of the same rank as cards opponent picked
    - Penalizes cards near (in rank and suit) to opponent's picks
    - Rewards cards when many of the same rank have been seen

    Args:
        card: Card to evaluate for discard safety.
        opponent_discards: Cards the opponent has discarded so far.
        seen_cards: All cards seen (your hand + discard pile).

    Returns:
        Safety score (higher = safer). Typically ranges from -20 to +5.
        Negative scores indicate danger, positive scores indicate safety.

    Example:
        >>> seen = set(view.hand + view.discard_pile)
        >>> # Pass only the opponent's discards, not the full pile.
        >>> # Track opponent discards separately in on_turn_end().
        >>> safest = max(view.hand,
        ...              key=lambda c: score_discard_safety(
        ...                  c, opponent_discards, seen))
        >>> # Discard the safest card
    """
    safety = 0.0

    # Cards the opponent discarded are ones they don't want.
    # Discarding a card of the same rank/nearby suit is SAFER because
    # the opponent has shown they aren't collecting those cards.
    for disc in opponent_discards:
        # Reward same rank (opponent doesn't want this rank)
        if disc.rank == card.rank:
            safety += 5.0
        # Reward nearby suit cards (opponent not building runs here)
        if (disc.suit == card.suit
                and abs(disc.rank.value - card.rank.value) <= 2):
            safety += 3.0

    # Reward if many of the same rank are seen (set is blocked)
    seen_same_rank = sum(
        1 for c in seen_cards
        if c.rank == card.rank and c != card
    )
    safety += seen_same_rank * 1.5

    return safety


def count_near_melds(hand: List[Card]) -> int:
    """Count card groupings that are one card away from forming a meld.

    Near-melds include:
    - Pairs (2 cards of same rank) - one more card needed for a set
    - Two consecutive cards of same suit - one more card needed for a run

    Args:
        hand: Cards to analyze.

    Returns:
        Number of near-meld opportunities in the hand.

    Example:
        >>> hand = [Card(Rank.FIVE, Suit.HEARTS),
        ...         Card(Rank.FIVE, Suit.DIAMONDS),  # Pair
        ...         Card(Rank.SIX, Suit.HEARTS),     # Consecutive with 5H
        ...         Card(Rank.KING, Suit.SPADES)]
        >>> count_near_melds(hand)
        2  # One pair (5H-5D) and one consecutive (5H-6H)
    """
    near_melds = 0
    hand_set = set(hand)

    # Count pairs (potential sets)
    from collections import Counter
    rank_counts = Counter(c.rank for c in hand)
    for rank, count in rank_counts.items():
        if count == 2:
            near_melds += 1  # Pair needs one more for set

    # Count potential runs (consecutive same suit).
    # Only count each adjacent pair once: check upward from each card.
    for card in hand:
        cv = card.rank.value
        suit = card.suit

        if cv < 13:  # Not King
            next_card = Card(Rank(cv + 1), suit)
            if next_card in hand_set:
                near_melds += 1

    return near_melds


def calculate_hand_strength(hand: List[Card]) -> float:
    """Calculate overall hand strength (0.0 = weak, 1.0 = gin).

    Hand strength considers multiple factors:
    - Current deadwood (most important)
    - Number of melds formed
    - Near-melds (potential for improvement)
    - Card flexibility (cards useful in multiple melds)

    Args:
        hand: Cards to evaluate.

    Returns:
        Strength score from 0.0 (terrible) to 1.0 (gin/perfect).

    Example:
        >>> # Gin hand (0 deadwood)
        >>> gin_hand = [Card(Rank.FIVE, Suit.HEARTS),
        ...             Card(Rank.SIX, Suit.HEARTS),
        ...             Card(Rank.SEVEN, Suit.HEARTS),
        ...             ...]  # All cards in melds
        >>> calculate_hand_strength(gin_hand)
        1.0
        >>>
        >>> # Weak hand (high deadwood, no melds)
        >>> weak_hand = [Card(Rank.KING, Suit.HEARTS),
        ...              Card(Rank.QUEEN, Suit.DIAMONDS),
        ...              Card(Rank.JACK, Suit.CLUBS),
        ...              ...]
        >>> calculate_hand_strength(weak_hand)
        0.1  # Very weak
    """
    if not hand:
        return 0.0

    # Calculate current deadwood (0-100+ points possible)
    deadwood = calculate_deadwood(hand)

    # Gin is perfect
    if deadwood == 0:
        return 1.0

    # Base score from deadwood (lower is better)
    # Max reasonable deadwood is ~100 (10 face cards)
    # Scale so 0 deadwood = 1.0, 50 deadwood = 0.5, 100 deadwood = 0.0
    base_score = max(0.0, 1.0 - (deadwood / 100.0))

    # Bonus for melds formed
    melds, _ = find_best_melds(hand)
    meld_bonus = len(melds) * 0.1  # Each meld adds 10%

    # Bonus for near-melds (potential)
    near_meld_count = count_near_melds(hand)
    near_meld_bonus = near_meld_count * 0.05  # Each near-meld adds 5%

    # Combine factors
    strength = base_score + meld_bonus + near_meld_bonus

    # Clamp to [0.0, 1.0]
    return min(1.0, max(0.0, strength))


# Re-export core functions for convenience
__all__ = [
    "calculate_deadwood",
    "is_gin",
    "can_knock",
    "is_valid_meld",
    "get_melds",
    "get_best_melds",
    "get_unmelded_cards",
    "deadwood_after_discard",
    "best_discard",
    "evaluate_discard_draw",
    "card_deadwood_contribution",
    "is_provably_safe_discard",
    "count_meld_outs",
    "score_discard_safety",
    "count_near_melds",
    "calculate_hand_strength",
]
