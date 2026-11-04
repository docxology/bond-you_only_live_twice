"""The copy under ``vendor/`` is a dependency, not a fork.

It must match its recorded provenance.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vendored_copies_match_their_provenance() -> None:
    """A change inside ``vendor/`` splits the copy from upstream; this fails."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "vendor.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
