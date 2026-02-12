"""Run a single game between two bots with verbose output.

Usage:
    python examples/single_game.py
"""

import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.game import GameEngine, GamePhase
from engine.rules import calculate_deadwood, find_best_melds
from framework.bot_interface import Bot
from bots.basic_bot import BasicBot
from bots.intermediate_bot import IntermediateBot


def verbose_logger(event, state, **kwargs):
    """Event callback that prints game actions as they happen."""
    if event == "game_start":
        bots = kwargs["bots"]
        dealer = kwargs["dealer"]
        # Store names on the function for later events
        verbose_logger._names = [b.name for b in bots]
        names = verbose_logger._names
        print(f"{'='*50}")
        print(f"  {names[0]} vs {names[1]}")
        print(f"  Dealer: {names[dealer]}")
        print(f"{'='*50}")
        print(f"  Discard pile: {state.discard_pile[-1]}")
        print()

    elif event == "turn_start":
        player = kwargs["player"]
        turn = kwargs["turn"]
        names = getattr(verbose_logger, "_names", ["Player 0", "Player 1"])
        dw = calculate_deadwood(state.hands[player])
        print(f"Turn {turn} — {names[player]} (deadwood: {dw})")

    elif event == "draw":
        player = kwargs["player"]
        choice = kwargs["choice"]
        card = kwargs["card"]
        choice_str = choice if isinstance(choice, str) else choice.value
        if choice_str in ("discard", "DISCARD"):
            print(f"  Drew from discard: {card}")
        else:
            print(f"  Drew from deck: {card}")

    elif event == "discard":
        player = kwargs["player"]
        card = kwargs["card"]
        dw = calculate_deadwood(state.hands[player])
        print(f"  Discarded: {card}  (deadwood now: {dw})")

    elif event == "deck_exhausted":
        print(f"\n  Deck exhausted — DRAW")

    elif event == "knock":
        player = kwargs["player"]
        result = kwargs["result"]
        dw = calculate_deadwood(state.hands[player])
        if dw == 0:
            print(f"  ** GIN! **")
        else:
            print(f"  ** KNOCK! (deadwood: {dw}) **")
        print()


def main():
    random.seed(42)

    bot0 = BasicBot()
    bot1 = IntermediateBot()

    engine = GameEngine(on_event=verbose_logger)
    result = engine.play_game(bot0, bot1)

    print(f"{'='*50}")
    print(f"  Result: {result.result_type}")
    if result.winner is not None:
        winner_name = bot0.name if result.winner == 0 else bot1.name
        print(f"  Winner: {winner_name}")
        print(f"  Score:  {result.score} points")

        # Show final hands
        for i, bot in enumerate([bot0, bot1]):
            hand = engine.state.hands[i]
            melds, unmelded = find_best_melds(hand)
            dw = sum(c.deadwood_value for c in unmelded)
            print(f"\n  {bot.name}'s hand (deadwood: {dw}):")
            for meld in melds:
                print(f"    Meld: {' '.join(str(c) for c in meld)}")
            if unmelded:
                print(f"    Unmelded: {' '.join(str(c) for c in unmelded)}")
    else:
        print(f"  No winner (draw)")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
