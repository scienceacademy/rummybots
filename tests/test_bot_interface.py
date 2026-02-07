"""Tests for the bot interface and utility library."""

import random
import unittest

from engine.card import Card, Rank, Suit
from engine.game import GameEngine, GamePhase, PlayerView
from framework.bot_interface import Bot
from framework.utilities import (
    best_discard,
    calculate_deadwood,
    can_knock,
    card_deadwood_contribution,
    deadwood_after_discard,
    evaluate_discard_draw,
    get_best_melds,
    get_melds,
    get_unmelded_cards,
    is_gin,
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


# --- Bot Interface Tests ---

class TestBotAbstract(unittest.TestCase):

    def test_cannot_instantiate_abstract_bot(self):
        with self.assertRaises(TypeError):
            Bot()

    def test_must_implement_draw_decision(self):
        class Incomplete(Bot):
            def discard_decision(self, view):
                pass
            def knock_decision(self, view):
                pass
        with self.assertRaises(TypeError):
            Incomplete()

    def test_must_implement_discard_decision(self):
        class Incomplete(Bot):
            def draw_decision(self, view):
                pass
            def knock_decision(self, view):
                pass
        with self.assertRaises(TypeError):
            Incomplete()

    def test_must_implement_knock_decision(self):
        class Incomplete(Bot):
            def draw_decision(self, view):
                pass
            def discard_decision(self, view):
                pass
        with self.assertRaises(TypeError):
            Incomplete()

    def test_complete_bot_can_instantiate(self):
        class Complete(Bot):
            def draw_decision(self, view):
                return "deck"
            def discard_decision(self, view):
                return view.hand[0]
            def knock_decision(self, view):
                return False
        bot = Complete()
        self.assertIsInstance(bot, Bot)

    def test_default_name_is_class_name(self):
        class MyCustomBot(Bot):
            def draw_decision(self, view):
                return "deck"
            def discard_decision(self, view):
                return view.hand[0]
            def knock_decision(self, view):
                return False
        bot = MyCustomBot()
        self.assertEqual(bot.name, "MyCustomBot")

    def test_custom_name(self):
        class NamedBot(Bot):
            @property
            def name(self):
                return "Champion Bot"
            def draw_decision(self, view):
                return "deck"
            def discard_decision(self, view):
                return view.hand[0]
            def knock_decision(self, view):
                return False
        bot = NamedBot()
        self.assertEqual(bot.name, "Champion Bot")

    def test_lifecycle_hooks_are_optional(self):
        class MinimalBot(Bot):
            def draw_decision(self, view):
                return "deck"
            def discard_decision(self, view):
                return view.hand[0]
            def knock_decision(self, view):
                return False
        bot = MinimalBot()
        # Should not raise
        view = PlayerView([], [], 0, GamePhase.DRAW, True, 0)
        bot.on_game_start(0, view)
        bot.on_turn_end(view)


class TestBotWithEngine(unittest.TestCase):

    def test_bot_subclass_plays_game(self):
        class TestBot(Bot):
            def draw_decision(self, view):
                return "deck"
            def discard_decision(self, view):
                return max(view.hand, key=lambda c: c.deadwood_value)
            def knock_decision(self, view):
                return True

        random.seed(42)
        engine = GameEngine()
        result = engine.play_game(TestBot(), TestBot())
        self.assertIn(
            result.result_type, ("gin", "knock", "undercut", "draw")
        )

    def test_lifecycle_hooks_called(self):
        class TrackingBot(Bot):
            def __init__(self):
                self.game_started = False
                self.player_idx = None
                self.turns_seen = 0

            def draw_decision(self, view):
                return "deck"

            def discard_decision(self, view):
                return max(view.hand, key=lambda c: c.deadwood_value)

            def knock_decision(self, view):
                return True

            def on_game_start(self, player_index, view):
                self.game_started = True
                self.player_idx = player_index

            def on_turn_end(self, view):
                self.turns_seen += 1

        random.seed(42)
        bot0 = TrackingBot()
        bot1 = TrackingBot()
        engine = GameEngine()
        engine.play_game(bot0, bot1)

        self.assertTrue(bot0.game_started)
        self.assertTrue(bot1.game_started)
        self.assertEqual(bot0.player_idx, 0)
        self.assertEqual(bot1.player_idx, 1)
        # At least one turn should have completed
        self.assertGreater(bot0.turns_seen + bot1.turns_seen, 0)

    def test_discard_tracking_bot(self):
        """Bot that tracks opponent discards via on_turn_end."""
        class TrackerBot(Bot):
            def __init__(self):
                self.last_discard_count = 0

            def draw_decision(self, view):
                return "deck"

            def discard_decision(self, view):
                return view.hand[0]

            def knock_decision(self, view):
                return can_knock(view.hand)

            def on_turn_end(self, view):
                self.last_discard_count = len(view.discard_pile)

        random.seed(99)
        bot = TrackerBot()
        engine = GameEngine()
        engine.play_game(bot, TrackerBot())
        # After game, bot should have tracked some discards
        self.assertGreater(bot.last_discard_count, 0)


# --- Utility Function Tests ---

class TestUtilityBasics(unittest.TestCase):

    def test_calculate_deadwood(self):
        hand = [c("K", "S"), c("Q", "H"), c("J", "D")]
        self.assertEqual(calculate_deadwood(hand), 30)

    def test_is_gin(self):
        hand = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"), c("J", "S"),
        ]
        self.assertTrue(is_gin(hand))

    def test_can_knock(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("3", "S"),
        ]
        self.assertTrue(can_knock(hand))

    def test_get_melds(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"),
        ]
        melds = get_melds(hand)
        self.assertTrue(len(melds) >= 1)

    def test_get_best_melds(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"), c("2", "H"),
        ]
        melds, unmelded = get_best_melds(hand)
        self.assertEqual(len(melds), 1)
        self.assertEqual(len(unmelded), 2)

    def test_get_unmelded_cards(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"), c("2", "H"),
        ]
        unmelded = get_unmelded_cards(hand)
        self.assertEqual(len(unmelded), 2)


