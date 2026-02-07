# Gin Rummy Bot Tournament Framework

## Project Overview

Create a tournament framework for student-programmed bots to play Gin Rummy against each other. The focus is on decision-making and strategy optimization, with the framework handling game mechanics and providing utilities for bot development.

## Core Requirements

### 1. Game Engine

- Implement complete Gin Rummy rules for 2-player games
- Handle deck management (shuffling, dealing, drawing)
- Manage discard pile
- Validate all moves for legality
- Detect knocking conditions and gin
- Calculate deadwood and scores
- Determine winners
- Single-hand games (no multi-round scoring to 100 points)

### 2. Bot Interface

Students implement a bot class with a standard interface:

- **draw_decision()**: Choose between drawing from deck or taking discard pile top card
- **discard_decision()**: Choose which card to discard from hand
- **knock_decision()**: Decide whether to knock (if eligible)

The interface should provide bots with:

- Current hand
- Discard pile history (all cards discarded so far)
- Number of cards remaining in deck
- Game state information

### 3. Utility Functions (Provided to Bots)

To help students focus on strategy rather than implementation:

- Calculate deadwood points for a hand
- Check if hand is gin (0 deadwood)
- Identify melds in a hand (sets and runs)
- Identify unmelded cards
- Check if knock is legal (deadwood ≤ 10)
- Query game state and history

### 4. Tournament Manager

- Run round-robin tournament (all bots play all other bots)
- Each pairing plays multiple games (50-100) with alternating dealer
- Track and aggregate results
- Generate rankings based on win percentage or points
- Provide statistics and tournament results

### 5. Sample Bots

Include reference implementations:

- **RandomBot**: Makes random legal moves (baseline)
- **BasicBot**: Simple heuristic (draw from deck, discard highest deadwood)
- **IntermediateBot**: More sophisticated strategy for students to beat

## Technical Specifications

### Language

Python 3.x

### Project Structure

```
gin-rummy-tournament/
├── engine/
│   ├── game.py          # Core game logic
│   ├── card.py          # Card and deck classes
│   └── rules.py         # Rule validation and scoring
├── framework/
│   ├── bot_interface.py # Abstract bot class
│   ├── utilities.py     # Helper functions for bots
│   └── tournament.py    # Tournament management
├── bots/
│   ├── random_bot.py
│   ├── basic_bot.py
│   └── student_bot_template.py
├── tests/
│   └── test_engine.py   # Unit tests for game engine
└── main.py              # Entry point for running tournaments
```

### Key Design Principles

- **Separation of concerns**: Game engine is separate from bot logic
- **Immutable game state**: Bots receive copies of state, cannot modify game directly
- **Simple interface**: Students focus on strategy, not implementation details
- **Extensible**: Easy to add new bots to the tournament
- **Testable**: Game engine should have comprehensive tests

## Deliverables

1. Complete game engine with Gin Rummy rules
2. Bot interface and utility library
3. Tournament framework
4. At least 2 sample bots (random and basic heuristic)
5. Student bot template with comments
6. Documentation for students on how to create their bot
7. README with setup and usage instructions

## Educational Goals

- Students practice decision tree design
- Students optimize strategies through iteration
- Students learn to work within a defined interface
- Students can test their bots against others
- Minimal complexity in information tracking (single hand, clear state)

## Future Enhancements (Out of Scope for Initial Version)

- GUI for watching games
- Multi-round games with scoring to 100
- Advanced statistics and analytics
- Replay functionality
- Web-based interface
