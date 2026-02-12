"""Test your bot against the sample bots.

Usage:
    python examples/test_my_bot.py

Edit the 'my_bot' variable below to point to your bot class.
"""

import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.tournament import run_match, format_rankings, BotStats
from bots.random_bot import RandomBot
from bots.basic_bot import BasicBot
from bots.intermediate_bot import IntermediateBot

# --- Change this to import your bot ---
from bots.student_bot_template import StudentBot as MyBot
# Example: from bots.my_bot import MyBot


def main():
    my_bot = MyBot()
    opponents = [RandomBot(), BasicBot(), IntermediateBot()]
    games_per_match = 100

    print(f"Testing {my_bot.name} against sample bots ({games_per_match} games each)")
    print(f"{'='*55}")

    my_stats = BotStats(my_bot.name)

    for opp in opponents:
        result = run_match(my_bot, opp, num_games=games_per_match, seed=42)

        print(
            f"  vs {opp.name:<20s}  "
            f"W:{result.bot0_wins:>3}  "
            f"L:{result.bot1_wins:>3}  "
            f"D:{result.draws:>3}  "
            f"Win: {result.bot0_win_rate:.0%}"
        )
        my_stats.record_match(opp.name, result, is_bot0=True)

    print(f"{'='*55}")
    print(f"\nOverall: {my_stats.wins}W-{my_stats.losses}L-{my_stats.draws}D "
          f"({my_stats.win_rate:.1%} win rate)")
    print(f"Total points scored: {my_stats.total_points}")
    print(f"Average points/game: {my_stats.avg_points:.1f}")

    if my_stats.errors > 0:
        print(f"\nWarning: {my_stats.errors} errors occurred!")


if __name__ == "__main__":
    main()
