"""Shared pytest configuration for the VOLCANO package.

Adds the package's ``src/`` to ``sys.path`` (so the package imports when pytest
runs without an installed wheel) and pins the matplotlib backend to Agg so
figure tests never open a display window.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
