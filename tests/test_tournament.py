"""Tests for the tournament framework."""

import random
import unittest

from engine.game import GameResult, InvalidMoveError
from framework.bot_interface import Bot
from framework.tournament import (
    BotStats,
    MatchResult,
    format_head_to_head,
    format_rankings,
    load_bots_from_directory,
    run_match,
    run_tournament,
)
from bots.random_bot import RandomBot
from bots.basic_bot import BasicBot
from bots.intermediate_bot import IntermediateBot


# --- Helper bots for testing ---

class CrashDrawBot(Bot):
    """Bot that crashes during draw_decision."""
    @property
    def name(self):
        return "CrashDrawBot"

    def draw_decision(self, view):
        raise RuntimeError("I crashed!")

    def discard_decision(self, view):
        return view.hand[0]

    def knock_decision(self, view):
        return False


class InvalidMoveBot(Bot):
    """Bot that always makes an invalid draw choice."""
    @property
    def name(self):
        return "InvalidMoveBot"

    def draw_decision(self, view):
        return "invalid_choice"

    def discard_decision(self, view):
        return view.hand[0]

    def knock_decision(self, view):
        return False


# --- MatchResult Tests ---

class TestMatchResult(unittest.TestCase):

    def test_record_win(self):
        mr = MatchResult("A", "B")
        result = GameResult(winner=0, score=15, result_type="knock", knocker=0)
        mr.record_game(result, bot0_idx=0)
        self.assertEqual(mr.bot0_wins, 1)
        self.assertEqual(mr.bot1_wins, 0)
        self.assertEqual(mr.bot0_points, 15)
        self.assertEqual(mr.games_played, 1)

    def test_record_loss(self):
        mr = MatchResult("A", "B")
        result = GameResult(winner=1, score=20, result_type="knock", knocker=1)
        mr.record_game(result, bot0_idx=0)
        self.assertEqual(mr.bot0_wins, 0)
        self.assertEqual(mr.bot1_wins, 1)
        self.assertEqual(mr.bot1_points, 20)

    def test_record_draw(self):
        mr = MatchResult("A", "B")
        result = GameResult(winner=None, score=0, result_type="draw")
        mr.record_game(result, bot0_idx=0)
        self.assertEqual(mr.draws, 1)
        self.assertEqual(mr.bot0_wins, 0)
        self.assertEqual(mr.bot1_wins, 0)

    def test_record_gin(self):
        mr = MatchResult("A", "B")
        result = GameResult(winner=0, score=45, result_type="gin", knocker=0)
        mr.record_game(result, bot0_idx=0)
        self.assertEqual(mr.bot0_gins, 1)
        self.assertEqual(mr.bot1_gins, 0)

    def test_record_undercut(self):
        mr = MatchResult("A", "B")
        # Bot1 undercuts Bot0's knock
        result = GameResult(winner=1, score=30, result_type="undercut", knocker=0)
        mr.record_game(result, bot0_idx=0)
        self.assertEqual(mr.bot1_undercuts, 1)

    def test_swapped_player_indices(self):
        mr = MatchResult("A", "B")
        # Bot0 is player index 1 (due to dealer alternation)
        result = GameResult(winner=1, score=10, result_type="knock", knocker=1)
        mr.record_game(result, bot0_idx=1)
        self.assertEqual(mr.bot0_wins, 1)

    def test_win_rate(self):
        mr = MatchResult("A", "B")
        for _ in range(3):
            mr.record_game(GameResult(0, 10, "knock", 0), bot0_idx=0)
        mr.record_game(GameResult(1, 10, "knock", 1), bot0_idx=0)
        self.assertAlmostEqual(mr.bot0_win_rate, 0.75)
        self.assertAlmostEqual(mr.bot1_win_rate, 0.25)

    def test_win_rate_no_games(self):
        mr = MatchResult("A", "B")
        self.assertEqual(mr.bot0_win_rate, 0.0)

    def test_repr(self):
        mr = MatchResult("A", "B")
        self.assertIn("A", repr(mr))
        self.assertIn("B", repr(mr))


