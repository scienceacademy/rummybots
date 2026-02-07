"""Tests for the GameEngine: game flow, move validation, and full simulations."""

import random
import unittest

from engine.card import Card, Deck, Rank, Suit
from engine.game import (
    DrawChoice,
    GameEngine,
    GamePhase,
    GameResult,
    GameState,
    InvalidMoveError,
)
from engine.rules import (
    apply_layoffs,
    can_knock,
    can_lay_off,
    is_valid_run,
    is_valid_set,
    score_with_layoffs,
)


def c(rank_str: str, suit_str: str) -> Card:
    """Shorthand card constructor for tests."""
    rank_map = {
        "A": Rank.ACE, "2": Rank.TWO, "3": Rank.THREE,
        "4": Rank.FOUR, "5": Rank.FIVE, "6": Rank.SIX,
        "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE,
        "10": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN,
        "K": Rank.KING,
    }
    suit_map = {
        "C": Suit.CLUBS, "D": Suit.DIAMONDS,
        "H": Suit.HEARTS, "S": Suit.SPADES,
    }
    return Card(rank_map[rank_str], suit_map[suit_str])


# --- Mock Bots ---

class SimpleBot:
    """Always draws from deck, discards first card, never knocks."""

    def draw_decision(self, view):
        return "deck"

    def discard_decision(self, view):
        return view.hand[0]

    def knock_decision(self, view):
        return False


class KnockBot:
    """Always draws from deck, discards highest deadwood, always knocks."""

    def draw_decision(self, view):
        return "deck"

    def discard_decision(self, view):
        return max(view.hand, key=lambda c: c.deadwood_value)

    def knock_decision(self, view):
        return True


class DiscardDrawBot:
    """Draws from discard pile when possible, discards first non-discard card."""

    def draw_decision(self, view):
        if view.top_of_discard is not None:
            return "discard"
        return "deck"

    def discard_decision(self, view):
        # Discard the first card that isn't the one just drawn
        # (since we always draw from discard, avoid discarding it back)
        # Just discard the first card — the engine will reject if it
        # was the discard-drawn card; this bot is used in controlled tests.
        return view.hand[0]

    def knock_decision(self, view):
        return False


class ScriptedBot:
    """Bot that follows a pre-scripted sequence of decisions."""

    def __init__(self, draw_choices, discard_indices, knock_choices):
        self._draws = iter(draw_choices)
        self._discards = iter(discard_indices)
        self._knocks = iter(knock_choices)

    def draw_decision(self, view):
        return next(self._draws)

    def discard_decision(self, view):
        idx = next(self._discards)
        return view.hand[idx]

    def knock_decision(self, view):
        return next(self._knocks)


# --- Layoff Tests ---

class TestCanLayOff(unittest.TestCase):

    def test_lay_off_onto_set(self):
        meld = [c("5", "H"), c("5", "D"), c("5", "C")]
        self.assertTrue(can_lay_off(c("5", "S"), meld))

    def test_cannot_lay_off_wrong_rank_onto_set(self):
        meld = [c("5", "H"), c("5", "D"), c("5", "C")]
        self.assertFalse(can_lay_off(c("6", "S"), meld))

    def test_cannot_lay_off_onto_full_set(self):
        meld = [c("5", "H"), c("5", "D"), c("5", "C"), c("5", "S")]
        # 5-card "set" is invalid
        self.assertFalse(can_lay_off(c("5", "H"), meld))

    def test_lay_off_extend_run_high(self):
        meld = [c("3", "H"), c("4", "H"), c("5", "H")]
        self.assertTrue(can_lay_off(c("6", "H"), meld))

    def test_lay_off_extend_run_low(self):
        meld = [c("4", "H"), c("5", "H"), c("6", "H")]
        self.assertTrue(can_lay_off(c("3", "H"), meld))

    def test_cannot_lay_off_gap_in_run(self):
        meld = [c("3", "H"), c("4", "H"), c("5", "H")]
        self.assertFalse(can_lay_off(c("7", "H"), meld))

    def test_cannot_lay_off_wrong_suit_on_run(self):
        meld = [c("3", "H"), c("4", "H"), c("5", "H")]
        self.assertFalse(can_lay_off(c("6", "D"), meld))


