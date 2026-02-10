# Student Guide: Building Your Gin Rummy Bot

This guide walks you through creating a bot for the Gin Rummy tournament.

## Step 1: Set Up Your Bot File

Copy the template to a new file:

```bash
cp bots/student_bot_template.py bots/bot_<name>.py
```

Open `bots/bot_<name>.py` and rename the class with your bot's name:

```python
class MyBot(Bot):
    @property
    def name(self):
        return "MyBot"  # Give your bot a name!
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

### Advanced Utilities

For more sophisticated strategies, use these advanced utilities:

```python
from framework.utilities import (
    count_meld_outs,           # How many unseen cards complete melds with this card
    is_provably_safe_discard,  # True if opponent can't use this card in any meld
    score_discard_safety,      # Rate how safe it is to discard (0=dangerous, 1=safe)
    calculate_hand_strength,   # Overall hand strength (0.0=weak, 1.0=gin)
    count_near_melds,          # Count cards one away from forming melds
)
```

**count_meld_outs(card, hand, seen_cards)**
Counts how many unseen cards would complete a meld with this card.
Useful for: Evaluating which cards have the most improvement potential.

```python
seen = set(view.hand + view.discard_pile)
for card in view.hand:
    outs = count_meld_outs(card, view.hand, seen)
    # Higher outs = more valuable to keep
```

**is_provably_safe_discard(card, seen_cards)**
Returns True if opponent cannot use this card in any meld (dead card).
Useful for: Safe discarding without giving opponent advantage.

```python
seen = set(view.hand + view.discard_pile)
safe_cards = [c for c in view.hand if is_provably_safe_discard(c, seen)]
# Discard safe cards first
```

**score_discard_safety(card, opponent_picks, seen_cards)**
Rates safety of discarding a card (higher = safer, negative = dangerous).
Useful for: Choosing between multiple discard options.

```python
seen = set(view.hand + view.discard_pile)
# Find safest discard
safest = max(view.hand, key=lambda c:
    score_discard_safety(c, view.discard_pile, seen))
```

**calculate_hand_strength(hand)**
Evaluates overall hand strength from 0.0 (weak) to 1.0 (gin).
Useful for: Knock decisions and strategy adjustments.

```python
strength = calculate_hand_strength(view.hand)
if strength > 0.7:
    # Strong hand, might knock early
```

**count_near_melds(hand)**
Counts cards one away from forming melds (pairs, consecutive cards).
Useful for: Understanding hand potential.

```python
near_melds = count_near_melds(view.hand)
# More near-melds = more improvement potential
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
python main.py --games 20

# Reproducible results
python main.py --games 50 --seed 42
```

### Debugging Your Bot

Before submitting, use the validation tool to catch common errors:

```bash
python scripts/validate_bot.py bots/my_bot.py
```

The validator checks:
- ✓ File exists and is readable
- ✓ Bot inherits from framework.bot_interface.Bot
- ✓ Bot has unique name property
- ✓ All three methods implemented
- ✓ Bot handles empty discard pile (first turn)
- ✓ Bot doesn't crash on sample hands
- ✓ Bot returns correct types (str/"deck"/"discard", Card, bool)
- ✓ Bot completes 10 games in <30 seconds
- ⚠ Bot performs better than RandomBot

### Common Errors and Solutions

**Error: "Invalid type from draw_decision()"**
- Make sure draw_decision() returns a string, not DrawChoice enum
- Return exactly "deck" or "discard" (lowercase)

**Error: "Card not in your hand"**
- You tried to discard a card you don't have
- Common cause: discarding the card you just drew from discard pile
- Solution: Return a Card object that's actually in view.hand

**Error: "Cannot discard card just drawn from discard pile"**
- Gin Rummy rule: you can't immediately discard what you just picked up
- Solution: Choose a different card to discard

**Error: "Bot timeout"**
- Your bot is taking too long (>5 seconds per decision)
- Check for infinite loops or expensive calculations
- Use utilities.calculate_deadwood() instead of reimplementing meld finding
- Avoid nested loops that don't terminate

### Print Debugging

Print statements work during local testing:

```python
def discard_decision(self, view):
    print(f"My hand: {view.hand}")
    print(f"Deadwood: {calculate_deadwood(view.hand)}")
    # ... your logic
```

Note: Prints are suppressed during tournaments.

## Step 7: Submit Your Bot

When your bot is ready for the tournament:

1. **Make sure your bot file is in the `bots/` directory** and has a unique filename (e.g., `bots/bot_<name>.py`).

2. **Verify your bot class**:
   - It subclasses `Bot` from `framework.bot_interface`
   - It has a unique `name` property (this is what appears in the rankings)
   - All three decision methods are implemented: `draw_decision`, `discard_decision`, `knock_decision`

3. **Run a final check** to make sure your bot works without errors:
   ```bash
   python main.py --games 50 --seed 42
   ```

   ```bash
   python scripts/validate_bot.py bots/my_bot.py
   ```

   If you see errors next to your bot's name, fix them before submitting.

1. **Submit with submit50** Only your bot file will be submitted (e.g., `bot_<name>.py`). Do not modify any other files in the project.

```bash
submit50 scienceacademy/problems/2025ap/rummybots
```

### Submission Checklist

- [ ] Bot file is named something other than `student_bot_template.py`, and starts with `bot_`.
- [ ] Bot class has a unique `name`
- [ ] Bot runs in the tournament without errors
- [ ] Bot does not import anything outside the standard library, `engine`, or `framework`

---

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
