"""Run a single game between two bots with verbose output.

Usage:
    python3 examples/single_game.py
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


class VerboseEngine(GameEngine):
    """A game engine that prints each action as it happens."""

    def play_game(self, bot0, bot1, dealer=0):
        self.state.setup(dealer)
        self._drawn_from_discard = None
        bots = [bot0, bot1]
        names = [bot0.name, bot1.name]

        print(f"{'='*50}")
        print(f"  {names[0]} vs {names[1]}")
        print(f"  Dealer: {names[dealer]}")
        print(f"{'='*50}")
        print(f"  Discard pile: {self.state.discard_pile[-1]}")
        print()

        for i, bot in enumerate(bots):
            if hasattr(bot, "on_game_start"):
                bot.on_game_start(i, self.state.get_player_view(i))

        turn = 0
        while self.state.phase != GamePhase.END:
            turn += 1
            player = self.state.current_player
            bot = bots[player]
            hand = self.state.hands[player]
            dw = calculate_deadwood(hand)

            print(f"Turn {turn} — {names[player]} (deadwood: {dw})")

            # Draw
            view = self.state.get_player_view(player)
            draw_choice = bot.draw_decision(view)
            top_discard = self.state.discard_pile[-1] if self.state.discard_pile else None
            self._execute_draw(player, draw_choice)
            if draw_choice in ("discard", "DISCARD"):
                print(f"  Drew from discard: {top_discard}")
            else:
                drawn = self.state.hands[player][-1]
                print(f"  Drew from deck: {drawn}")

            # Discard
            view = self.state.get_player_view(player)
            discard_card = bot.discard_decision(view)
            self._execute_discard(player, discard_card)
            new_dw = calculate_deadwood(self.state.hands[player])
            print(f"  Discarded: {discard_card}  (deadwood now: {new_dw})")

            # Deck check
            from engine import rules
            if self.state.deck.remaining < 2:
                self.state.phase = GamePhase.END
                print(f"\n  Deck exhausted — DRAW")
                from engine.game import GameResult
                return GameResult(winner=None, score=0, result_type="draw")

            # Knock check
            if rules.can_knock(self.state.hands[player]):
                self.state.phase = GamePhase.KNOCK
                view = self.state.get_player_view(player)
                if bot.knock_decision(view):
                    result = self._execute_knock(player)
                    if new_dw == 0:
                        print(f"  ** GIN! **")
                    else:
                        print(f"  ** KNOCK! (deadwood: {new_dw}) **")
                    print()
                    return result

            for i, bot in enumerate(bots):
                if hasattr(bot, "on_turn_end"):
                    bot.on_turn_end(self.state.get_player_view(i))

            self.state.current_player = 1 - player
            self.state.phase = GamePhase.DRAW
            print()

        from engine.game import GameResult
        return GameResult(winner=None, score=0, result_type="draw")


def main():
    random.seed(42)

    bot0 = BasicBot()
    bot1 = IntermediateBot()

    engine = VerboseEngine()
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