class TestApplyLayoffs(unittest.TestCase):

    def test_lay_off_single_card(self):
        melds = [[c("5", "H"), c("5", "D"), c("5", "C")]]
        unmelded = [c("5", "S"), c("K", "D")]
        remaining = apply_layoffs(melds, unmelded)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0], c("K", "D"))

    def test_lay_off_onto_run(self):
        melds = [[c("3", "H"), c("4", "H"), c("5", "H")]]
        unmelded = [c("6", "H"), c("K", "S")]
        remaining = apply_layoffs(melds, unmelded)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0], c("K", "S"))

    def test_lay_off_multiple_cards(self):
        melds = [[c("3", "H"), c("4", "H"), c("5", "H")]]
        unmelded = [c("6", "H"), c("7", "H")]
        remaining = apply_layoffs(melds, unmelded)
        self.assertEqual(len(remaining), 0)

    def test_no_layoffs_possible(self):
        melds = [[c("5", "H"), c("5", "D"), c("5", "C")]]
        unmelded = [c("K", "S"), c("Q", "D")]
        remaining = apply_layoffs(melds, unmelded)
        self.assertEqual(len(remaining), 2)

    def test_empty_unmelded(self):
        melds = [[c("5", "H"), c("5", "D"), c("5", "C")]]
        remaining = apply_layoffs(melds, [])
        self.assertEqual(len(remaining), 0)


class TestScoreWithLayoffs(unittest.TestCase):

    def test_gin_no_layoffs(self):
        knocker = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"), c("J", "S"),
        ]
        defender = [
            c("K", "H"), c("Q", "H"), c("J", "H"),
            c("2", "D"), c("3", "D"), c("4", "D"),
            c("7", "C"), c("8", "C"), c("9", "C"),
            c("6", "D"),
        ]
        points, result = score_with_layoffs(knocker, defender, is_gin=True)
        self.assertEqual(result, "gin")
        self.assertEqual(points, 6 + 25)  # defender dw=6

    def test_knock_with_layoff(self):
        # Knocker: set of 5s + run 8-9-10 spades, deadwood = 2H (2)
        knocker = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"),
            c("2", "H"),
        ]
        # Defender: has 5S which can lay off onto knocker's set of 5s
        defender = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "S"),  # can lay off
            c("K", "D"),  # deadwood = 10 after layoff
        ]
        points, result = score_with_layoffs(knocker, defender)
        self.assertEqual(result, "knock")
        # Defender deadwood after layoff: K=10, knocker deadwood: 2
        self.assertEqual(points, 10 - 2)

    def test_undercut_via_layoff(self):
        # Knocker: deadwood = 8
        knocker = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("3", "S"), c("4", "S"), c("5", "S"),
            c("8", "H"),  # deadwood = 8
        ]
        # Defender: unmelded 6S can lay off onto knocker's 3-4-5 spades run
        defender = [
            c("2", "H"), c("2", "D"), c("2", "C"),
            c("6", "S"),  # lays off → 0 unmelded deadwood
            c("7", "H"), c("7", "D"), c("7", "C"),
        ]
        points, result = score_with_layoffs(knocker, defender)
        self.assertEqual(result, "undercut")
        # Defender dw=0 after layoff, knocker dw=8
        # Undercut: -(8 - 0 + 25) = -33
        self.assertEqual(points, -33)


# --- GameEngine Flow Tests ---

class TestGameEngineSetup(unittest.TestCase):

    def test_engine_creates_valid_state(self):
        engine = GameEngine()
        engine.state.setup()
        self.assertEqual(len(engine.state.hands[0]), 10)
        self.assertEqual(len(engine.state.hands[1]), 10)
        self.assertEqual(len(engine.state.discard_pile), 1)
        self.assertEqual(engine.state.deck.remaining, 31)


class TestExecuteDraw(unittest.TestCase):

    def setUp(self):
        self.engine = GameEngine()
        self.engine.state.setup(dealer=0)
        # Player 1 is non-dealer and goes first

    def test_draw_from_deck(self):
        self.engine._execute_draw(1, "deck")
        self.assertEqual(len(self.engine.state.hands[1]), 11)
        self.assertEqual(self.engine.state.deck.remaining, 30)
        self.assertEqual(self.engine.state.phase, GamePhase.DISCARD)

    def test_draw_from_discard(self):
        top_card = self.engine.state.discard_pile[-1]
        self.engine._execute_draw(1, "discard")
        self.assertIn(top_card, self.engine.state.hands[1])
        self.assertEqual(len(self.engine.state.hands[1]), 11)
        self.assertEqual(len(self.engine.state.discard_pile), 0)

    def test_draw_accepts_enum(self):
        self.engine._execute_draw(1, DrawChoice.DECK)
        self.assertEqual(len(self.engine.state.hands[1]), 11)

    def test_draw_wrong_player(self):
        with self.assertRaises(InvalidMoveError):
            self.engine._execute_draw(0, "deck")

    def test_draw_wrong_phase(self):
        self.engine.state.phase = GamePhase.DISCARD
        with self.assertRaises(InvalidMoveError):
            self.engine._execute_draw(1, "deck")

    def test_draw_invalid_choice(self):
        with self.assertRaises(InvalidMoveError):
            self.engine._execute_draw(1, "invalid")

    def test_draw_invalid_type(self):
        with self.assertRaises(InvalidMoveError):
            self.engine._execute_draw(1, 42)

    def test_draw_from_empty_discard(self):
        self.engine.state.discard_pile.clear()
        with self.assertRaises(InvalidMoveError):
            self.engine._execute_draw(1, "discard")


