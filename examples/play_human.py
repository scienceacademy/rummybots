"""Play a game of Gin Rummy against a bot.

Usage:
    python examples/play_human.py bots/random_bot.py
    python examples/play_human.py bots/basic_bot.py
"""

import importlib.util
import inspect
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.card import Card, Rank, Suit, RANK_NAMES
from engine.game import GameEngine, GamePhase, PlayerView
from engine.rules import calculate_deadwood, find_best_melds, can_knock
from framework.bot_interface import Bot

import engine.game
# Disable the signal-based timeout so human input doesn't get killed
engine.game._HAS_SIGALRM = False


# Reverse lookup: string -> Rank
_RANK_LOOKUP = {v: k for k, v in RANK_NAMES.items()}

# Reverse lookup: string -> Suit
_SUIT_LOOKUP = {s.value: s for s in Suit}


def parse_card(text):
    """Parse a card string like '5H', '10S', 'KD', 'AC' into a Card object."""
    text = text.strip().upper()
    if len(text) < 2:
        return None
    suit_char = text[-1]
    rank_str = text[:-1]
    rank = _RANK_LOOKUP.get(rank_str)
    suit = _SUIT_LOOKUP.get(suit_char)
    if rank is None or suit is None:
        return None
    return Card(rank, suit)


def format_hand(hand):
    """Format a hand grouped by melds first, then unmelded by suit/rank.

    Returns (display_string, melds, unmelded) where display_string looks like:
        (3H 4H 5H)  (9C 9D 9S)  | 2D  7S  KC  QH
    """
    melds, unmelded = find_best_melds(hand)
    unmelded = sorted(unmelded, key=lambda c: (c.suit.value, c.rank.value))
    parts = []
    for meld in melds:
        sorted_meld = sorted(meld, key=lambda c: (c.suit.value, c.rank.value))
        parts.append("(" + " ".join(str(c) for c in sorted_meld) + ")")
    meld_str = "  ".join(parts)
    unmelded_str = "  ".join(str(c) for c in unmelded)
    if meld_str and unmelded_str:
        display = f"{meld_str}  |  {unmelded_str}"
    elif meld_str:
        display = meld_str
    else:
        display = unmelded_str
    return display, melds, unmelded


def print_state(view):
    """Print the current game state for the human player."""
    print()
    print(f"  {'─' * 44}")
    print(f"  Deck: {view.deck_size} cards remaining")
    if view.top_of_discard:
        print(f"  Discard pile top: {view.top_of_discard}")
    else:
        print(f"  Discard pile: (empty)")
    dw = calculate_deadwood(view.hand)
    display, melds, unmelded = format_hand(view.hand)
    print(f"  Deadwood: {dw}")
    print(f"  Hand: {display}")
    print(f"  {'─' * 44}")


class HumanPlayer(Bot):
    """A 'bot' that prompts a human for decisions via the terminal."""

    @property
    def name(self):
        return "Human"

    def draw_decision(self, view):
        print_state(view)
        while True:
            choice = input("  Draw from (d)eck or (p)ickup discard? ").strip().lower()
            if choice in ("d", "deck"):
                return "deck"
            if choice in ("p", "pickup", "discard"):
                if view.top_of_discard is None:
                    print("  Discard pile is empty, drawing from deck.")
                    return "deck"
                return "discard"
            print("  Enter 'd' for deck or 'p' for pickup.")

    def discard_decision(self, view):
        display, melds, unmelded = format_hand(view.hand)
        print()
        print(f"  Your hand after drawing ({calculate_deadwood(view.hand)} deadwood):")
        print(f"  {display}")

        while True:
            choice = input("  Discard which card? (e.g. 'KH'): ").strip()
            card = parse_card(choice)
            if card and card in view.hand:
                return card
            print(f"  Card not found in hand. Enter a card name like '5H' or 'KH'.")

    def knock_decision(self, view):
        dw = calculate_deadwood(view.hand)
        if dw == 0:
            print("  *** GIN! ***")
            return True
        print(f"\n  You can knock! (deadwood: {dw})")
        while True:
            choice = input("  Knock? (y/n): ").strip().lower()
            if choice in ("y", "yes"):
                return True
            if choice in ("n", "no"):
                return False
            print("  Enter 'y' or 'n'.")