# --- BotStats Tests ---

class TestBotStats(unittest.TestCase):

    def test_record_match(self):
        stats = BotStats("TestBot")
        mr = MatchResult("TestBot", "Opponent")
        mr.bot0_wins = 7
        mr.bot1_wins = 3
        mr.draws = 0
        mr.bot0_points = 100
        mr.bot0_gins = 2
        mr.bot0_undercuts = 1
        mr.games_played = 10
        stats.record_match("Opponent", mr, is_bot0=True)

        self.assertEqual(stats.wins, 7)
        self.assertEqual(stats.losses, 3)
        self.assertEqual(stats.total_points, 100)
        self.assertEqual(stats.gins, 2)
        self.assertEqual(stats.head_to_head["Opponent"], (7, 3))

    def test_win_rate(self):
        stats = BotStats("Test")
        stats.wins = 75
        stats.losses = 25
        self.assertAlmostEqual(stats.win_rate, 0.75)

    def test_avg_points(self):
        stats = BotStats("Test")
        stats.total_points = 500
        stats.games_played = 100
        self.assertAlmostEqual(stats.avg_points, 5.0)


# --- run_match Tests ---

class TestRunMatch(unittest.TestCase):

    def test_basic_match(self):
        result = run_match(BasicBot(), BasicBot(), num_games=10, seed=42)
        self.assertEqual(result.games_played, 10)
        self.assertEqual(
            result.bot0_wins + result.bot1_wins + result.draws, 10
        )

    def test_match_with_seed_deterministic(self):
        r1 = run_match(BasicBot(), RandomBot(), num_games=20, seed=123)
        r2 = run_match(BasicBot(), RandomBot(), num_games=20, seed=123)
        self.assertEqual(r1.bot0_wins, r2.bot0_wins)
        self.assertEqual(r1.bot1_wins, r2.bot1_wins)
        self.assertEqual(r1.draws, r2.draws)

    def test_match_handles_crash(self):
        result = run_match(CrashDrawBot(), BasicBot(), num_games=5, seed=42)
        self.assertEqual(result.games_played, 0)
        self.assertEqual(len(result.errors), 5)

    def test_match_handles_invalid_move(self):
        result = run_match(InvalidMoveBot(), BasicBot(), num_games=5, seed=42)
        self.assertEqual(len(result.errors), 5)

    def test_match_alternates_sides(self):
        # After many games, both bots should have been player 0
        result = run_match(BasicBot(), RandomBot(), num_games=20, seed=42)
        # Just verify it completes without error
        self.assertEqual(result.games_played, 20)

    def test_dealer_alternates_in_match(self):
        """Verify dealer alternates between 0 and 1 across games."""
        from unittest.mock import patch
        from engine.game import GameEngine

        dealers_seen = []
        original_play_game = GameEngine.play_game

        def capture_dealer(self, bot0, bot1, dealer=0, rng=None):
            dealers_seen.append(dealer)
            return original_play_game(self, bot0, bot1, dealer=dealer, rng=rng)

        # Patch play_game to capture dealer parameter
        with patch.object(GameEngine, 'play_game', capture_dealer):
            run_match(BasicBot(), BasicBot(), num_games=10, seed=42)

        # Verify alternation: [0, 1, 0, 1, 0, 1, ...]
        expected = [i % 2 for i in range(10)]
        self.assertEqual(dealers_seen, expected,
                        f"Expected dealer alternation {expected}, got {dealers_seen}")


# --- run_tournament Tests ---

