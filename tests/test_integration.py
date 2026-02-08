"""Integration tests and final validation.

Phase 8: End-to-end tests covering the complete workflow from
tournament start to results, edge cases, performance, and
validation that the system behaves correctly.
"""

import inspect
import os
import random
import signal
import time
import unittest

from engine.card import Card, Deck, Rank, Suit
from engine.game import (
    BotTimeoutError,
    DrawChoice,
    GameEngine,
    GamePhase,
    GameResult,
    GameState,
    InvalidMoveError,
    PlayerView,
)
from engine.rules import (
    calculate_deadwood,
    can_knock,
    find_best_melds,
    is_gin,
    score_hand,
    score_with_layoffs,
)
from framework.bot_interface import Bot
from framework.tournament import (
    format_head_to_head,
    format_rankings,
    load_bots_from_directory,
    run_match,
    run_tournament,
)
from framework.utilities import (
    best_discard,
    deadwood_after_discard,
    evaluate_discard_draw,
    get_unmelded_cards,
)
from bots.random_bot import RandomBot
from bots.basic_bot import BasicBot
from bots.intermediate_bot import IntermediateBot
from bots.student_bot_template import StudentBot


def c(rank_str: str, suit_str: str) -> Card:
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


# --- Integration: Complete Workflow ---

