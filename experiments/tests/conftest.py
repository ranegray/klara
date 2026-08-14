"""Make the experiments scripts importable from tests.

experiments/ is deliberately not an installed package — run_sweep.py and
analysis/ are scripts run directly. Tests import them by putting both
directories on sys.path, the same resolution a direct `python <script>`
invocation gets.
"""

import sys
from pathlib import Path

EXPERIMENTS_DIR = Path(__file__).resolve().parents[1]

for directory in (EXPERIMENTS_DIR, EXPERIMENTS_DIR / "analysis"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
