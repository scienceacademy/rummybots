"""Utility functions to help with bot strategy.

Import these functions in your bot to analyze hands and make decisions.

Example:
    from framework.utilities import calculate_deadwood, find_best_melds

    class MyBot(Bot):
        def knock_decision(self, view):
            deadwood = calculate_deadwood(view.hand)
            return deadwood <= 5  # only knock with low deadwood
"""

from typing import List, Tuple

from engine.card import Card
from engine.rules import (
    Meld,
    calculate_deadwood,
    can_knock,
    find_all_melds,
    find_best_melds,
    is_gin,
    is_valid_meld,
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
]