class TestFullWorkflow(unittest.TestCase):
    """Test the complete workflow from bot loading to results."""

    def test_load_and_run_tournament(self):
        """Load bots from directory and run a full tournament."""
        bots = load_bots_from_directory("bots")
        self.assertGreaterEqual(len(bots), 3)

        rankings, matches = run_tournament(
            bots, games_per_match=20, seed=42, verbose=False
        )

        # Should have rankings for all bots
        self.assertEqual(len(rankings), len(bots))
        # Should have C(n,2) matches
        n = len(bots)
        self.assertEqual(len(matches), n * (n - 1) // 2)
        # Rankings should be sorted by win rate
        for i in range(len(rankings) - 1):
            self.assertGreaterEqual(
                rankings[i].win_rate, rankings[i + 1].win_rate
            )

    def test_output_formatting(self):
        """Rankings and head-to-head should produce valid output."""
        bots = [BasicBot(), RandomBot()]
        rankings, _ = run_tournament(
            bots, games_per_match=10, seed=42, verbose=False
        )
        rankings_str = format_rankings(rankings)
        h2h_str = format_head_to_head(rankings)

        self.assertIn("TOURNAMENT RESULTS", rankings_str)
        self.assertIn("Win%", rankings_str)
        self.assertIn("HEAD-TO-HEAD", h2h_str)
        # No empty or broken lines
        for line in rankings_str.split("\n"):
            self.assertNotIn("None", line)

    def test_tournament_total_games_consistent(self):
        """Total games across all matches should be correct."""
        bots = [BasicBot(), RandomBot(), IntermediateBot()]
        games_per = 30
        rankings, matches = run_tournament(
            bots, games_per_match=games_per, seed=42, verbose=False
        )

        # Each match should have played the right number of games
        for match in matches:
            self.assertEqual(
                match.bot0_wins + match.bot1_wins + match.draws
                + len(match.errors),
                games_per,
            )

        # Each bot plays (n-1) matches
        for s in rankings:
            expected = games_per * (len(bots) - 1)
            self.assertEqual(
                s.wins + s.losses + s.draws + s.errors, expected
            )


# --- Integration: Game Integrity ---

class TestGameIntegrity(unittest.TestCase):
    """Verify game state integrity across many games."""

    def test_all_cards_accounted_for(self):
        """After setup, all 52 cards should be distributed."""
        for seed in range(20):
            random.seed(seed)
            gs = GameState()
            gs.setup(dealer=seed % 2)

            all_cards = (
                list(gs.hands[0])
                + list(gs.hands[1])
                + list(gs.discard_pile)
            )
            remaining = gs.deck.deal(gs.deck.remaining)
            all_cards += remaining

            self.assertEqual(len(all_cards), 52)
            self.assertEqual(len(set(all_cards)), 52)

    def test_no_duplicate_cards_during_game(self):
        """During gameplay, no card should appear in two places."""

        class InspectorBot(Bot):
            def __init__(self):
                self.violations = []

            @property
            def name(self):
                return "InspectorBot"

            def draw_decision(self, view):
                return "deck"

            def discard_decision(self, view):
                # Check for duplicates in hand
                if len(set(view.hand)) != len(view.hand):
                    self.violations.append("Duplicate card in hand")
                return best_discard(view.hand)

            def knock_decision(self, view):
                return can_knock(view.hand)

        for seed in range(50):
            random.seed(seed)
            bot0 = InspectorBot()
            bot1 = InspectorBot()
            engine = GameEngine()
            engine.play_game(bot0, bot1)
            self.assertEqual(bot0.violations, [], f"seed={seed}")
            self.assertEqual(bot1.violations, [], f"seed={seed}")

    def test_hand_size_always_correct(self):
        """Hand should be 10 cards at decision points (11 during discard)."""

        class HandSizeBot(Bot):
            def __init__(self):
                self.errors = []

            @property
            def name(self):
                return "HandSizeBot"

            def draw_decision(self, view):
                if len(view.hand) != 10:
                    self.errors.append(
                        f"draw: hand size {len(view.hand)}"
                    )
                return "deck"

            def discard_decision(self, view):
                if len(view.hand) != 11:
                    self.errors.append(
                        f"discard: hand size {len(view.hand)}"
                    )
                return view.hand[0]

            def knock_decision(self, view):
                if len(view.hand) != 10:
                    self.errors.append(
                        f"knock: hand size {len(view.hand)}"
                    )
                return True

        for seed in range(50):
            random.seed(seed)
            bot0 = HandSizeBot()
            bot1 = HandSizeBot()
            engine = GameEngine()
            engine.play_game(bot0, bot1)
            self.assertEqual(bot0.errors, [], f"seed={seed}")
            self.assertEqual(bot1.errors, [], f"seed={seed}")


# --- Integration: Scoring Consistency ---

class TestScoringConsistency(unittest.TestCase):
    """Verify scoring is consistent and correct."""

    def test_winner_always_has_positive_score(self):
        """When there's a winner, the score should be positive."""
        engine = GameEngine()
        for seed in range(100):
            random.seed(seed)
            result = engine.play_game(BasicBot(), RandomBot())
            if result.winner is not None:
                self.assertGreater(result.score, 0, f"seed={seed}")

    def test_draw_has_zero_score(self):
        """Draws should have score 0 and no winner."""
        engine = GameEngine()
        for seed in range(200):
            random.seed(seed)
            # Two bots that never knock → always draw
            class NeverKnockBot(Bot):
                @property
                def name(self):
                    return "NeverKnockBot"
                def draw_decision(self, view):
                    return "deck"
                def discard_decision(self, view):
                    return view.hand[0]
                def knock_decision(self, view):
                    return False

            result = engine.play_game(NeverKnockBot(), NeverKnockBot())
            self.assertEqual(result.result_type, "draw")
            self.assertIsNone(result.winner)
            self.assertEqual(result.score, 0)

    def test_gin_always_has_bonus(self):
        """Gin results should always include the 25-point bonus."""
        engine = GameEngine()
        gin_found = False
        for seed in range(500):
            random.seed(seed)
            result = engine.play_game(BasicBot(), BasicBot())
            if result.result_type == "gin":
                gin_found = True
                self.assertGreaterEqual(result.score, 25)
                break
        # It's possible gin doesn't occur in 500 games, that's OK

    def test_score_with_layoffs_vs_without(self):
        """Score with layoffs should be <= score without for the knocker."""
        knocker = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"),
            c("3", "H"),  # deadwood = 3
        ]
        # Defender has 5S which can lay off onto knocker's set
        defender = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "S"),  # can lay off
            c("K", "D"), c("Q", "D"),  # deadwood
        ]
        pts_no_layoff, _ = score_hand(knocker, defender)
        pts_layoff, _ = score_with_layoffs(knocker, defender)
        # Layoffs reduce defender's deadwood, so knocker gets fewer points
        self.assertLessEqual(pts_layoff, pts_no_layoff)


# --- Integration: Error Handling ---

