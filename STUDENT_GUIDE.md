# Student Guide: Building Your Gin Rummy Bot

This guide walks you through creating a bot for the Gin Rummy tournament.

## Step 1: Set Up Your Bot File

Copy the template to a new file:

```bash
cp bots/student_bot_template.py bots/my_bot.py
```

Open `bots/my_bot.py` and rename the class:

```python
class MyBot(Bot):
    @property
    def name(self):
        return "My Bot"  # Give your bot a name!
```

## Step 2: Understand the Game View

Every decision method receives a `view` object (a `PlayerView`) with:

| Property | Type | Description |
|----------|------|-------------|
| `view.hand` | `list[Card]` | Your current cards |
| `view.discard_pile` | `list[Card]` | All discarded cards (full history) |
| `view.top_of_discard` | `Card` or `None` | Top card of the discard pile |
| `view.deck_size` | `int` | Cards remaining in the deck |
| `view.opponent_hand_size` | `int` | Number of cards opponent has |
| `view.phase` | `GamePhase` | Current phase (DRAW, DISCARD, KNOCK) |

Cards have two main properties:
- `card.rank` — the rank (ACE, TWO, ... KING)
- `card.suit` — the suit (CLUBS, DIAMONDS, HEARTS, SPADES)
- `card.deadwood_value` — point value (ace=1, face cards=10, others=face value)

## Step 3: Implement Your Strategy

### draw_decision(view) → "deck" or "discard"

Decide where to draw from. The discard pile's top card is visible — you know what you're getting. The deck is a mystery.

```python
def draw_decision(self, view):
    # Simple: always draw from deck
    return "deck"

    # Smarter: take the discard if it improves your hand
    if view.top_of_discard is not None:
        current_dw = calculate_deadwood(view.hand)
        if_take = evaluate_discard_draw(view.hand, view.top_of_discard)
        if if_take < current_dw:
            self._drew_from_discard = view.top_of_discard
            return "discard"
    return "deck"
```

**Important:** If you draw from the discard pile, you **cannot** discard that same card on the same turn. Track what you drew so you can avoid it in `discard_decision`.

### discard_decision(view) → Card

After drawing, you have 11 cards. Choose one to discard.

```python
def discard_decision(self, view):
    # Simple: discard whatever minimizes deadwood
    return best_discard(view.hand)

    # If you drew from discard, exclude that card
    choices = view.hand
    if self._drew_from_discard is not None:
        choices = [c for c in choices if c != self._drew_from_discard]
    return best_discard(choices)
```

### knock_decision(view) → True or False

Called only when your deadwood ≤ 10. Should you end the hand?

```python
def knock_decision(self, view):
    # Simple: always knock when you can
    return True

    # Conservative: only knock with very low deadwood
    return calculate_deadwood(view.hand) <= 5

    # Aggressive when deck is low (opponent might catch up)
    if view.deck_size < 10:
        return True
    return calculate_deadwood(view.hand) <= 3
```

## Step 4: Use the Utility Functions

Import these from `framework.utilities`:

```python
from framework.utilities import (
    calculate_deadwood,      # Total deadwood points for a hand
    is_gin,                  # True if deadwood is 0
    can_knock,               # True if deadwood <= 10
    get_melds,               # All possible melds in a hand
    get_best_melds,          # Optimal melds + leftover cards
    get_unmelded_cards,      # Cards not in any meld
    best_discard,            # Card to discard for minimum deadwood
    deadwood_after_discard,  # Deadwood if you discard a specific card
    evaluate_discard_draw,   # Best deadwood if you take the discard card
    card_deadwood_contribution,  # How much a card hurts your hand
)
```

### Examples

```python
# What's my current deadwood?
dw = calculate_deadwood(view.hand)

# What melds do I have?
melds, unmelded = get_best_melds(view.hand)

# Which card should I discard?
to_discard = best_discard(view.hand)

# Would taking the discard card help me?
if view.top_of_discard:
    current = calculate_deadwood(view.hand)
    if_take = evaluate_discard_draw(view.hand, view.top_of_discard)
    improves = if_take < current  # True if taking it helps

# How much is each unmelded card hurting me?
for card in get_unmelded_cards(view.hand):
    cost = card_deadwood_contribution(view.hand, card)
    print(f"{card}: costs {cost} deadwood points")
```

## Step 5: Track Game State (Optional)

Override the lifecycle hooks to track information across turns:

```python
class MyBot(Bot):
    def __init__(self):
        self._drew_from_discard = None
        self._opponent_discards = []

    def on_game_start(self, player_index, view):
        """Reset tracking at the start of each game."""
        self._drew_from_discard = None
        self._opponent_discards = []

    def on_turn_end(self, view):
        """Track discards after each turn."""
        # The discard pile shows the full history
        self._opponent_discards = list(view.discard_pile)
```

## Step 6: Test Your Bot

Run a tournament to see how your bot performs:

```bash
# Quick test with 20 games per matchup
python3 main.py --games 20

# Reproducible results
python3 main.py --games 50 --seed 42
```

## Strategy Ideas

Here are some strategies to explore:

### Draw Strategy
- **Take from discard** when the card completes a meld (set or run)
- **Avoid taking from discard** if it doesn't improve your hand — it reveals information to your opponent
- Consider whether taking a card creates **partial melds** (two of a kind, two in a run sequence)

### Discard Strategy
- **Discard high deadwood** cards that aren't part of or near a meld
- **Avoid discarding cards the opponent might want** — track what they've picked up from the discard pile
- **Prefer discarding cards whose rank has been seen** in the discard pile (opponent less likely to need them)
- **Keep cards near melds** — a pair is close to a set, consecutive cards are close to a run

### Knock Strategy
- **Low deadwood knock** (≤ 5) is safer — less chance of being undercut
- **Gin is always best** — 25 point bonus and no layoffs allowed
- **Knock early** if the deck is running low — a draw scores 0 for both
- **Don't knock** if you think the opponent has very low deadwood — risk of undercut

### Advanced Ideas
- Track which cards have been discarded to estimate what remains in the deck
- Track what the opponent picks from the discard pile to guess their strategy
- Adapt knock threshold based on game state (deck size, opponent behavior)

## Gin Rummy Scoring Reference

| Outcome | Points |
|---------|--------|
| **Knock** | Difference in deadwood (defender - knocker) |
| **Gin** | Defender's deadwood + 25 bonus |
| **Undercut** | Difference in deadwood + 25 bonus (to defender) |
| **Draw** | 0 (deck exhausted) |

Card values: Ace = 1, Number cards = face value, Face cards (J/Q/K) = 10
