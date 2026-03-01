"""Tournament framework for Gin Rummy bot competitions.

Supports running matches between pairs of bots, round-robin tournaments,
and generating statistics and rankings.
"""

import importlib
import inspect
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
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


def _run_match_worker(args):
    """Worker function for parallel match execution."""
    bot0, bot1, num_games, seed = args
    return run_match(bot0, bot1, num_games, seed=seed)


def run_tournament(
    bots: List[Bot],
    games_per_match: int = 100,
    seed: Optional[int] = None,
    verbose: bool = True,
    parallel: bool = True,
) -> Tuple[List[BotStats], List[MatchResult]]:
    """Run a round-robin tournament.

    Every bot plays every other bot. Results are aggregated into
    per-bot statistics and per-match results.

    Args:
        bots: List of bot instances to compete.
        games_per_match: Number of games per bot pairing.
        seed: Base random seed for reproducibility.
        verbose: Print progress during tournament.
        parallel: Run matches in parallel using multiple processes.

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
    stats: Dict[str, BotStats] = {b.name: BotStats(b.name) for b in bots}
    total_matches = len(pairings)

    if parallel and total_matches >= 2:
        match_results = _run_tournament_parallel(
            bots, pairings, games_per_match, seed, verbose, stats
        )
    else:
        match_results = _run_tournament_sequential(
            bots, pairings, games_per_match, seed, verbose, stats
        )

    # Sort by win rate descending, then by total points
    rankings = sorted(
        stats.values(),
        key=lambda s: (s.win_rate, s.total_points),
        reverse=True,
    )

    return rankings, match_results


def _run_tournament_sequential(
    bots, pairings, games_per_match, seed, verbose, stats
):
    """Run tournament matches sequentially."""
    match_results: List[MatchResult] = []
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
        match_start = time.monotonic()
        match = run_match(bot0, bot1, games_per_match, seed=match_seed)
        match_elapsed = time.monotonic() - match_start
        match_results.append(match)

        stats[bot0.name].record_match(bot1.name, match, is_bot0=True)
        stats[bot1.name].record_match(bot0.name, match, is_bot0=False)

        if verbose:
            ms_per_game = (match_elapsed / games_per_match) * 1000
            print(
                f" {match.bot0_wins}-{match.bot1_wins}"
                f" ({match.draws} draws)"
                f"  [{ms_per_game:.1f}ms/game]"
            )

    return match_results


def _run_tournament_parallel(
    bots, pairings, games_per_match, seed, verbose, stats
):
    """Run tournament matches in parallel using multiple processes."""
    total_matches = len(pairings)
    workers = os.cpu_count() or 1

    if verbose:
        print(f"  Running {total_matches} matches across {workers} workers...")

    # Build work items: (bot0, bot1, num_games, seed) for each pairing
    work_items = []
    for match_num, (i, j) in enumerate(pairings):
        match_seed = seed + match_num * 1000 if seed is not None else None
        work_items.append((bots[i], bots[j], games_per_match, match_seed))

    # Map match_num to pairing indices for stats aggregation
    pairing_map = {match_num: (i, j) for match_num, (i, j) in enumerate(pairings)}

    # Submit all matches and collect results as they complete
    match_results = [None] * total_matches
    completed = 0
    tournament_start = time.monotonic()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_idx = {
            executor.submit(_run_match_worker, item): idx
            for idx, item in enumerate(work_items)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            i, j = pairing_map[idx]
            completed += 1

            try:
                match = future.result()
            except Exception as e:
                # Worker crashed — create an empty result with the error recorded
                match = MatchResult(bots[i].name, bots[j].name)
                match.record_error(f"Worker process error: {type(e).__name__}: {e}")
                if verbose:
                    print(
                        f"  Match {completed}/{total_matches} ERROR: "
                        f"{bots[i].name} vs {bots[j].name}: {e}"
                    )

            match_results[idx] = match
            stats[bots[i].name].record_match(bots[j].name, match, is_bot0=True)
            stats[bots[j].name].record_match(bots[i].name, match, is_bot0=False)

            if verbose and not match.errors:
                print(
                    f"  Match {completed}/{total_matches} done: "
                    f"{match.bot0_name} vs {match.bot1_name} "
                    f"{match.bot0_wins}-{match.bot1_wins}"
                    f" ({match.draws} draws)"
                )

    if verbose:
        elapsed = time.monotonic() - tournament_start
        print(f"  All matches completed in {elapsed:.1f}s")

    return match_results


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


def format_html_report(
    rankings: List[BotStats],
    matches: List[MatchResult],
    games_per_match: int,
) -> str:
    """Generate an HTML tournament report."""

    # Build head-to-head matrix data
    names = [s.name for s in rankings]
    h2h_cells = {}
    for s in rankings:
        for opp, (w, l) in s.head_to_head.items():
            h2h_cells[(s.name, opp)] = (w, l)

    # Rankings table rows
    ranking_rows = ""
    for rank, s in enumerate(rankings, 1):
        ranking_rows += f"""<tr>
            <td data-v="{rank}">{rank}</td>
            <td class="bot-name" data-v="{s.name}">{s.name}</td>
            <td data-v="{s.wins}">{s.wins}</td>
            <td data-v="{s.losses}">{s.losses}</td>
            <td data-v="{s.draws}">{s.draws}</td>
            <td class="pct" data-v="{s.win_rate:.4f}">{s.win_rate:.1%}</td>
            <td data-v="{s.total_points}">{s.total_points}</td>
            <td data-v="{s.avg_points:.2f}">{s.avg_points:.1f}</td>
            <td data-v="{s.gins}">{s.gins}</td>
            <td data-v="{s.undercuts}">{s.undercuts}</td>
        </tr>"""

    # Head-to-head table
    h2h_header = "".join(
        f'<th class="h2h-name">{n}</th>' for n in names
    )
    h2h_rows = ""
    for row_name in names:
        cells = f'<td class="bot-name">{row_name}</td>'
        for col_name in names:
            if row_name == col_name:
                cells += '<td class="self">&mdash;</td>'
            else:
                w, l = h2h_cells.get((row_name, col_name), (0, 0))
                total = w + l
                pct = w / total if total else 0
                if pct > 0.55:
                    cls = "win"
                elif pct < 0.45:
                    cls = "loss"
                else:
                    cls = "even"
                cells += f'<td class="{cls}">{w}-{l}</td>'
        h2h_rows += f"<tr>{cells}</tr>"

    # Error summary
    total_errors = sum(len(m.errors) for m in matches)
    error_section = ""
    if total_errors > 0:
        error_lines = []
        for m in matches:
            for err in m.errors[:3]:
                error_lines.append(
                    f"<li>{m.bot0_name} vs {m.bot1_name}: {err}</li>"
                )
            if len(m.errors) > 3:
                error_lines.append(
                    f"<li>... and {len(m.errors) - 3} more</li>"
                )
        error_section = f"""
        <div class="errors">
            <h2>Errors ({total_errors})</h2>
            <ul>{"".join(error_lines)}</ul>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Gin Rummy Tournament Results</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #f5f5f5; color: #222; padding: 2rem; }}
  h1 {{ text-align: center; margin-bottom: 0.25rem; font-size: 1.8rem; }}
  .meta {{ text-align: center; color: #666; margin-bottom: 2rem; font-size: 0.9rem; }}
  .card {{ background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1);
           padding: 1.5rem; margin-bottom: 1.5rem; overflow-x: auto; }}
  h2 {{ margin-bottom: 1rem; font-size: 1.2rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
  th, td {{ padding: 0.5rem 0.75rem; text-align: right; border-bottom: 1px solid #eee; }}
  th {{ background: #fafafa; font-weight: 600; position: sticky; top: 0; }}
  td.bot-name {{ text-align: left; font-weight: 600; }}
  th:first-child, td:first-child {{ text-align: center; }}
  tr.top {{ background: #fffbe6; }}
  tr:hover {{ background: #f0f7ff; }}
  .pct {{ font-weight: 600; }}
  /* h2h */
  .h2h-name {{ writing-mode: vertical-rl; text-orientation: mixed; font-size: 0.8rem;
               white-space: nowrap; padding: 0.5rem 0.25rem; }}
  td.self {{ background: #f0f0f0; color: #aaa; text-align: center; }}
  td.win {{ background: #e6f4ea; color: #1a7f37; text-align: center; font-weight: 600; }}
  td.loss {{ background: #ffeef0; color: #cf222e; text-align: center; }}
  td.even {{ background: #fff8e1; text-align: center; }}
  .errors {{ background: #fff3f3; border-radius: 8px; padding: 1.5rem; }}
  .errors h2 {{ color: #cf222e; }}
  .errors ul {{ margin-left: 1.5rem; font-size: 0.85rem; }}
  /* sortable headers */
  th.sortable {{ cursor: pointer; user-select: none; position: relative; padding-right: 1.2rem; }}
  th.sortable:hover {{ background: #eef; }}
  th.sortable::after {{ content: "\\2195"; position: absolute; right: 0.2rem; opacity: 0.3; font-size: 0.75rem; }}
  th.sortable.asc::after {{ content: "\\2191"; opacity: 0.8; }}
  th.sortable.desc::after {{ content: "\\2193"; opacity: 0.8; }}
</style>
</head>
<body>
<h1>Gin Rummy Tournament</h1>
<p class="meta">{len(rankings)} bots &middot; {games_per_match} games per match</p>

<div class="card">
<h2>Rankings</h2>
<table id="rankings">
<thead><tr>
  <th class="sortable desc" data-col="0" data-type="num">#</th>
  <th class="sortable" data-col="1" data-type="str" style="text-align:left">Bot</th>
  <th class="sortable" data-col="2" data-type="num">W</th>
  <th class="sortable" data-col="3" data-type="num">L</th>
  <th class="sortable" data-col="4" data-type="num">D</th>
  <th class="sortable" data-col="5" data-type="num">Win%</th>
  <th class="sortable" data-col="6" data-type="num">Pts</th>
  <th class="sortable" data-col="7" data-type="num">Avg</th>
  <th class="sortable" data-col="8" data-type="num">Gins</th>
  <th class="sortable" data-col="9" data-type="num">Undercuts</th>
</tr></thead>
<tbody>
{ranking_rows}
</tbody>
</table>
</div>

<div class="card">
<h2>Head-to-Head</h2>
<table>
<tr><th></th>{h2h_header}</tr>
{h2h_rows}
</table>
</div>

{error_section}

<script>
document.querySelectorAll("#rankings th.sortable").forEach(th => {{
  th.addEventListener("click", () => {{
    const table = document.getElementById("rankings");
    const tbody = table.querySelector("tbody");
    const rows = Array.from(tbody.querySelectorAll("tr"));
    const col = parseInt(th.dataset.col);
    const type = th.dataset.type;
    const isAsc = th.classList.contains("asc");
    const dir = isAsc ? -1 : 1;

    rows.sort((a, b) => {{
      const av = a.children[col].dataset.v;
      const bv = b.children[col].dataset.v;
      if (type === "num") return (parseFloat(av) - parseFloat(bv)) * dir;
      return av.localeCompare(bv) * dir;
    }});

    table.querySelectorAll("th.sortable").forEach(h => h.classList.remove("asc", "desc"));
    th.classList.add(isAsc ? "desc" : "asc");
    rows.forEach(r => tbody.appendChild(r));
  }});
}});
</script>
</body>
</html>"""


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
