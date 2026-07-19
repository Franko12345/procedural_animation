"""Launcher for the Lagarto game. The implementation lives in the `lagarto` package.

Run:
    python lizard_game.py             # play
    python lizard_game.py --smoke 90  # headless-friendly self-test
"""

from lagarto.app import main

if __name__ == "__main__":
    main()
