"""Tests for meld detection, scoring, and game logic."""

import unittest

from engine.card import Card, Rank, Suit
from engine.rules import (
    calculate_deadwood,
    can_knock,
    find_all_melds,
    find_best_melds,
    find_runs,
    find_sets,
    is_gin,
    is_valid_meld,
    is_valid_run,
    is_valid_set,
    score_hand,
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


class TestValidation(unittest.TestCase):

    def test_valid_set_of_three(self):
        cards = [c("5", "H"), c("5", "D"), c("5", "C")]
        self.assertTrue(is_valid_set(cards))

    def test_valid_set_of_four(self):
        cards = [c("K", "H"), c("K", "D"), c("K", "C"), c("K", "S")]
        self.assertTrue(is_valid_set(cards))

    def test_invalid_set_two_cards(self):
        cards = [c("5", "H"), c("5", "D")]
        self.assertFalse(is_valid_set(cards))

    def test_invalid_set_different_ranks(self):
        cards = [c("5", "H"), c("6", "D"), c("5", "C")]
        self.assertFalse(is_valid_set(cards))

    def test_invalid_set_duplicate_suit(self):
        cards = [c("5", "H"), c("5", "H"), c("5", "C")]
        self.assertFalse(is_valid_set(cards))

    def test_valid_run_three(self):
        cards = [c("3", "H"), c("4", "H"), c("5", "H")]
        self.assertTrue(is_valid_run(cards))

    def test_valid_run_long(self):
        cards = [
            c("A", "S"), c("2", "S"), c("3", "S"),
            c("4", "S"), c("5", "S"),
        ]
        self.assertTrue(is_valid_run(cards))

    def test_valid_run_face_cards(self):
        cards = [c("J", "D"), c("Q", "D"), c("K", "D")]
        self.assertTrue(is_valid_run(cards))

    def test_invalid_run_mixed_suits(self):
        cards = [c("3", "H"), c("4", "D"), c("5", "H")]
        self.assertFalse(is_valid_run(cards))

    def test_invalid_run_not_consecutive(self):
        cards = [c("3", "H"), c("5", "H"), c("7", "H")]
        self.assertFalse(is_valid_run(cards))

    def test_invalid_run_two_cards(self):
        cards = [c("3", "H"), c("4", "H")]
        self.assertFalse(is_valid_run(cards))

    def test_is_valid_meld_set(self):
        cards = [c("7", "H"), c("7", "D"), c("7", "C")]
        self.assertTrue(is_valid_meld(cards))

    def test_is_valid_meld_run(self):
        cards = [c("8", "S"), c("9", "S"), c("10", "S")]
        self.assertTrue(is_valid_meld(cards))


class TestFindMelds(unittest.TestCase):

    def test_find_sets_basic(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"), c("2", "H"),
        ]
        sets = find_sets(hand)
        self.assertEqual(len(sets), 1)
        self.assertTrue(is_valid_set(sets[0]))

    def test_find_sets_four_of_kind(self):
        hand = [
            c("8", "H"), c("8", "D"), c("8", "C"), c("8", "S"),
            c("A", "H"),
        ]
        sets = find_sets(hand)
        # Should find C(4,3)=4 three-card sets + 1 four-card set
        self.assertEqual(len(sets), 5)

    def test_find_sets_none(self):
        hand = [c("A", "H"), c("2", "D"), c("3", "C")]
        sets = find_sets(hand)
        self.assertEqual(len(sets), 0)

    def test_find_runs_basic(self):
        hand = [
            c("3", "H"), c("4", "H"), c("5", "H"),
            c("K", "S"), c("2", "D"),
        ]
        runs = find_runs(hand)
        self.assertTrue(len(runs) >= 1)
        self.assertTrue(any(len(r) == 3 for r in runs))

    def test_find_runs_extended(self):
        hand = [
            c("3", "H"), c("4", "H"), c("5", "H"), c("6", "H"),
        ]
        runs = find_runs(hand)
        # Should find: 3-4-5, 4-5-6, 3-4-5-6
        self.assertEqual(len(runs), 3)

    def test_find_runs_none(self):
        hand = [c("A", "H"), c("5", "H"), c("K", "H")]
        runs = find_runs(hand)
        self.assertEqual(len(runs), 0)

    def test_find_all_melds(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),  # set
            c("8", "S"), c("9", "S"), c("10", "S"),  # run
        ]
        melds = find_all_melds(hand)
        self.assertTrue(len(melds) >= 2)