class TestExecuteDiscard(unittest.TestCase):

    def setUp(self):
        self.engine = GameEngine()
        self.engine.state.setup(dealer=0)
        # Draw first to get to discard phase
        self.engine._execute_draw(1, "deck")

    def test_discard_valid(self):
        card = self.engine.state.hands[1][0]
        self.engine._execute_discard(1, card)
        self.assertEqual(len(self.engine.state.hands[1]), 10)
        self.assertEqual(self.engine.state.discard_pile[-1], card)

    def test_discard_card_not_in_hand(self):
        # Create a card that's definitely not in the hand
        fake = Card(Rank.ACE, Suit.SPADES)
        # Make sure it's not in the hand
        while fake in self.engine.state.hands[1]:
            fake = Card(Rank.TWO, Suit.DIAMONDS)
        with self.assertRaises(InvalidMoveError):
            self.engine._execute_discard(1, fake)

    def test_discard_wrong_phase(self):
        self.engine.state.phase = GamePhase.DRAW
        card = self.engine.state.hands[1][0]
        with self.assertRaises(InvalidMoveError):
            self.engine._execute_discard(1, card)

    def test_cannot_discard_card_drawn_from_discard(self):
        # Reset and draw from discard instead
        self.engine = GameEngine()
        self.engine.state.setup(dealer=0)
        top_card = self.engine.state.discard_pile[-1]
        self.engine._execute_draw(1, "discard")
        with self.assertRaises(InvalidMoveError):
            self.engine._execute_discard(1, top_card)

    def test_can_discard_other_card_after_discard_draw(self):
        self.engine = GameEngine()
        self.engine.state.setup(dealer=0)
        self.engine._execute_draw(1, "discard")
        # Should be able to discard a different card
        other_card = self.engine.state.hands[1][0]
        if other_card == self.engine._drawn_from_discard:
            other_card = self.engine.state.hands[1][1]
        self.engine._execute_discard(1, other_card)
        self.assertEqual(len(self.engine.state.hands[1]), 10)


class TestExecuteKnock(unittest.TestCase):

    def test_knock_wins(self):
        engine = GameEngine()
        engine.state.setup()
        # Set up a hand that can knock
        engine.state.hands[0] = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"),
            c("2", "H"),  # deadwood = 2
        ]
        engine.state.hands[1] = [
            c("K", "H"), c("Q", "D"), c("J", "C"),
            c("9", "H"), c("8", "D"), c("7", "C"),
            c("6", "S"), c("4", "D"), c("3", "C"),
            c("2", "D"),  # all deadwood = 79
        ]
        result = engine._execute_knock(0)
        self.assertEqual(result.winner, 0)
        self.assertEqual(result.result_type, "knock")
        self.assertGreater(result.score, 0)
        self.assertEqual(result.knocker, 0)

    def test_knock_gin(self):
        engine = GameEngine()
        engine.state.setup()
        engine.state.hands[0] = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"), c("J", "S"),
        ]
        engine.state.hands[1] = [
            c("K", "H"), c("Q", "D"), c("J", "C"),
            c("9", "H"), c("8", "D"), c("7", "C"),
            c("6", "S"), c("4", "D"), c("3", "C"),
            c("2", "D"),
        ]
        result = engine._execute_knock(0)
        self.assertEqual(result.result_type, "gin")
        self.assertEqual(result.winner, 0)

    def test_knock_undercut(self):
        engine = GameEngine()
        engine.state.setup()
        # Knocker has higher deadwood than defender
        engine.state.hands[0] = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"),
            c("10", "H"),  # deadwood = 10
        ]
        engine.state.hands[1] = [
            c("2", "H"), c("2", "D"), c("2", "C"),
            c("3", "H"), c("3", "D"), c("3", "C"),
            c("4", "H"), c("4", "D"), c("4", "C"),
            c("A", "S"),  # deadwood = 1
        ]
        result = engine._execute_knock(0)
        self.assertEqual(result.result_type, "undercut")
        self.assertEqual(result.winner, 1)
        self.assertEqual(result.knocker, 0)


