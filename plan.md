# Gin Rummy Bot Tournament - Implementation Plan

## Phase 1: Foundation - Card and Deck System

### Step 1.1: Create Card Class

- Define Card class with rank and suit
- Implement card comparison and equality
- Implement string representation
- Add card value methods for Gin Rummy (face cards = 10, Ace = 1, etc.)

### Step 1.2: Create Deck Class

- Implement standard 52-card deck
- Add shuffle functionality
- Add deal and draw methods
- Track remaining cards

### Step 1.3: Test Card and Deck

- Write unit tests for card operations
- Write unit tests for deck operations
- Verify shuffle randomness
- Test edge cases (empty deck, etc.)

**Deliverable**: Functional card and deck system with tests

---

## Phase 2: Core Game Logic

### Step 2.1: Implement Meld Detection

- Create function to identify sets (3-4 of same rank)
- Create function to identify runs (3+ consecutive cards of same suit)
- Create function to find all possible melds in a hand
- Create function to find optimal meld arrangement (minimize deadwood)

### Step 2.2: Implement Scoring System

- Calculate deadwood points for unmelded cards
- Detect gin (0 deadwood)
- Implement knock scoring rules
- Handle undercut scenarios (defender has less/equal deadwood)

### Step 2.3: Create Game State Class

- Track current hands for both players
- Track deck and discard pile
- Track whose turn it is
- Track game phase (draw, discard, knock, end)
- Provide immutable state views for bots

### Step 2.4: Test Game Logic

- Test meld detection with various hands
- Test deadwood calculation
- Test scoring scenarios
- Test edge cases

**Deliverable**: Complete game logic with meld detection and scoring

---

## Phase 3: Game Engine

### Step 3.1: Implement Game Flow

- Initialize game (shuffle, deal 10 cards each, flip first discard)
- Handle draw phase (from deck or discard pile)
- Handle discard phase
- Handle knock declaration
- Handle game end and winner determination

### Step 3.2: Implement Move Validation

