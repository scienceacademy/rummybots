"""Entry point for running Gin Rummy bot tournaments.

Usage:
    python main.py                  # Run tournament with all bots
    python main.py --games 50       # Set games per match
    python main.py --seed 42        # Set random seed for reproducibility
    python main.py --no-h2h         # Skip head-to-head details
"""

import argparse
import sys

from framework.tournament import (
    format_head_to_head,
    format_rankings,
    load_bots_from_directory,
    run_tournament,
)


def main():
    parser = argparse.ArgumentParser(
        description="Run a Gin Rummy bot tournament"
    )
    parser.add_argument(
        "--games", type=int, default=100,
        help="Number of games per bot pairing (default: 100)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--no-h2h", action="store_true",
        help="Skip head-to-head details in output",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress match-by-match progress output",
    )
    args = parser.parse_args()

    print("Loading bots...")
    bots = load_bots_from_directory()

    if len(bots) < 2:
        print("Error: Need at least 2 bots to run a tournament.")
        print("Add bot files to the bots/ directory.")
        sys.exit(1)

    print(f"Found {len(bots)} bots: {', '.join(b.name for b in bots)}")
    print(f"Running round-robin tournament ({args.games} games per match)...")
    if args.seed is not None:
        print(f"Random seed: {args.seed}")
    print()

    rankings, matches = run_tournament(
        bots,
        games_per_match=args.games,
        seed=args.seed,
        verbose=not args.quiet,
    )

    print(format_rankings(rankings))

    if not args.no_h2h:
        print(format_head_to_head(rankings))

    # Report any errors
    total_errors = sum(len(m.errors) for m in matches)
    if total_errors > 0:
        print(f"\nWarning: {total_errors} errors occurred during tournament:")
        for match in matches:
            for err in match.errors[:3]:  # show first 3 per match
                print(f"  {match.bot0_name} vs {match.bot1_name}: {err}")
            if len(match.errors) > 3:
                print(f"  ... and {len(match.errors) - 3} more")


if __name__ == "__main__":
    main()