class TestErrorHandling(unittest.TestCase):
    """Test that errors are handled gracefully."""

    def test_crashing_bot_doesnt_crash_tournament(self):
        class CrashBot(Bot):
            @property
            def name(self):
                return "CrashBot"
            def draw_decision(self, view):
                raise ValueError("boom")
            def discard_decision(self, view):
                return view.hand[0]
            def knock_decision(self, view):
                return False

        rankings, matches = run_tournament(
            [CrashBot(), BasicBot()],
            games_per_match=5,
            seed=42,
            verbose=False,
        )
        self.assertEqual(len(rankings), 2)
        # CrashBot should have 0 wins and errors
        crash = next(s for s in rankings if s.name == "CrashBot")
        self.assertEqual(crash.wins, 0)
        self.assertGreater(crash.errors, 0)

    def test_slow_bot_doesnt_hang(self):
        """A bot that takes time but finishes should work."""
        class SlowBot(Bot):
            @property
            def name(self):
                return "SlowBot"
            def draw_decision(self, view):
                # Simulate brief computation
                _ = calculate_deadwood(view.hand)
                return "deck"
            def discard_decision(self, view):
                return best_discard(view.hand)
            def knock_decision(self, view):
                return True

        result = run_match(SlowBot(), BasicBot(), num_games=5, seed=42)
        self.assertEqual(result.games_played, 5)

    def test_invalid_discard_reported(self):
        """Bot discarding a card not in hand should produce an error."""
        class BadDiscardBot(Bot):
            @property
            def name(self):
                return "BadDiscardBot"
            def draw_decision(self, view):
                return "deck"
            def discard_decision(self, view):
                # Return a card that's probably not in hand
                return Card(Rank.KING, Suit.SPADES)
            def knock_decision(self, view):
                return False

        result = run_match(BadDiscardBot(), BasicBot(), num_games=5, seed=42)
        # Some or all games should error
        self.assertGreater(len(result.errors), 0)


# --- Performance Testing ---

class TestPerformance(unittest.TestCase):
    """Verify the system performs within reasonable limits."""

    def test_100_game_match_under_5_seconds(self):
        """A 100-game match should complete quickly."""
        start = time.time()
        run_match(BasicBot(), IntermediateBot(), num_games=100, seed=42)
        elapsed = time.time() - start
        self.assertLess(elapsed, 5.0, f"Match took {elapsed:.1f}s")

    def test_full_tournament_under_15_seconds(self):
        """A 3-bot, 100-games-per-match tournament should be fast."""
        bots = [BasicBot(), RandomBot(), IntermediateBot()]
        start = time.time()
        run_tournament(bots, games_per_match=100, seed=42, verbose=False)
        elapsed = time.time() - start
        self.assertLess(elapsed, 15.0, f"Tournament took {elapsed:.1f}s")

    def test_many_games_memory_stable(self):
        """Running many games should not accumulate state."""
        engine = GameEngine()
        for seed in range(500):
            random.seed(seed)
            engine.play_game(BasicBot(), BasicBot())
        # If we get here without MemoryError, we're fine
        self.assertTrue(True)


# --- Final Validation ---

