#!/usr/bin/env python3
"""Bot validation tool for students.

Run this script before submitting your bot to catch common errors:
    python scripts/validate_bot.py bots/my_bot.py

The validator checks:
- File exists and is readable
- Bot class inherits from framework.bot_interface.Bot
- Bot has unique name property
- All three decision methods are implemented
- Bot handles empty discard pile (first turn)
- Bot doesn't crash on sample hands
- Bot returns correct types
- Bot completes games in reasonable time
"""

import importlib.util
import inspect
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.card import Card, Rank, Suit
from engine.game import GameEngine, PlayerView
from framework.bot_interface import Bot
from bots.random_bot import RandomBot


class ValidationResult:
    """Result of a validation check."""

    def __init__(self, passed: bool, message: str, warning: bool = False):
        self.passed = passed
        self.message = message
        self.warning = warning

    def __str__(self):
        if self.warning:
            return f"⚠  {self.message}"
        elif self.passed:
            return f"✓ {self.message}"
        else:
            return f"✗ {self.message}"


def check_file_exists(bot_path: str) -> ValidationResult:
    """Check if the bot file exists and is readable."""
    path = Path(bot_path)
    if not path.exists():
        return ValidationResult(False, f"File not found: {bot_path}")
    if not path.is_file():
        return ValidationResult(False, f"Not a file: {bot_path}")
    if not path.suffix == ".py":
        return ValidationResult(False, f"Not a Python file: {bot_path}")
    return ValidationResult(True, f"File exists: {bot_path}")


def load_bot_class(bot_path: str) -> Tuple[Optional[type], Optional[ValidationResult]]:
    """Load the bot class from the file."""
    try:
        # Load the module
        spec = importlib.util.spec_from_file_location("student_bot", bot_path)
        if spec is None or spec.loader is None:
            return None, ValidationResult(False, "Could not load module spec")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find Bot subclass
        bot_classes = [
            obj for name, obj in inspect.getmembers(module, inspect.isclass)
            if issubclass(obj, Bot) and obj != Bot
        ]

        if not bot_classes:
            return None, ValidationResult(False, "No Bot subclass found in file")

        if len(bot_classes) > 1:
            return bot_classes[0], ValidationResult(
                True,
                f"Multiple bot classes found, using {bot_classes[0].__name__}",
                warning=True
            )

        return bot_classes[0], ValidationResult(True, f"Bot class loaded: {bot_classes[0].__name__}")

    except SyntaxError as e:
        return None, ValidationResult(False, f"Syntax error: {e}")
    except Exception as e:
        return None, ValidationResult(False, f"Failed to load bot: {type(e).__name__}: {e}")


def check_inherits_from_bot(bot_class: type) -> ValidationResult:
    """Check if bot class inherits from Bot."""
    if not issubclass(bot_class, Bot):
        return ValidationResult(False, "Bot class does not inherit from framework.bot_interface.Bot")
    return ValidationResult(True, "Bot inherits from framework.bot_interface.Bot")


def check_has_name_property(bot_class: type) -> ValidationResult:
    """Check if bot has a name property."""
    try:
        bot_instance = bot_class()
        name = bot_instance.name
        if not name or not isinstance(name, str):
            return ValidationResult(False, "Bot name property is empty or not a string")
        if name in ["Bot", "StudentBot"]:
            return ValidationResult(
                True,
                f"Bot has generic name '{name}' - consider using a unique name",
                warning=True
            )
        return ValidationResult(True, f"Bot has name: '{name}'")
    except Exception as e:
        return ValidationResult(False, f"Could not get bot name: {type(e).__name__}: {e}")


def check_all_methods_implemented(bot_class: type) -> List[ValidationResult]:
    """Check if all three decision methods are implemented."""
    results = []
    required_methods = {
        'draw_decision': 'draw_decision(self, view: PlayerView) -> str',
        'discard_decision': 'discard_decision(self, view: PlayerView) -> Card',
        'knock_decision': 'knock_decision(self, view: PlayerView) -> bool',
    }

    try:
        bot_instance = bot_class()
        for method_name, signature in required_methods.items():
            if not hasattr(bot_instance, method_name):
                results.append(ValidationResult(False, f"Missing method: {signature}"))
            else:
                method = getattr(bot_instance, method_name)
                if not callable(method):
                    results.append(ValidationResult(False, f"Not callable: {method_name}"))
                else:
                    results.append(ValidationResult(True, f"Method implemented: {method_name}"))
    except Exception as e:
        results.append(ValidationResult(False, f"Could not instantiate bot: {type(e).__name__}: {e}"))

    return results


def check_handles_empty_discard(bot_class: type) -> ValidationResult:
    """Check if bot handles empty discard pile (first turn)."""
    try:
        bot = bot_class()
        engine = GameEngine()

        # Create a mock PlayerView with None for top_of_discard
        class MockView:
            def __init__(self):
                self.hand = [Card(Rank.ACE, Suit.HEARTS) for _ in range(10)]
                self.top_of_discard = None
                self.discard_pile = []
                self.opponent_hand_size = 10
                self.deck_size = 31
                self.phase = "draw"

        view = MockView()
        decision = bot.draw_decision(view)

        if decision not in ("deck", "discard"):
            return ValidationResult(False, f"draw_decision with empty discard returned invalid: {decision}")

        return ValidationResult(True, "Bot handles empty discard pile")

    except Exception as e:
        return ValidationResult(False, f"Bot crashes on empty discard: {type(e).__name__}: {e}")