class TestRunTournament(unittest.TestCase):

    def test_two_bots(self):
        bots = [BasicBot(), RandomBot()]
        rankings, matches = run_tournament(
            bots, games_per_match=10, seed=42, verbose=False
        )
        self.assertEqual(len(rankings), 2)
        self.assertEqual(len(matches), 1)  # C(2,2) = 1

    def test_three_bots(self):
        bots = [BasicBot(), RandomBot(), IntermediateBot()]
        rankings, matches = run_tournament(
            bots, games_per_match=10, seed=42, verbose=False
        )
        self.assertEqual(len(rankings), 3)
        self.assertEqual(len(matches), 3)  # C(3,2) = 3

    def test_rankings_sorted_by_win_rate(self):
        bots = [RandomBot(), BasicBot(), IntermediateBot()]
        rankings, _ = run_tournament(
            bots, games_per_match=50, seed=42, verbose=False
        )
        # Rankings should be descending by win rate
        for i in range(len(rankings) - 1):
            self.assertGreaterEqual(
                rankings[i].win_rate, rankings[i + 1].win_rate
            )

    def test_tournament_deterministic(self):
        bots1 = [BasicBot(), RandomBot()]
        bots2 = [BasicBot(), RandomBot()]
        r1, _ = run_tournament(bots1, games_per_match=20, seed=99, verbose=False)
        r2, _ = run_tournament(bots2, games_per_match=20, seed=99, verbose=False)
        self.assertEqual(r1[0].wins, r2[0].wins)
        self.assertEqual(r1[1].wins, r2[1].wins)

    def test_head_to_head_populated(self):
        bots = [BasicBot(), RandomBot(), IntermediateBot()]
        rankings, _ = run_tournament(
            bots, games_per_match=10, seed=42, verbose=False
        )
        for s in rankings:
            # Each bot should have h2h against 2 opponents
            self.assertEqual(len(s.head_to_head), 2)

    def test_too_few_bots(self):
        with self.assertRaises(ValueError):
            run_tournament([BasicBot()], verbose=False)

    def test_duplicate_names_rejected(self):
        with self.assertRaises(ValueError):
            run_tournament(
                [BasicBot(), BasicBot()], verbose=False
            )

    def test_error_handling_in_tournament(self):
        bots = [BasicBot(), CrashDrawBot()]
        rankings, matches = run_tournament(
            bots, games_per_match=5, seed=42, verbose=False
        )
        self.assertEqual(len(rankings), 2)
        # CrashDrawBot should have errors
        crash_stats = next(s for s in rankings if s.name == "CrashDrawBot")
        self.assertGreater(crash_stats.errors, 0)


# --- Formatting Tests ---

class TestFormatting(unittest.TestCase):

    def test_format_rankings(self):
        bots = [BasicBot(), RandomBot()]
        rankings, _ = run_tournament(
            bots, games_per_match=10, seed=42, verbose=False
        )
        output = format_rankings(rankings)
        self.assertIn("TOURNAMENT RESULTS", output)
        self.assertIn("BasicBot", output)
        self.assertIn("RandomBot", output)

    def test_format_head_to_head(self):
        bots = [BasicBot(), RandomBot()]
        rankings, _ = run_tournament(
            bots, games_per_match=10, seed=42, verbose=False
        )
        output = format_head_to_head(rankings)
        self.assertIn("HEAD-TO-HEAD", output)
        self.assertIn("vs", output)


# --- Bot Loading Tests ---

class TestLoadBots(unittest.TestCase):

    def test_load_from_bots_directory(self):
        bots = load_bots_from_directory("bots")
        self.assertGreaterEqual(len(bots), 3)
        names = [b.name for b in bots]
        self.assertIn("BasicBot", names)
        self.assertIn("RandomBot", names)
        self.assertIn("IntermediateBot", names)

    def test_excludes_template(self):
        bots = load_bots_from_directory("bots")
        names = [b.name for b in bots]
        self.assertNotIn("StudentBot", names)

    def test_nonexistent_directory(self):
        with self.assertRaises(FileNotFoundError):
            load_bots_from_directory("nonexistent_dir")


if __name__ == "__main__":
    unittest.main()