class TestBestMelds(unittest.TestCase):

    def test_simple_set(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"), c("2", "H"),
        ]
        melds, unmelded = find_best_melds(hand)
        self.assertEqual(len(melds), 1)
        self.assertEqual(len(unmelded), 2)

    def test_two_melds(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"),
            c("K", "H"),
        ]
        melds, unmelded = find_best_melds(hand)
        self.assertEqual(len(melds), 2)
        self.assertEqual(len(unmelded), 1)

    def test_no_melds(self):
        hand = [
            c("A", "H"), c("3", "D"), c("5", "C"),
            c("7", "S"), c("9", "H"),
        ]
        melds, unmelded = find_best_melds(hand)
        self.assertEqual(len(melds), 0)
        self.assertEqual(len(unmelded), 5)

    def test_gin_hand(self):
        # Three sets + a run = all 10 cards melded
        hand = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("9", "H"), c("9", "D"), c("9", "C"),
            c("K", "S"),
        ]
        # This isn't gin since K is unmelded.
        # Let me build a proper gin hand.
        hand = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"),
            c("J", "S"),
        ]
        melds, unmelded = find_best_melds(hand)
        self.assertEqual(len(unmelded), 0)

    def test_overlapping_melds_picks_best(self):
        # Card could be in a set or a run — algorithm picks
        # whichever minimizes deadwood.
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),  # set of 5s
            c("4", "H"), c("6", "H"),                # extends to run
            c("K", "S"), c("Q", "D"),
        ]
        melds, unmelded = find_best_melds(hand)
        # Best: use 5H in the run 4H-5H-6H and set 5D-5C is only 2
        # OR use 5H in set, leaving 4H, 6H unmelded (10+6=16 more)
        # Run uses 5H: set can't form (only 2 fives), unmelded =
        #   5D(5)+5C(5)+KS(10)+QD(10) = 30
        # Set uses 5H: unmelded = 4H(4)+6H(6)+KS(10)+QD(10) = 30
        # Equal, either is fine. Just verify a meld is found.
        total_melded = sum(len(m) for m in melds)
        self.assertTrue(total_melded >= 3)