def check_no_crashes_on_sample_hands(bot_class: type) -> ValidationResult:
    """Check if bot can play several games without crashing."""
    try:
        bot = bot_class()
        opponent = RandomBot()
        engine = GameEngine()

        games_to_test = 5
        for i in range(games_to_test):
            try:
                result = engine.play_game(bot, opponent, dealer=0, rng=None)
            except Exception as e:
                return ValidationResult(
                    False,
                    f"Bot crashed in game {i+1}/{games_to_test}: {type(e).__name__}: {e}"
                )

        return ValidationResult(True, f"Bot completed {games_to_test} games without crashing")

    except Exception as e:
        return ValidationResult(False, f"Failed to test games: {type(e).__name__}: {e}")


def check_performance_acceptable(bot_class: type) -> ValidationResult:
    """Check if bot completes games in reasonable time."""
    try:
        bot = bot_class()
        opponent = RandomBot()
        engine = GameEngine()

        games_to_test = 10
        start_time = time.time()

        for _ in range(games_to_test):
            engine.play_game(bot, opponent, dealer=0, rng=None)

        elapsed = time.time() - start_time
        avg_time = elapsed / games_to_test

        if elapsed > 30:
            return ValidationResult(
                False,
                f"{games_to_test} games took {elapsed:.1f}s (avg {avg_time:.2f}s/game) - too slow (>30s)"
            )
        elif elapsed > 10:
            return ValidationResult(
                True,
                f"{games_to_test} games took {elapsed:.1f}s (avg {avg_time:.2f}s/game) - acceptable but slow",
                warning=True
            )
        else:
            return ValidationResult(
                True,
                f"{games_to_test} games took {elapsed:.1f}s (avg {avg_time:.2f}s/game) - good performance"
            )

    except Exception as e:
        return ValidationResult(False, f"Performance test failed: {type(e).__name__}: {e}")


def check_better_than_random(bot_class: type) -> ValidationResult:
    """Check if bot performs better than RandomBot (optional/warning)."""
    try:
        bot = bot_class()
        opponent = RandomBot()
        engine = GameEngine()

        games_to_test = 20
        wins = 0

        for _ in range(games_to_test):
            result = engine.play_game(bot, opponent, dealer=0, rng=None)
            if result.winner == 0:
                wins += 1

        win_rate = wins / games_to_test

        if win_rate < 0.4:
            return ValidationResult(
                True,
                f"Bot won {wins}/{games_to_test} ({win_rate:.1%}) vs RandomBot - needs improvement",
                warning=True
            )
        else:
            return ValidationResult(
                True,
                f"Bot won {wins}/{games_to_test} ({win_rate:.1%}) vs RandomBot - good!"
            )

    except Exception as e:
        return ValidationResult(
            True,
            f"Could not test win rate: {type(e).__name__}: {e}",
            warning=True
        )


def validate_bot(bot_path: str) -> Tuple[bool, List[ValidationResult]]:
    """Run all validation checks on a bot file.

    Returns:
        Tuple of (all_passed, list of results)
    """
    results = []

    # Check 1: File exists
    result = check_file_exists(bot_path)
    results.append(result)
    if not result.passed:
        return False, results

    # Check 2: Load bot class
    bot_class, result = load_bot_class(bot_path)
    results.append(result)
    if bot_class is None:
        return False, results

    # Check 3: Inherits from Bot
    result = check_inherits_from_bot(bot_class)
    results.append(result)
    if not result.passed:
        return False, results

    # Check 4: Has name property
    result = check_has_name_property(bot_class)
    results.append(result)

    # Check 5: All methods implemented
    method_results = check_all_methods_implemented(bot_class)
    results.extend(method_results)
    if not all(r.passed for r in method_results):
        return False, results

    # Check 6: Handles empty discard
    result = check_handles_empty_discard(bot_class)
    results.append(result)
    if not result.passed:
        return False, results

    # Check 7: No crashes on sample hands
    result = check_no_crashes_on_sample_hands(bot_class)
    results.append(result)
    if not result.passed:
        return False, results

    # Check 8: Performance acceptable
    result = check_performance_acceptable(bot_class)
    results.append(result)
    if not result.passed:
        return False, results

    # Check 9: Better than random (warning only)
    result = check_better_than_random(bot_class)
    results.append(result)

    # All critical checks passed
    all_passed = all(r.passed for r in results if not r.warning)
    return all_passed, results


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_bot.py <bot_file.py>")
        print("\nExample: python scripts/validate_bot.py bots/my_bot.py")
        sys.exit(1)

    bot_path = sys.argv[1]

    print("=" * 60)
    print("GIN RUMMY BOT VALIDATOR")
    print("=" * 60)
    print(f"\nValidating: {bot_path}\n")

    all_passed, results = validate_bot(bot_path)

    # Print results
    for result in results:
        print(result)

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ VALIDATION PASSED")
        print("=" * 60)
        print("\nYour bot is ready for submission!")
        sys.exit(0)
    else:
        print("✗ VALIDATION FAILED")
        print("=" * 60)
        print("\nPlease fix the errors above before submitting.")
        sys.exit(1)


if __name__ == "__main__":
    main()