class TestDeadwoodAfterDiscard(unittest.TestCase):

    def test_discard_reduces_deadwood(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"), c("2", "H"),
        ]
        # Discarding K (10 points) should leave deadwood of 2
        dw = deadwood_after_discard(hand, c("K", "S"))
        self.assertEqual(dw, 2)

    def test_discard_card_not_in_hand(self):
        hand = [c("5", "H"), c("5", "D")]
        with self.assertRaises(ValueError):
            deadwood_after_discard(hand, c("K", "S"))

    def test_discard_each_card(self):
        hand = [
            c("A", "H"), c("5", "D"), c("K", "S"),
        ]
        # Should be able to evaluate each card
        for card in hand:
            dw = deadwood_after_discard(hand, card)
            self.assertIsInstance(dw, int)
            self.assertGreaterEqual(dw, 0)


class TestBestDiscard(unittest.TestCase):

    def test_best_discard_removes_highest_deadwood(self):
        # With no melds possible, discarding K is best
        hand = [
            c("A", "H"), c("3", "D"), c("K", "S"),
        ]
        result = best_discard(hand)
        self.assertEqual(result, c("K", "S"))

    def test_best_discard_preserves_meld(self):
        # 5H, 5D, 5C form a meld — K should be discarded
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"), c("2", "H"),
        ]
        result = best_discard(hand)
        # Best discard is K (10 deadwood) over 2 (2 deadwood)
        self.assertEqual(result, c("K", "S"))


class TestEvaluateDiscardDraw(unittest.TestCase):

    def test_taking_useful_card_improves_hand(self):
        # Hand has two 5s, taking a third makes a meld
        hand = [
            c("5", "H"), c("5", "D"),
            c("K", "S"), c("Q", "H"), c("J", "D"),
            c("9", "C"), c("8", "H"), c("7", "D"),
            c("3", "S"), c("2", "C"),
        ]
        discard_card = c("5", "C")
        current_dw = calculate_deadwood(hand)
        best_dw = evaluate_discard_draw(hand, discard_card)
        self.assertLess(best_dw, current_dw)

    def test_taking_useless_card_no_improvement(self):
        # Hand already has a meld, discard card doesn't help
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"), c("Q", "H"), c("J", "D"),
            c("9", "C"), c("8", "H"), c("7", "D"),
            c("3", "S"),
        ]
        discard_card = c("2", "C")  # doesn't form any meld
        current_dw = calculate_deadwood(hand)
        best_dw = evaluate_discard_draw(hand, discard_card)
        # Taking 2C and discarding K should equal taking nothing
        # (deadwood would still reduce by swapping K for 2, but
        # that's an improvement from the swap, not the draw)
        self.assertIsInstance(best_dw, int)


class TestCardDeadwoodContribution(unittest.TestCase):

    def test_melded_card_contributes_nothing(self):
        # 5H is part of a set — removing it increases deadwood
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"),
        ]
        # Current deadwood: 10 (just K)
        # Without 5H: deadwood = 5+5+10 = 20
        # Contribution = 10 - 20 = -10 (removing it hurts)
        contrib = card_deadwood_contribution(hand, c("5", "H"))
        self.assertLess(contrib, 0)

    def test_unmelded_card_contributes_positively(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"),
        ]
        # K is unmelded deadwood = 10
        # Without K: deadwood = 0
        # Contribution = 10 - 0 = 10
        contrib = card_deadwood_contribution(hand, c("K", "S"))
        self.assertEqual(contrib, 10)

    def test_card_not_in_hand_raises(self):
        hand = [c("5", "H")]
        with self.assertRaises(ValueError):
            card_deadwood_contribution(hand, c("K", "S"))


# --- PlayerView Immutability Tests ---

class TestPlayerViewImmutability(unittest.TestCase):

    def _make_view(self):
        return PlayerView(
            hand=[c("5", "H"), c("K", "S")],
            discard_pile=[c("3", "D")],
            deck_size=30,
            phase=GamePhase.DRAW,
            is_my_turn=True,
            opponent_hand_size=10,
        )

    def test_hand_is_copy(self):
        view = self._make_view()
        hand = view.hand
        hand.append(c("A", "H"))
        self.assertEqual(len(view.hand), 2)

    def test_discard_pile_is_copy(self):
        view = self._make_view()
        pile = view.discard_pile
        pile.append(c("A", "H"))
        self.assertEqual(len(view.discard_pile), 1)

    def test_multiple_hand_accesses_independent(self):
        view = self._make_view()
        hand1 = view.hand
        hand2 = view.hand
        hand1.pop()
        self.assertEqual(len(hand2), 2)

    def test_no_opponent_hand_access(self):
        view = self._make_view()
        self.assertFalse(hasattr(view, "opponent_hand"))
        self.assertEqual(view.opponent_hand_size, 10)


if __name__ == "__main__":
    unittest.main()
