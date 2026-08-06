"""Render the VOLCANO mission report figures under ``output/figures/``.

Writes six deterministic PNGs (rendezvous windows, orbital capture, concealed-
lair detection, hidden-base discovery, infiltration route, pattern of life) via
:mod:`you_only_live_twice.figures`. Exits 0 when every figure file is produced.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from you_only_live_twice.figures import (
    plot_concealed_lair,
    plot_emitter_error_sweep,
    plot_emitter_localization,
    plot_hidden_base_discovery,
    plot_infiltration_route,
    plot_orbital_capture,
    plot_pattern_of_life,
    plot_rendezvous_windows,
)


def main() -> int:
    paths = [
        plot_rendezvous_windows(),
        plot_orbital_capture(),
        plot_concealed_lair(),
        plot_hidden_base_discovery(),
        plot_infiltration_route(),
        plot_pattern_of_life(),
        plot_emitter_localization(),
        plot_emitter_error_sweep(),
    ]
    for path in paths:
        size = Path(path).stat().st_size
        print(f"[VOLCANO] figure {path} ({size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
