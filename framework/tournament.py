"""Tournament framework for Gin Rummy bot competitions.

Supports running matches between pairs of bots, round-robin tournaments,
and generating statistics and rankings.
"""

import importlib
import inspect
import os
import random
import sys
from itertools import combinations
from typing import Dict, List, Optional, Tuple, Type

from engine.game import GameEngine, GameResult, InvalidMoveError
from framework.bot_interface import Bot


class MatchResult:
    """Aggregated results from a multi-game match between two bots."""

    def __init__(self, bot0_name: str, bot1_name: str):
        self.bot0_name = bot0_name
        self.bot1_name = bot1_name
        self.games_played = 0
        self.bot0_wins = 0
        self.bot1_wins = 0
        self.draws = 0
        self.bot0_points = 0
        self.bot1_points = 0
        self.bot0_gins = 0
        self.bot1_gins = 0
        self.bot0_undercuts = 0  # times bot0 undercut bot1
        self.bot1_undercuts = 0
        self.errors: List[str] = []

    def record_game(self, result: GameResult, bot0_idx: int = 0) -> None:
        """Record a single game result.

        Args:
            result: The GameResult from the engine.
            bot0_idx: Which player index corresponds to bot0
                (handles dealer alternation).
        """
        self.games_played += 1
        bot1_idx = 1 - bot0_idx

        if result.winner is None:
            self.draws += 1
            return

        if result.winner == bot0_idx:
            self.bot0_wins += 1
            self.bot0_points += result.score
        else:
            self.bot1_wins += 1
            self.bot1_points += result.score

        if result.result_type == "gin":
            if result.winner == bot0_idx:
                self.bot0_gins += 1
            else:
                self.bot1_gins += 1
        elif result.result_type == "undercut":
            # The winner undercut the knocker
            if result.winner == bot0_idx:
                self.bot0_undercuts += 1
            else:
                self.bot1_undercuts += 1

    def record_error(self, error_msg: str) -> None:
        """Record a bot error."""
        self.errors.append(error_msg)

    @property
    def bot0_win_rate(self) -> float:
        decided = self.bot0_wins + self.bot1_wins
        return self.bot0_wins / decided if decided > 0 else 0.0

    @property
    def bot1_win_rate(self) -> float:
        decided = self.bot0_wins + self.bot1_wins
        return self.bot1_wins / decided if decided > 0 else 0.0

    def __repr__(self) -> str:
        return (
            f"MatchResult({self.bot0_name} vs {self.bot1_name}: "
            f"{self.bot0_wins}-{self.bot1_wins}-{self.draws})"
        )


class BotStats:
    """Aggregated statistics for a single bot across a tournament."""

    def __init__(self, name: str):
        self.name = name
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.total_points = 0
        self.gins = 0
        self.undercuts = 0  # times this bot undercut opponent
        self.errors = 0
        self.head_to_head: Dict[str, Tuple[int, int]] = {}

    @property
    def win_rate(self) -> float:
        decided = self.wins + self.losses
        return self.wins / decided if decided > 0 else 0.0

    @property
    def avg_points(self) -> float:
        return self.total_points / self.games_played if self.games_played > 0 else 0.0

    def record_match(self, opponent_name: str, match: MatchResult, is_bot0: bool) -> None:
        """Update stats from a match result."""
        if is_bot0:
            self.wins += match.bot0_wins
            self.losses += match.bot1_wins
            self.total_points += match.bot0_points
            self.gins += match.bot0_gins
            self.undercuts += match.bot0_undercuts
            h2h_wins = match.bot0_wins
            h2h_losses = match.bot1_wins
        else:
            self.wins += match.bot1_wins
            self.losses += match.bot0_wins
            self.total_points += match.bot1_points
            self.gins += match.bot1_gins
            self.undercuts += match.bot1_undercuts
            h2h_wins = match.bot1_wins
            h2h_losses = match.bot0_wins

        self.draws += match.draws
        self.games_played += match.games_played
        self.errors += len(match.errors)
        self.head_to_head[opponent_name] = (h2h_wins, h2h_losses)