def load_bot(bot_path):
    """Load a bot class from a Python file and return an instance."""
    spec = importlib.util.spec_from_file_location("opponent_bot", bot_path)
    if spec is None or spec.loader is None:
        print(f"Error: Could not load '{bot_path}'")
        sys.exit(1)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    bot_classes = [
        obj for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, Bot) and obj is not Bot
    ]
    if not bot_classes:
        print(f"Error: No Bot subclass found in '{bot_path}'")
        sys.exit(1)
    return bot_classes[0]()


def event_logger(event, state, **kwargs):
    """Print bot actions so the human can follow the game."""
    if event == "game_start":
        bots = kwargs["bots"]
        dealer = kwargs["dealer"]
        event_logger._names = [b.name for b in bots]
        names = event_logger._names
        print()
        print(f"  {'=' * 44}")
        print(f"  Gin Rummy: {names[0]} vs {names[1]}")
        print(f"  Dealer: {names[dealer]}")
        print(f"  {'=' * 44}")

    elif event == "turn_start":
        player = kwargs["player"]
        names = getattr(event_logger, "_names", ["Player 0", "Player 1"])
        print(f"\n  --- {names[player]}'s turn ---")

    elif event == "draw":
        player = kwargs["player"]
        names = getattr(event_logger, "_names", ["Player 0", "Player 1"])
        # Only show bot draws (human sees their own)
        if names[player] != "Human":
            choice = kwargs["choice"]
            choice_str = choice if isinstance(choice, str) else choice.value
            if choice_str in ("discard", "DISCARD"):
                card = kwargs["card"]
                print(f"  {names[player]} picked up from discard: {card}")
            else:
                print(f"  {names[player]} drew from deck")

    elif event == "discard":
        player = kwargs["player"]
        names = getattr(event_logger, "_names", ["Player 0", "Player 1"])
        card = kwargs["card"]
        if names[player] != "Human":
            print(f"  {names[player]} discarded: {card}")

    elif event == "knock":
        player = kwargs["player"]
        names = getattr(event_logger, "_names", ["Player 0", "Player 1"])
        dw = calculate_deadwood(state.hands[player])
        if dw == 0:
            print(f"  {names[player]} declares GIN!")
        else:
            print(f"  {names[player]} knocks! (deadwood: {dw})")

    elif event == "deck_exhausted":
        print(f"\n  Deck exhausted — game is a draw!")


def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/play_human.py <bot_file>")
        print("  e.g. python examples/play_human.py bots/random_bot.py")
        sys.exit(1)

    bot_path = sys.argv[1]
    opponent = load_bot(bot_path)

    human = HumanPlayer()
    engine = GameEngine(on_event=event_logger)

    # Human is always player 0, bot is player 1
    result = engine.play_game(human, opponent)

    # Show final results
    print()
    print(f"  {'=' * 44}")
    print(f"  Result: {result.result_type}")
    if result.winner is not None:
        names = ["Human", opponent.name]
        winner_name = names[result.winner]
        print(f"  Winner: {winner_name}")
        print(f"  Score: {result.score} points")

        for i, name in enumerate(names):
            hand = engine.state.hands[i]
            melds, unmelded = find_best_melds(hand)
            dw = sum(c.deadwood_value for c in unmelded)
            print(f"\n  {name}'s final hand (deadwood: {dw}):")
            for meld in melds:
                print(f"    Meld: {' '.join(str(c) for c in meld)}")
            if unmelded:
                print(f"    Unmelded: {' '.join(str(c) for c in unmelded)}")
    else:
        print(f"  No winner (draw)")
    print(f"  {'=' * 44}")


if __name__ == "__main__":
    main()
