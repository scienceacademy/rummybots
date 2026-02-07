"""Tests for Card and Deck classes."""

import unittest

from engine.card import Card, Deck, Rank, Suit


class TestCard(unittest.TestCase):

    def test_creation(self):
        card = Card(Rank.ACE, Suit.SPADES)
        self.assertEqual(card.rank, Rank.ACE)
        self.assertEqual(card.suit, Suit.SPADES)

    def test_str(self):
        self.assertEqual(str(Card(Rank.ACE, Suit.SPADES)), "AS")
        self.assertEqual(str(Card(Rank.TEN, Suit.HEARTS)), "10H")
        self.assertEqual(str(Card(Rank.KING, Suit.DIAMONDS)), "KD")
        self.assertEqual(str(Card(Rank.QUEEN, Suit.CLUBS)), "QC")

    def test_repr(self):
        card = Card(Rank.JACK, Suit.HEARTS)
        self.assertEqual(repr(card), "Card(JH)")

    def test_equality(self):
        c1 = Card(Rank.FIVE, Suit.HEARTS)
        c2 = Card(Rank.FIVE, Suit.HEARTS)
        c3 = Card(Rank.FIVE, Suit.CLUBS)
        self.assertEqual(c1, c2)
        self.assertNotEqual(c1, c3)

    def test_equality_different_type(self):
        card = Card(Rank.ACE, Suit.SPADES)
        self.assertNotEqual(card, "AS")
        self.assertNotEqual(card, 1)

    def test_hash(self):
        c1 = Card(Rank.FIVE, Suit.HEARTS)
        c2 = Card(Rank.FIVE, Suit.HEARTS)
        self.assertEqual(hash(c1), hash(c2))
        # Cards can be used in sets/dicts
        s = {c1, c2}
        self.assertEqual(len(s), 1)

    def test_comparison(self):
        low = Card(Rank.TWO, Suit.CLUBS)
        high = Card(Rank.KING, Suit.CLUBS)
        self.assertTrue(low < high)
        self.assertTrue(high > low)
        self.assertTrue(low <= high)
        self.assertTrue(high >= low)
        self.assertTrue(low <= Card(Rank.TWO, Suit.CLUBS))
        self.assertTrue(low >= Card(Rank.TWO, Suit.CLUBS))

    def test_sorting(self):
        cards = [
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.FIVE, Suit.HEARTS),
        ]
        sorted_cards = sorted(cards)
        self.assertEqual(sorted_cards[0].rank, Rank.ACE)
        self.assertEqual(sorted_cards[1].rank, Rank.FIVE)
        self.assertEqual(sorted_cards[2].rank, Rank.KING)

    def test_deadwood_value_ace(self):
        card = Card(Rank.ACE, Suit.SPADES)
        self.assertEqual(card.deadwood_value, 1)

    def test_deadwood_value_number_cards(self):
        for rank in [Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE,
                     Rank.SIX, Rank.SEVEN, Rank.EIGHT, Rank.NINE]:
            card = Card(rank, Suit.HEARTS)
            self.assertEqual(card.deadwood_value, rank.value)

    def test_deadwood_value_ten(self):
        card = Card(Rank.TEN, Suit.DIAMONDS)
        self.assertEqual(card.deadwood_value, 10)

    def test_deadwood_value_face_cards(self):
        for rank in [Rank.JACK, Rank.QUEEN, Rank.KING]:
            card = Card(rank, Suit.CLUBS)
            self.assertEqual(card.deadwood_value, 10)


class TestDeck(unittest.TestCase):

    def test_deck_has_52_cards(self):
        deck = Deck()
        self.assertEqual(deck.remaining, 52)
        self.assertEqual(len(deck), 52)

    def test_deck_contains_all_cards(self):
        deck = Deck()
        cards = deck.deal(52)
        # Check all 52 unique cards are present
        card_set = set(cards)
        self.assertEqual(len(card_set), 52)
        # Check every suit/rank combo exists
        for suit in Suit:
            for rank in Rank:
                self.assertIn(Card(rank, suit), card_set)

    def test_draw_returns_card(self):
        deck = Deck()
        card = deck.draw()
        self.assertIsInstance(card, Card)
        self.assertEqual(deck.remaining, 51)

    def test_draw_from_empty_deck(self):
        deck = Deck()
        deck.deal(52)
        with self.assertRaises(IndexError):
            deck.draw()

    def test_deal(self):
        deck = Deck()
        hand = deck.deal(10)
        self.assertEqual(len(hand), 10)
        self.assertEqual(deck.remaining, 42)

    def test_deal_too_many(self):
        deck = Deck()
        with self.assertRaises(ValueError):
            deck.deal(53)

    def test_deal_exact_remaining(self):
        deck = Deck()
        cards = deck.deal(52)
        self.assertEqual(len(cards), 52)
        self.assertTrue(deck.is_empty())

    def test_is_empty(self):
        deck = Deck()
        self.assertFalse(deck.is_empty())
        deck.deal(52)
        self.assertTrue(deck.is_empty())

    def test_shuffle_changes_order(self):
        """Shuffle should produce a different order (with very high
        probability)."""
        import random
        random.seed(42)
        deck1 = Deck()
        cards1 = deck1.deal(52)

        random.seed(99)
        deck2 = Deck()
        cards2 = deck2.deal(52)

        # Extremely unlikely to be identical with different seeds
        self.assertNotEqual(cards1, cards2)

    def test_multiple_draws_deplete_deck(self):
        deck = Deck()
        for i in range(52):
            deck.draw()
            self.assertEqual(deck.remaining, 51 - i)
        self.assertTrue(deck.is_empty())

    def test_dealt_cards_are_unique(self):
        deck = Deck()
        cards = []
        for _ in range(52):
            cards.append(deck.draw())
        # All cards should be unique
        self.assertEqual(len(set(cards)), 52)


if __name__ == "__main__":
    unittest.main()