- Validate draw choices
- Validate discard choices (must have 11 cards before discard)
- Validate knock legality (deadwood ≤ 10)
- Validate layoff rules (defender adding to knocker's melds)

### Step 3.3: Create Game Manager

- Orchestrate full game from start to finish
- Interface with two bot instances
- Enforce turn order
- Handle invalid moves (with clear error messages)
- Return game results

### Step 3.4: Test Game Engine

- Test complete game flows
- Test all edge cases (gin on deal, empty deck, etc.)
- Test move validation
- Simulate full games

**Deliverable**: Fully functional game engine

---

## Phase 4: Bot Interface and Utilities

### Step 4.1: Define Bot Abstract Class

- Define abstract methods: draw_decision(), discard_decision(), knock_decision()
- Define receive_state() method for game state updates
- Document expected behavior and return formats

### Step 4.2: Implement Utility Library

- calculate_deadwood(hand) -> int
- is_gin(hand) -> bool
- find_melds(hand) -> list of melds
- find_unmelded_cards(hand, melds) -> list
- can_knock(hand) -> bool
- get_discard_history() -> list
- get_deck_size() -> int

### Step 4.3: Create Game State View for Bots

- Provide read-only access to relevant game information
- Hide opponent's hand
- Expose own hand, discard pile, deck size
- Provide helper methods using utility library

### Step 4.4: Test Bot Interface

- Test that state views are immutable
- Test that utilities work correctly
- Verify bots cannot access hidden information

**Deliverable**: Complete bot interface and utility library

---

## Phase 5: Sample Bots

### Step 5.1: Implement RandomBot

- Randomly choose between deck and discard pile
- Randomly choose card to discard
- Randomly decide whether to knock (if legal)

### Step 5.2: Implement BasicBot

- Always draw from deck
- Discard highest deadwood card
- Knock when deadwood ≤ 10

### Step 5.3: Implement IntermediateBot (Optional)

- Track discards to avoid giving opponent useful cards
- Calculate probability of improving hand
- Strategic knock decisions based on game state
- More sophisticated discard logic

### Step 5.4: Create Student Bot Template

- Provide skeleton class with all required methods
- Add helpful comments explaining each decision point
- Include examples of using utility functions
- Add suggestions for strategies to try

### Step 5.5: Test Sample Bots

- Verify all bots follow interface correctly
- Test bots against each other
- Ensure no crashes or invalid moves

**Deliverable**: Working sample bots and student template

---

## Phase 6: Tournament Framework

### Step 6.1: Implement Match System

- Run single game between two bots
- Alternate dealer across games
- Record results (winner, scores, game stats)
- Handle errors gracefully (bot crashes, timeouts)

### Step 6.2: Implement Round-Robin Tournament

- Generate all bot pairings
- Run N games per pairing (configurable, default 100)
- Aggregate results per bot
- Handle odd number of bots if needed

### Step 6.3: Implement Statistics and Ranking

- Calculate win percentage for each bot
- Calculate average points per game
- Calculate head-to-head records
- Generate leaderboard

### Step 6.4: Create Tournament Runner

- Load all bot classes from bots directory
- Configure tournament parameters (games per pairing, etc.)
- Run complete tournament
- Display results

### Step 6.5: Test Tournament System

- Test with 2, 3, and 5+ bots
- Verify statistics are correct
- Test error handling for misbehaving bots
- Verify deterministic results with fixed random seed

**Deliverable**: Complete tournament framework

---

## Phase 7: Documentation and Polish

### Step 7.1: Write Student Documentation

- How to create a bot (step-by-step guide)
- Available utility functions reference
- Example strategies and decision trees
- How to test their bot locally
- How to submit bot to tournament

### Step 7.2: Write README

- Project overview
- Setup instructions
- How to run tournaments
- How to add new bots
- Project structure explanation

### Step 7.3: Add Code Documentation

- Docstrings for all public methods
- Type hints throughout
- Comments for complex logic
- Examples in docstrings

### Step 7.4: Create Example Usage Scripts

- Script to run single game with verbose output
- Script to test a bot against sample bots
- Script to run quick tournament

**Deliverable**: Complete documentation

---

## Phase 8: Testing and Validation

### Step 8.1: Integration Testing

- Test complete workflow from tournament start to results
- Test with various bot combinations
- Verify all edge cases are handled

### Step 8.2: Performance Testing

- Ensure tournaments complete in reasonable time
- Profile any slow components
- Optimize if needed

### Step 8.3: Final Validation

- Run tournament with all sample bots
- Verify results make sense (BasicBot beats RandomBot, etc.)
- Check for any remaining bugs

**Deliverable**: Tested and validated system

---

## Implementation Order Summary

1. **Phase 1**: Card/Deck foundation (1-2 hours)
2. **Phase 2**: Game logic and meld detection (2-3 hours)
3. **Phase 3**: Game engine (2-3 hours)
4. **Phase 4**: Bot interface and utilities (1-2 hours)
5. **Phase 5**: Sample bots (1-2 hours)
6. **Phase 6**: Tournament framework (2-3 hours)
7. **Phase 7**: Documentation (1-2 hours)
8. **Phase 8**: Testing and validation (1-2 hours)

**Estimated Total Time**: 11-18 hours

---

## Testing Strategy

Each phase should include:

- Unit tests for individual components
- Integration tests for phase deliverables
- Manual testing for game flow and bot behavior

Run full test suite after each phase before proceeding.

---

## Success Criteria

- [ ] Game engine correctly implements Gin Rummy rules
- [ ] Bots can play complete games without errors
- [ ] Tournament runs successfully with multiple bots
- [ ] Results are accurate and reproducible
- [ ] Student template is clear and helpful
- [ ] Documentation is complete and understandable
- [ ] All tests pass