# --- Full Game Tests ---

class TestFullGame(unittest.TestCase):

    def test_game_completes(self):
        """A game between two simple bots should complete."""
        random.seed(42)
        engine = GameEngine()
        result = engine.play_game(SimpleBot(), KnockBot())
        self.assertIsInstance(result, GameResult)
        self.assertIn(
            result.result_type, ("gin", "knock", "undercut", "draw")
        )

    def test_game_with_seed_is_deterministic(self):
        """Same seed should produce same result."""
        random.seed(123)
        engine1 = GameEngine()
        result1 = engine1.play_game(KnockBot(), KnockBot())

        random.seed(123)
        engine2 = GameEngine()
        result2 = engine2.play_game(KnockBot(), KnockBot())

        self.assertEqual(result1.winner, result2.winner)
        self.assertEqual(result1.score, result2.score)
        self.assertEqual(result1.result_type, result2.result_type)

    def test_game_alternating_dealer(self):
        """Games can be played with either player as dealer."""
        random.seed(42)
        engine = GameEngine()
        result0 = engine.play_game(KnockBot(), KnockBot(), dealer=0)
        self.assertIsInstance(result0, GameResult)

        random.seed(42)
        result1 = engine.play_game(KnockBot(), KnockBot(), dealer=1)
        self.assertIsInstance(result1, GameResult)

    def test_many_games_no_crashes(self):
        """Run many games to check for stability."""
        engine = GameEngine()
        for seed in range(50):
            random.seed(seed)
            result = engine.play_game(KnockBot(), SimpleBot())
            self.assertIsInstance(result, GameResult)
            if result.result_type != "draw":
                self.assertIn(result.winner, (0, 1))
                self.assertGreater(result.score, 0)

    def test_draw_result(self):
        """A game where no one knocks should eventually draw."""
        random.seed(42)
        engine = GameEngine()
        result = engine.play_game(SimpleBot(), SimpleBot())
        # Two SimpleBots never knock, so game should end as draw
        self.assertEqual(result.result_type, "draw")
        self.assertIsNone(result.winner)
        self.assertEqual(result.score, 0)

    def test_knock_bot_beats_simple_bot_usually(self):
        """KnockBot should win more than it loses against SimpleBot."""
        knock_wins = 0
        simple_wins = 0
        draws = 0
        for seed in range(100):
            random.seed(seed)
            engine = GameEngine()
            result = engine.play_game(KnockBot(), SimpleBot())
            if result.winner == 0:
                knock_wins += 1
            elif result.winner == 1:
                simple_wins += 1
            else:
                draws += 1
        # KnockBot should win significantly more
        self.assertGreater(knock_wins, simple_wins)

    def test_game_result_repr(self):
        result = GameResult(
            winner=0, score=25, result_type="knock", knocker=0
        )
        self.assertIn("knock", repr(result))
        self.assertIn("25", repr(result))


class TestGameEdgeCases(unittest.TestCase):

    def test_discard_draw_restriction_enforced(self):
        """Bot that draws from discard cannot discard the same card."""

        class BadBot:
            def draw_decision(self, view):
                return "discard"

            def discard_decision(self, view):
                # Try to discard the last card (just drawn from discard)
                return view.hand[-1]

            def knock_decision(self, view):
                return False

        random.seed(42)
        engine = GameEngine()
        with self.assertRaises(InvalidMoveError):
            engine.play_game(BadBot(), SimpleBot())

    def test_game_state_after_game(self):
        """Game state should reflect the outcome after a game."""
        random.seed(42)
        engine = GameEngine()
        result = engine.play_game(KnockBot(), KnockBot())
        if result.result_type != "draw":
            self.assertEqual(engine.state.winner, result.winner)
            self.assertEqual(engine.state.phase, GamePhase.END)

    def test_engine_reuse(self):
        """Same engine instance can run multiple games."""
        engine = GameEngine()
        for seed in range(10):
            random.seed(seed)
            result = engine.play_game(KnockBot(), SimpleBot())
            self.assertIsInstance(result, GameResult)


if __name__ == "__main__":
    unittest.main()