def run_match(
    bot0: Bot,
    bot1: Bot,
    num_games: int = 100,
    seed: Optional[int] = None,
) -> MatchResult:
    """Run a multi-game match between two bots.

    Alternates dealer each game. Handles bot errors gracefully.

    Args:
        bot0: First bot instance.
        bot1: Second bot instance.
        num_games: Number of games to play.
        seed: Random seed for reproducibility (None for random).

    Returns:
        MatchResult with aggregated statistics.
    """
    result = MatchResult(bot0.name, bot1.name)
    engine = GameEngine()

    for game_num in range(num_games):
        # Create a dedicated RNG for the engine, isolated from global random.
        # Also seed global random for bot determinism (bots may use random module).
        if seed is not None:
            game_rng = random.Random(seed + game_num)
            random.seed(seed + game_num)
        else:
            game_rng = random.Random()

        # Alternate which bot is player 0 each game for fairness
        if game_num % 2 == 0:
            p0, p1 = bot0, bot1
            bot0_idx = 0
        else:
            p0, p1 = bot1, bot0
            bot0_idx = 1

        # Alternate dealer independently of position so that
        # first-mover advantage is evenly distributed.
        dealer = (game_num // 2) % 2

        try:
            game_result = engine.play_game(p0, p1, dealer=dealer, rng=game_rng)
            result.record_game(game_result, bot0_idx=bot0_idx)
        except Exception as e:
            result.record_error(
                f"Game {game_num}: {type(e).__name__}: {e}"
            )

    return result


def run_tournament(
    bots: List[Bot],
    games_per_match: int = 100,
    seed: Optional[int] = None,
    verbose: bool = True,
) -> Tuple[List[BotStats], List[MatchResult]]:
    """Run a round-robin tournament.

    Every bot plays every other bot. Results are aggregated into
    per-bot statistics and per-match results.

    Args:
        bots: List of bot instances to compete.
        games_per_match: Number of games per bot pairing.
        seed: Base random seed for reproducibility.
        verbose: Print progress during tournament.

    Returns:
        A tuple of (rankings, match_results) where rankings is a
        list of BotStats sorted by win rate (descending), and
        match_results contains all individual match results.
    """
    if len(bots) < 2:
        raise ValueError("Need at least 2 bots for a tournament")

    # Check for duplicate names
    names = [b.name for b in bots]
    if len(set(names)) != len(names):
        raise ValueError(f"Duplicate bot names found: {names}")

    pairings = list(combinations(range(len(bots)), 2))
    match_results: List[MatchResult] = []
    stats: Dict[str, BotStats] = {b.name: BotStats(b.name) for b in bots}

    total_matches = len(pairings)
    for match_num, (i, j) in enumerate(pairings):
        bot0, bot1 = bots[i], bots[j]
        if verbose:
            print(
                f"  Match {match_num + 1}/{total_matches}: "
                f"{bot0.name} vs {bot1.name}...",
                end="",
                flush=True,
            )

        match_seed = seed + match_num * 1000 if seed is not None else None
        match = run_match(bot0, bot1, games_per_match, seed=match_seed)
        match_results.append(match)

        # Update per-bot stats
        stats[bot0.name].record_match(bot1.name, match, is_bot0=True)
        stats[bot1.name].record_match(bot0.name, match, is_bot0=False)

        if verbose:
            print(
                f" {match.bot0_wins}-{match.bot1_wins}"
                f" ({match.draws} draws)"
            )

    # Sort by win rate descending, then by total points
    rankings = sorted(
        stats.values(),
        key=lambda s: (s.win_rate, s.total_points),
        reverse=True,
    )

    return rankings, match_results


def format_rankings(rankings: List[BotStats]) -> str:
    """Format tournament rankings as a readable table."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("TOURNAMENT RESULTS")
    lines.append("=" * 70)
    lines.append(
        f"{'Rank':<6}{'Bot':<20}{'W':>5}{'L':>5}{'D':>5}"
        f"{'Win%':>8}{'Pts':>7}{'Avg':>7}{'Gins':>6}"
    )
    lines.append("-" * 70)

    for rank, s in enumerate(rankings, 1):
        lines.append(
            f"{rank:<6}{s.name:<20}{s.wins:>5}{s.losses:>5}"
            f"{s.draws:>5}{s.win_rate:>7.1%}{s.total_points:>7}"
            f"{s.avg_points:>7.1f}{s.gins:>6}"
        )

    lines.append("=" * 70)
    return "\n".join(lines)


def format_head_to_head(rankings: List[BotStats]) -> str:
    """Format head-to-head records as a table."""
    lines = []
    lines.append("")
    lines.append("HEAD-TO-HEAD RECORDS")
    lines.append("-" * 50)

    for s in rankings:
        for opp_name, (wins, losses) in sorted(s.head_to_head.items()):
            lines.append(
                f"  {s.name} vs {opp_name}: "
                f"{wins}-{losses}"
            )
    return "\n".join(lines)


def load_bots_from_directory(
    directory: str = "bots",
    exclude: Optional[List[str]] = None,
) -> List[Bot]:
    """Discover and load all Bot subclasses from a directory.

    Scans Python files in the directory for classes that subclass Bot
    and instantiates them.

    **Security warning**: Bot files are loaded via importlib and their
    top-level code executes with full process privileges. Only load
    bot files from trusted sources or review them before loading.
    Use ``scripts/validate_bot.py`` to check student bots first.

    Args:
        directory: Path to the directory containing bot files.
        exclude: List of filenames to skip (e.g., ["student_bot_template.py"]).

    Returns:
        List of instantiated Bot objects.
    """
    if exclude is None:
        exclude = ["student_bot_template.py", "__init__.py"]

    bots = []
    bot_dir = os.path.abspath(directory)

    # Add project root to path if needed
    project_root = os.path.dirname(bot_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    for filename in sorted(os.listdir(bot_dir)):
        if not filename.endswith(".py") or filename in exclude:
            continue

        module_name = f"bots.{filename[:-3]}"
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            print(f"  Warning: Could not load {filename}: {e}")
            continue

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, Bot)
                and obj is not Bot
                and not inspect.isabstract(obj)
            ):
                try:
                    bots.append(obj())
                except Exception as e:
                    print(f"  Warning: Could not instantiate {name}: {e}")

    return bots