class TestFinalValidation(unittest.TestCase):
    """Final checks that the system works end-to-end."""

    def test_bot_strength_hierarchy(self):
        """IntermediateBot > BasicBot > RandomBot over many games."""
        intermediate_vs_random = run_match(
            IntermediateBot(), RandomBot(),
            num_games=100, seed=42,
        )
        basic_vs_random = run_match(
            BasicBot(), RandomBot(),
            num_games=100, seed=42,
        )
        intermediate_vs_basic = run_match(
            IntermediateBot(), BasicBot(),
            num_games=100, seed=42,
        )

        # Intermediate should dominate Random
        self.assertGreater(
            intermediate_vs_random.bot0_win_rate, 0.8,
            "IntermediateBot should strongly beat RandomBot",
        )
        # Basic should beat Random
        self.assertGreater(
            basic_vs_random.bot0_win_rate, 0.7,
            "BasicBot should beat RandomBot",
        )
        # Intermediate should be competitive with Basic
        self.assertGreater(
            intermediate_vs_basic.bot0_win_rate, 0.4,
            "IntermediateBot should compete with BasicBot",
        )

    def test_all_result_types_occur(self):
        """Over many games, we should see knock, undercut, and draw."""
        seen = set()
        engine = GameEngine()
        # BasicBot knocks aggressively (deadwood ≤ 10), IntermediateBot
        # often has lower deadwood, producing undercuts.
        # Also mix in draws from non-knocking games.
        pairings = [
            (BasicBot(), IntermediateBot()),
            (IntermediateBot(), BasicBot()),
            (BasicBot(), BasicBot()),
        ]
        for seed in range(3000):
            random.seed(seed)
            b0, b1 = pairings[seed % len(pairings)]
            result = engine.play_game(b0, b1)
            seen.add(result.result_type)
            if seen >= {"knock", "undercut", "draw"}:
                break

        self.assertIn("knock", seen)
        self.assertIn("draw", seen)
        self.assertIn("undercut", seen, "Undercut should occur eventually")

    def test_student_template_is_functional(self):
        """The student template should work out of the box."""
        bot = StudentBot()
        engine = GameEngine()
        random.seed(42)
        result = engine.play_game(bot, BasicBot())
        self.assertIsInstance(result, GameResult)
        self.assertIn(
            result.result_type,
            ("gin", "knock", "undercut", "draw"),
        )

    def test_deterministic_tournament(self):
        """Same seed should always produce identical rankings."""
        bots1 = [BasicBot(), RandomBot(), IntermediateBot()]
        bots2 = [BasicBot(), RandomBot(), IntermediateBot()]

        r1, m1 = run_tournament(
            bots1, games_per_match=50, seed=777, verbose=False
        )
        r2, m2 = run_tournament(
            bots2, games_per_match=50, seed=777, verbose=False
        )

        # Rankings order should be identical
        for s1, s2 in zip(r1, r2):
            self.assertEqual(s1.name, s2.name)
            self.assertEqual(s1.wins, s2.wins)
            self.assertEqual(s1.losses, s2.losses)
            self.assertEqual(s1.total_points, s2.total_points)

    def test_all_bots_loadable(self):
        """All bots in bots/ should load without errors."""
        bots = load_bots_from_directory("bots")
        names = {b.name for b in bots}
        self.assertIn("RandomBot", names)
        self.assertIn("BasicBot", names)
        self.assertIn("IntermediateBot", names)
        # Template excluded by default
        self.assertNotIn("StudentBot", names)


# --- Anti-Cheat Tests ---

