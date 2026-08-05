"""Tests for the deterministic VOLCANO report figures.

Calls each figure generator directly (in-process, so they count toward src
coverage), verifying the PNG is produced at a non-empty path within
``output/figures/``.
"""

from __future__ import annotations

from pathlib import Path

from you_only_live_twice.figures import (
    figures_dir,
    plot_concealed_lair,
    plot_hidden_base_discovery,
    plot_infiltration_route,
    plot_orbital_capture,
    plot_pattern_of_life,
    plot_rendezvous_windows,
)

_EXPECTED = {
    "rendezvous_windows.png",
    "orbital_capture.png",
    "concealed_lair_detection.png",
    "hidden_base_discovery.png",
    "infiltration_route.png",
    "pattern_of_life.png",
}


def test_figures_dir_exists() -> None:
    assert figures_dir().is_dir()


def test_render_all_figures() -> None:
    paths = [
        plot_rendezvous_windows(dt_s=300.0),
        plot_orbital_capture(dt_s=300.0),
        plot_concealed_lair(),
        plot_hidden_base_discovery(),
        plot_infiltration_route(),
        plot_pattern_of_life(),
    ]
    names = {Path(p).name for p in paths}
    assert names == _EXPECTED
    for p in paths:
        assert Path(p).is_file()
        assert Path(p).stat().st_size > 1_000  # non-trivial PNG
