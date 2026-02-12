"""Run a quick tournament with fewer games for fast iteration.

Usage:
    python examples/quick_tournament.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.tournament import (
    format_head_to_head,
    format_rankings,
    load_bots_from_directory,
    run_tournament,
)


def main():
    bots_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "bots",
    )
    bots = load_bots_from_directory(bots_dir)

    if len(bots) < 2:
        print("Need at least 2 bots in the bots/ directory.")
        sys.exit(1)

    print(f"Quick tournament: {', '.join(b.name for b in bots)}")
    print(f"20 games per matchup\n")

    rankings, matches = run_tournament(
        bots, games_per_match=20, seed=42, verbose=True
    )

    print(format_rankings(rankings))
    print(format_head_to_head(rankings))


if __name__ == "__main__":
    main()
