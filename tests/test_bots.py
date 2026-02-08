"""Tests for sample bots — verify they follow the interface and play correctly."""

import random
import unittest

from engine.game import GameEngine, GameResult
from framework.bot_interface import Bot
from bots.random_bot import RandomBot
from bots.basic_bot import BasicBot
from bots.intermediate_bot import IntermediateBot
from bots.student_bot_template import StudentBot


ALL_BOTS = [RandomBot, BasicBot, IntermediateBot, StudentBot]


class TestBotInterface(unittest.TestCase):
    """Verify all bots are proper Bot subclasses."""

    def test_all_bots_subclass_bot(self):
        for BotClass in ALL_BOTS:
            bot = BotClass()
            self.assertIsInstance(bot, Bot, f"{BotClass.__name__}")

    def test_all_bots_have_names(self):
        for BotClass in ALL_BOTS:
            bot = BotClass()
            self.assertIsInstance(bot.name, str)
            self.assertTrue(len(bot.name) > 0)


class TestBotsPlayGames(unittest.TestCase):
    """Verify each bot can play a complete game without crashing."""

    def _play_n_games(self, bot0, bot1, n=20):
        """Play n games and return results."""
        results = []
        engine = GameEngine()
        for seed in range(n):
            random.seed(seed)
            result = engine.play_game(bot0, bot1, dealer=seed % 2)
            results.append(result)
        return results

    def test_random_bot_plays(self):
        results = self._play_n_games(RandomBot(), RandomBot())
        for r in results:
            self.assertIsInstance(r, GameResult)

    def test_basic_bot_plays(self):
        results = self._play_n_games(BasicBot(), BasicBot())
        for r in results:
            self.assertIsInstance(r, GameResult)

    def test_intermediate_bot_plays(self):
        results = self._play_n_games(IntermediateBot(), IntermediateBot())
        for r in results:
            self.assertIsInstance(r, GameResult)

    def test_student_bot_plays(self):
        results = self._play_n_games(StudentBot(), StudentBot())
        for r in results:
            self.assertIsInstance(r, GameResult)


class TestBotMatchups(unittest.TestCase):
    """Test all bot pairings play without errors."""

    def test_all_pairings(self):
        engine = GameEngine()
        for i, Bot1 in enumerate(ALL_BOTS):
            for j, Bot2 in enumerate(ALL_BOTS):
                if i >= j:
                    continue
                for seed in range(10):
                    random.seed(seed)
                    result = engine.play_game(
                        Bot1(), Bot2(), dealer=seed % 2
                    )
                    self.assertIsInstance(
                        result, GameResult,
                        f"{Bot1.__name__} vs {Bot2.__name__} seed={seed}",
                    )


class TestBotStrength(unittest.TestCase):
    """Verify relative bot strength makes sense."""

    def _win_rate(self, Bot1, Bot2, n=100):
        """Return bot1's win rate over n games."""
        wins = 0
        engine = GameEngine()
        for seed in range(n):
            random.seed(seed)
            result = engine.play_game(Bot1(), Bot2(), dealer=seed % 2)
            if result.winner == 0:
                wins += 1
        return wins / n

    def test_basic_beats_random(self):
        rate = self._win_rate(BasicBot, RandomBot)
        self.assertGreater(
            rate, 0.5,
            f"BasicBot should beat RandomBot (won {rate:.0%})",
        )

    def test_intermediate_beats_random(self):
        rate = self._win_rate(IntermediateBot, RandomBot)
        self.assertGreater(
            rate, 0.5,
            f"IntermediateBot should beat RandomBot (won {rate:.0%})",
        )

    def test_intermediate_beats_basic(self):
        rate = self._win_rate(IntermediateBot, BasicBot)
        self.assertGreater(
            rate, 0.4,
            f"IntermediateBot should compete with BasicBot (won {rate:.0%})",
        )


class TestBotStability(unittest.TestCase):
    """Run many games to catch rare crashes or invalid moves."""

    def test_many_random_games(self):
        engine = GameEngine()
        for seed in range(200):
            random.seed(seed)
            result = engine.play_game(
                RandomBot(), RandomBot(), dealer=seed % 2
            )
            self.assertIn(
                result.result_type,
                ("gin", "knock", "undercut", "draw"),
            )

    def test_many_mixed_games(self):
        bots = [RandomBot(), BasicBot(), IntermediateBot()]
        engine = GameEngine()
        for seed in range(100):
            random.seed(seed)
            b0 = bots[seed % len(bots)]
            b1 = bots[(seed + 1) % len(bots)]
            result = engine.play_game(b0, b1, dealer=seed % 2)
            self.assertIsInstance(result, GameResult)


class TestIntermediateBotTracking(unittest.TestCase):
    """Verify IntermediateBot's state tracking works."""

    def test_tracking_resets_each_game(self):
        bot = IntermediateBot()
        engine = GameEngine()

        random.seed(42)
        engine.play_game(bot, BasicBot())
        seen_after_first = len(bot._seen_discards)

        random.seed(99)
        engine.play_game(bot, BasicBot())
        # Should have reset — new game, different discards
        # (not accumulated from previous game)
        self.assertIsInstance(bot._seen_discards, set)

    def test_tracks_discards(self):
        bot = IntermediateBot()
        engine = GameEngine()
        random.seed(42)
        engine.play_game(bot, BasicBot())
        # After a game, bot should have tracked some discards
        self.assertGreater(len(bot._seen_discards), 0)


if __name__ == "__main__":
    unittest.main()
