# Gin Rummy Bot Tournament

A tournament framework for student-programmed bots to play Gin Rummy against each other. Students focus on strategy and decision-making while the framework handles game mechanics, scoring, and tournament management.

## Quick Start

```bash
# Run a tournament with all bots in the bots/ directory
python main.py

# Run with a fixed seed for reproducible results
python main.py --seed 42

# Run fewer games per matchup for quick testing
python main.py --games 20
```

## Creating Your Bot

1. Copy `bots/student_bot_template.py` to a new file (e.g., `bots/my_bot.py`)
2. Rename the class and implement your strategy
3. Run `python main.py` to see how your bot performs

See [STUDENT_GUIDE.md](STUDENT_GUIDE.md) for a detailed walkthrough.

## Project Structure

```
rummybots/
├── engine/                  # Core game logic (don't modify)
│   ├── card.py              # Card, Deck, Rank, Suit classes
│   ├── game.py              # GameState, GameEngine, PlayerView
│   └── rules.py             # Meld detection, scoring, layoffs
├── framework/               # Bot and tournament framework
│   ├── bot_interface.py     # Abstract Bot base class
│   ├── utilities.py         # Helper functions for bot strategy
│   └── tournament.py        # Match and tournament management
├── bots/                    # Bot implementations
│   ├── random_bot.py        # RandomBot — random legal moves
│   ├── basic_bot.py         # BasicBot — simple heuristics
│   ├── intermediate_bot.py  # IntermediateBot — smarter strategy
│   └── student_bot_template.py  # Template for student bots
├── scripts/                 # Utility scripts
│   └── validate_bot.py      # Bot validation tool
├── tests/                   # Test suite (192 tests)
├── main.py                  # Tournament runner CLI
├── STUDENT_GUIDE.md         # Guide for creating bots
└── README.md
```

## How It Works

### Gin Rummy Rules (Single Hand)

- Each player is dealt 10 cards. One card is flipped to start the discard pile.
- On each turn, a player **draws** (from deck or discard pile), then **discards** one card.
- **Melds** are sets (3-4 of same rank) or runs (3+ consecutive same suit).
- **Deadwood** is the point value of unmelded cards (face cards = 10, ace = 1).
- A player can **knock** when their deadwood is 10 or less.
- **Gin** (0 deadwood) earns a 25-point bonus.
- After a knock, the defender can **lay off** cards onto the knocker's melds.
- If the defender's deadwood is equal or lower, they **undercut** for a 25-point bonus.
- If the deck runs low (< 2 cards), the hand is a draw.

### Bot Interface

Bots implement three methods:

| Method | Called When | Returns |
|--------|-----------|---------|
| `draw_decision(view)` | Start of turn | `"deck"` or `"discard"` |
| `discard_decision(view)` | After drawing (11 cards) | A `Card` to discard |
| `knock_decision(view)` | After discarding, if deadwood ≤ 10 | `True` or `False` |

### Tournament Format

- **Round-robin**: Every bot plays every other bot
- **100 games per pairing** (configurable) with alternating sides
- **Ranked by win percentage**, then total points
- Errors from crashing bots are caught and reported

## CLI Options

```
python main.py [options]

Options:
  --games N     Games per bot pairing (default: 100)
  --seed N      Random seed for reproducibility
  --no-h2h      Skip head-to-head details
  --quiet        Suppress match progress output
```

## Running Tests

```bash
python -m unittest discover -s tests -v
```

## Sample Tournament Output

```
======================================================================
TOURNAMENT RESULTS
======================================================================
Rank  Bot                     W    L    D    Win%    Pts    Avg  Gins
----------------------------------------------------------------------
1     IntermediateBot        31    9    0  77.5%   1402   35.0     0
2     BasicBot               28   11    1  71.8%   1152   28.8     0
3     RandomBot               0   39    1   0.0%      0    0.0     0
======================================================================
```
