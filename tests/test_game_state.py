"""Tests for GameState and PlayerView."""

import unittest

from engine.card import Card, Rank, Suit
from engine.game import GamePhase, GameState, PlayerView


class TestGameStateSetup(unittest.TestCase):

    def test_setup_deals_correct_cards(self):
        gs = GameState()
        gs.setup(dealer=0)
        self.assertEqual(len(gs.hands[0]), 10)
        self.assertEqual(len(gs.hands[1]), 10)
        self.assertEqual(len(gs.discard_pile), 1)
        # 52 - 10 - 10 - 1 = 31
        self.assertEqual(gs.deck.remaining, 31)

    def test_setup_non_dealer_goes_first(self):
        gs = GameState()
        gs.setup(dealer=0)
        self.assertEqual(gs.current_player, 1)

        gs.setup(dealer=1)
        self.assertEqual(gs.current_player, 0)

    def test_setup_starts_in_draw_phase(self):
        gs = GameState()
        gs.setup()
        self.assertEqual(gs.phase, GamePhase.DRAW)

    def test_setup_no_winner(self):
        gs = GameState()
        gs.setup()
        self.assertIsNone(gs.winner)

    def test_all_cards_unique(self):
        gs = GameState()
        gs.setup()
        all_cards = (
            gs.hands[0]
            + gs.hands[1]
            + gs.discard_pile
        )
        # Plus remaining deck cards
        remaining = gs.deck.deal(gs.deck.remaining)
        all_cards += remaining
        self.assertEqual(len(set(all_cards)), 52)

    def test_setup_resets_state(self):
        gs = GameState()
        gs.setup()
        gs.winner = 0
        gs.score = 50
        gs.setup()
        self.assertIsNone(gs.winner)
        self.assertEqual(gs.score, 0)


class TestPlayerView(unittest.TestCase):

    def test_view_contains_hand(self):
        gs = GameState()
        gs.setup()
        view = gs.get_player_view(0)
        self.assertEqual(len(view.hand), 10)
        self.assertEqual(view.hand, gs.hands[0])

    def test_view_hand_is_copy(self):
        gs = GameState()
        gs.setup()
        view = gs.get_player_view(0)
        view.hand.append(Card(Rank.ACE, Suit.SPADES))
        # Original hand should not be modified
        self.assertEqual(len(gs.hands[0]), 10)

    def test_view_discard_pile_is_copy(self):
        gs = GameState()
        gs.setup()
        view = gs.get_player_view(0)
        original_len = len(gs.discard_pile)
        view.discard_pile.append(Card(Rank.ACE, Suit.SPADES))
        self.assertEqual(len(gs.discard_pile), original_len)

    def test_view_shows_correct_turn(self):
        gs = GameState()
        gs.setup(dealer=0)
        # Player 1 goes first (non-dealer)
        view0 = gs.get_player_view(0)
        view1 = gs.get_player_view(1)
        self.assertFalse(view0.is_my_turn)
        self.assertTrue(view1.is_my_turn)

    def test_view_hides_opponent_hand(self):
        gs = GameState()
        gs.setup()
        view = gs.get_player_view(0)
        # View should have opponent hand SIZE but not cards
        self.assertEqual(view.opponent_hand_size, 10)
        # No direct access to opponent's cards
        self.assertFalse(hasattr(view, 'opponent_hand'))

    def test_view_top_of_discard(self):
        gs = GameState()
        gs.setup()
        view = gs.get_player_view(0)
        self.assertEqual(
            view.top_of_discard,
            gs.discard_pile[-1],
        )

    def test_view_deck_size(self):
        gs = GameState()
        gs.setup()
        view = gs.get_player_view(0)
        self.assertEqual(view.deck_size, 31)

    def test_view_phase(self):
        gs = GameState()
        gs.setup()
        view = gs.get_player_view(0)
        self.assertEqual(view.phase, GamePhase.DRAW)

    def test_empty_discard_top(self):
        view = PlayerView(
            hand=[],
            discard_pile=[],
            deck_size=0,
            phase=GamePhase.DRAW,
            is_my_turn=True,
            opponent_hand_size=0,
        )
        self.assertIsNone(view.top_of_discard)


if __name__ == "__main__":
    unittest.main()