class TestScoring(unittest.TestCase):

    def test_deadwood_no_melds(self):
        hand = [c("K", "S"), c("Q", "H"), c("J", "D")]
        self.assertEqual(calculate_deadwood(hand), 30)

    def test_deadwood_with_meld(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"),
        ]
        self.assertEqual(calculate_deadwood(hand), 10)

    def test_deadwood_gin(self):
        hand = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"),
            c("J", "S"),
        ]
        self.assertEqual(calculate_deadwood(hand), 0)

    def test_is_gin_true(self):
        hand = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"),
            c("J", "S"),
        ]
        self.assertTrue(is_gin(hand))

    def test_is_gin_false(self):
        hand = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("K", "S"),
        ]
        self.assertFalse(is_gin(hand))

    def test_can_knock_true(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("3", "S"),
        ]
        # Deadwood = 3
        self.assertTrue(can_knock(hand))

    def test_can_knock_at_ten(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"),
        ]
        # Deadwood = 10
        self.assertTrue(can_knock(hand))

    def test_can_knock_false(self):
        hand = [
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("K", "S"), c("2", "H"),
        ]
        # Deadwood = 12
        self.assertFalse(can_knock(hand))

    def test_score_gin(self):
        knocker = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "H"), c("5", "D"), c("5", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"),
            c("J", "S"),
        ]
        defender = [
            c("K", "H"), c("Q", "H"), c("J", "H"),
            c("2", "D"), c("3", "D"), c("4", "D"),
            c("7", "C"), c("8", "C"), c("9", "C"),
            c("6", "D"),
        ]
        # Defender deadwood: 6D = 6
        points, result = score_hand(knocker, defender, is_gin=True)
        self.assertEqual(result, "gin")
        self.assertEqual(points, 6 + 25)

    def test_score_normal_knock(self):
        # Knocker: deadwood 5
        knocker = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("8", "S"), c("9", "S"), c("10", "S"),
            c("5", "H"),  # deadwood
        ]
        # Defender: deadwood 20
        defender = [
            c("2", "H"), c("2", "D"), c("2", "C"),
            c("K", "S"), c("Q", "D"),  # deadwood = 20
        ]
        points, result = score_hand(knocker, defender)
        self.assertEqual(result, "knock")
        self.assertEqual(points, 15)  # 20 - 5

    def test_score_undercut(self):
        # Knocker: deadwood 8
        knocker = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("8", "S"),  # deadwood = 8
        ]
        # Defender: deadwood 5
        defender = [
            c("2", "H"), c("2", "D"), c("2", "C"),
            c("5", "S"),  # deadwood = 5
        ]
        points, result = score_hand(knocker, defender)
        self.assertEqual(result, "undercut")
        # Undercut: -(knocker_dw - defender_dw + 25) = -(8-5+25) = -28
        self.assertEqual(points, -28)

    def test_score_undercut_equal_deadwood(self):
        # Knocker: deadwood 5
        knocker = [
            c("A", "H"), c("A", "D"), c("A", "C"),
            c("5", "S"),
        ]
        # Defender: deadwood 5
        defender = [
            c("2", "H"), c("2", "D"), c("2", "C"),
            c("5", "H"),
        ]
        points, result = score_hand(knocker, defender)
        self.assertEqual(result, "undercut")
        self.assertEqual(points, -25)


class TestMeldPerformance(unittest.TestCase):
    """Tests for meld algorithm performance."""

    def test_complex_hand_meld_performance(self):
        """Test meld finding with many overlapping possibilities."""
        # Worst case: many cards that could be in multiple melds
        # E.g., 3♥ 4♥ 5♥ 6♥ 7♥ 8♥ (many run combinations)
        #       3♠ 3♦ 3♣ (set)
        complex_hand = [
            c("3", "H"), c("4", "H"), c("5", "H"),
            c("6", "H"), c("7", "H"), c("8", "H"),
            c("3", "S"), c("3", "D"), c("3", "C"),
            c("K", "S")  # Deadwood
        ]

        import time
        start = time.time()
        melds, deadwood = find_best_melds(complex_hand)
        elapsed = time.time() - start

        # Should complete quickly even for complex hands
        self.assertLess(elapsed, 1.0,
                       f"Meld finding took {elapsed:.2f}s, expected <1s")
        # Should find good melds
        dw = calculate_deadwood(complex_hand)
        self.assertLessEqual(dw, 10,
                            f"Deadwood {dw} should be ≤10 with good meld finding")

    def test_memoization_effectiveness(self):
        """Test that memoization improves performance on repeated calls."""
        hand = [
            c("3", "H"), c("4", "H"), c("5", "H"),
            c("6", "H"), c("7", "H"), c("3", "S"),
            c("3", "D"), c("K", "S"), c("Q", "D"),
            c("J", "C")
        ]

        import time
        # First call (cache miss)
        start = time.time()
        result1 = find_best_melds(hand)
        first_time = time.time() - start

        # Second call (cache hit)
        start = time.time()
        result2 = find_best_melds(hand)
        second_time = time.time() - start

        # Results should be identical
        self.assertEqual(len(result1[0]), len(result2[0]))
        self.assertEqual(len(result1[1]), len(result2[1]))

        # Second call should be much faster (at least 2x)
        # Note: This might be flaky on very fast systems, but demonstrates caching
        if first_time > 0.001:  # Only check if first call was measurable
            self.assertLess(second_time, first_time * 0.5,
                           f"Cache should speed up repeated calls: "
                           f"first={first_time:.4f}s, second={second_time:.4f}s")


if __name__ == "__main__":
    unittest.main()