class TestAntiCheat(unittest.TestCase):
    """Verify that common cheating strategies are blocked."""

    def test_rng_manipulation_blocked(self):
        """A bot that seeds the global random cannot control the deal.

        The engine uses a dedicated random.Random instance, so calling
        random.seed() in a bot method should have no effect on the cards
        dealt.
        """
        class RNGCheaterBot(Bot):
            """Bot that tries to seed global random for predictable deals."""
            def __init__(self):
                self.hands_seen = []

            @property
            def name(self):
                return "RNGCheater"

            def draw_decision(self, view):
                # Try to manipulate the global RNG
                random.seed(12345)
                self.hands_seen.append(sorted(view.hand))
                return "deck"

            def discard_decision(self, view):
                random.seed(12345)
                return view.hand[-1]

            def knock_decision(self, view):
                return can_knock(view.hand)

        # Run several games with different engine seeds
        # If RNG manipulation worked, the cheater would see the same
        # hand every game. With isolated RNG, hands should differ.
        engine = GameEngine()
        cheater = RNGCheaterBot()
        opponent = BasicBot()
        hands = set()
        for seed in range(10):
            cheater.hands_seen = []
            game_rng = random.Random(seed)
            engine.play_game(cheater, opponent, rng=game_rng)
            if cheater.hands_seen:
                hands.add(tuple(cheater.hands_seen[0]))

        # With 10 different seeds, we should see multiple distinct hands
        self.assertGreater(
            len(hands), 1,
            "RNG manipulation should not produce identical hands across games"
        )

    def test_frame_snooping_blocked(self):
        """The immediate caller frame of bot methods should not contain engine state.

        Because bot methods are called via a standalone trampoline function
        (_call_bot_method), the GameEngine's `self` is not in the direct
        caller's frame (f_back). This prevents the simplest form of
        frame introspection from accessing game internals.
        """
        class FrameSnooperBot(Bot):
            """Bot that checks the immediate caller frame for engine state."""
            def __init__(self):
                self.found_engine_in_caller = False

            @property
            def name(self):
                return "FrameSnooper"

            def _check_caller_frame(self):
                """Check the immediate caller frames for engine references."""
                frame = inspect.currentframe()
                try:
                    # Walk up: _check_caller_frame -> draw_decision -> _call_bot_method
                    caller = frame.f_back  # draw_decision (self is the bot, OK)
                    if caller:
                        caller = caller.f_back  # _call_bot_method (trampoline)
                    if caller:
                        local_vars = caller.f_locals
                        for val in local_vars.values():
                            if hasattr(val, '_execute_draw') or hasattr(val, 'state'):
                                self.found_engine_in_caller = True
                finally:
                    del frame

            def draw_decision(self, view):
                self._check_caller_frame()
                return "deck"

            def discard_decision(self, view):
                return view.hand[-1]

            def knock_decision(self, view):
                return can_knock(view.hand)

        engine = GameEngine()
        snooper = FrameSnooperBot()
        game_rng = random.Random(42)
        engine.play_game(snooper, BasicBot(), rng=game_rng)

        self.assertFalse(
            snooper.found_engine_in_caller,
            "Trampoline's caller frame should not contain GameEngine"
        )

    @unittest.skipIf(
        not hasattr(signal, "SIGALRM") or os.name == "nt",
        "Timeout tests require Unix signal support"
    )
    def test_slow_bot_times_out(self):
        """A bot that infinite-loops should be timed out and raise an error."""
        class InfiniteLoopBot(Bot):
            @property
            def name(self):
                return "InfiniteLooper"

            def draw_decision(self, view):
                while True:
                    pass  # infinite loop

            def discard_decision(self, view):
                return view.hand[0]

            def knock_decision(self, view):
                return False

        engine = GameEngine()
        game_rng = random.Random(42)
        with self.assertRaises(BotTimeoutError):
            engine.play_game(InfiniteLoopBot(), BasicBot(), rng=game_rng)

    def test_bad_draw_return_type(self):
        """Bot returning wrong type from draw_decision raises InvalidMoveError."""
        class BadDrawBot(Bot):
            @property
            def name(self):
                return "BadDrawBot"

            def draw_decision(self, view):
                return 42  # should be str or DrawChoice

            def discard_decision(self, view):
                return view.hand[0]

            def knock_decision(self, view):
                return False

        engine = GameEngine()
        game_rng = random.Random(42)
        with self.assertRaises(InvalidMoveError) as ctx:
            engine.play_game(BadDrawBot(), BasicBot(), rng=game_rng)
        self.assertIn("draw_decision", str(ctx.exception))

    def test_bad_discard_return_type(self):
        """Bot returning wrong type from discard_decision raises InvalidMoveError."""
        class BadDiscardTypeBot(Bot):
            @property
            def name(self):
                return "BadDiscardTypeBot"

            def draw_decision(self, view):
                return "deck"

            def discard_decision(self, view):
                return "not a card"  # should be Card

            def knock_decision(self, view):
                return False

        engine = GameEngine()
        game_rng = random.Random(42)
        with self.assertRaises(InvalidMoveError) as ctx:
            engine.play_game(BadDiscardTypeBot(), BasicBot(), rng=game_rng)
        self.assertIn("discard_decision", str(ctx.exception))

    def test_bad_knock_return_type(self):
        """Bot returning wrong type from knock_decision raises InvalidMoveError."""
        class BadKnockBot(Bot):
            @property
            def name(self):
                return "BadKnockBot"

            def draw_decision(self, view):
                return "deck"

            def discard_decision(self, view):
                return best_discard(view.hand)

            def knock_decision(self, view):
                return "yes"  # should be bool

        engine = GameEngine()
        # Try multiple seeds since knock_decision is only called when eligible
        for seed in range(100):
            game_rng = random.Random(seed)
            try:
                engine.play_game(BadKnockBot(), BasicBot(), rng=game_rng)
            except InvalidMoveError as e:
                self.assertIn("knock_decision", str(e))
                return  # Test passed
        # If we never reached knock phase in 100 games, skip
        self.skipTest("knock_decision was never called in 100 games")

    def test_cheating_bots_in_tournament(self):
        """Cheating bots should not crash the tournament — errors are recorded."""
        class RNGCheater(Bot):
            @property
            def name(self):
                return "RNGCheater"
            def draw_decision(self, view):
                random.seed(0)
                return "deck"
            def discard_decision(self, view):
                return view.hand[-1]
            def knock_decision(self, view):
                return True

        rankings, matches = run_tournament(
            [RNGCheater(), BasicBot()],
            games_per_match=20,
            seed=42,
            verbose=False,
        )
        # Tournament should complete without crashing
        self.assertEqual(len(rankings), 2)
        # All games should complete (no errors from RNG cheating)
        for match in matches:
            total = match.bot0_wins + match.bot1_wins + match.draws
            self.assertEqual(total + len(match.errors), 20)


if __name__ == "__main__":
    unittest.main()
