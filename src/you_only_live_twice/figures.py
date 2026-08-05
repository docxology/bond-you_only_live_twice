"""Deterministic figures for the VOLCANO mission report.

Renders publication-quality PNGs under ``output/figures/`` for the three
special-agent capabilities:

* rendezvous windows — target elevation and slant range vs time, with the
  detected windows shaded;
* concealed-lair detection — the thermal + terrain scenes and the fused
  anomaly map with the top candidate region marked;
* pattern of life — the daily activity profile with the peak windows and the
  base operating rhythm.

Every figure is drawn with ``MPLBACKEND=Agg`` and fixed data, so output is
byte-deterministic for a given scenario. Functions return the absolute path of
the written PNG so scripts and the manuscript can locate them.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from you_only_live_twice.pattern_of_life import (
    BaseActivity,
    daily_activity_profile,
    hourly_histogram,
    peak_activity_windows,
)
from you_only_live_twice.rendezvous_windows import (
    circular_state,
    range_and_elevation,
)
from you_only_live_twice.scenario import build_scenario
from you_only_live_twice.terrain_anomaly import (
    detect_concealed_lair,
)

__all__ = [
    "figures_dir",
    "plot_concealed_lair",
    "plot_hidden_base_discovery",
    "plot_infiltration_route",
    "plot_orbital_capture",
    "plot_pattern_of_life",
    "plot_rendezvous_windows",
]


def figures_dir() -> Path:
    """The absolute path of the output figures directory (created on demand)."""
    root = Path(__file__).resolve().parent.parent.parent
    out = root / "output" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _save(fig: Any, name: str) -> str:
    path = figures_dir() / name
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def plot_rendezvous_windows(
    dt_s: float = 300.0,
    t_start: float = 0.0,
    t_end: float = 86400.0,
    max_range_km: float = 1500.0,
    min_elevation_deg: float = 0.0,
) -> str:
    """Plot target elevation and range vs time with the detected windows shaded."""
    scenario = build_scenario()
    chaser = scenario["orbits"]["chaser"]
    target = scenario["orbits"]["target"]
    # Lightweight window detection on the same geometry the mission uses.
    from you_only_live_twice.rendezvous_windows import find_rendezvous_windows

    times = list(range(int(t_start), int(t_end) + int(dt_s), int(dt_s)))
    ranges: list[float] = []
    elevations: list[float] = []
    for t in times:
        cp, cv = circular_state(chaser, float(t))
        tp, _ = circular_state(target, float(t))
        rng, elev = range_and_elevation(cp, cv, tp)
        ranges.append(rng / 1e3)
        elevations.append(math.degrees(elev))

    windows = find_rendezvous_windows(
        chaser,
        target,
        t_start=t_start,
        t_end=t_end,
        dt=dt_s,
        max_range_km=max_range_km,
        min_elevation_deg=min_elevation_deg,
    )

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    for win in windows:
        for ax in (ax1, ax2):
            ax.axvspan(win.start_s, win.end_s, color="tab:orange", alpha=0.18)
    ax1.plot(times, ranges, color="tab:blue")
    ax1.set_ylabel("Slant range (km)")
    ax1.set_title("Space-capsule rendezvous windows — VOLCANO")
    ax2.plot(times, elevations, color="tab:green")
    ax2.set_ylabel("Elevation (deg)")
    ax2.set_xlabel("Time since mission start (s)")
    ax2.axhline(min_elevation_deg, color="grey", ls="--", lw=0.8, label="min elevation")
    ax2.legend(loc="best", fontsize="small")
    fig.tight_layout()
    return _save(fig, "rendezvous_windows.png")


def plot_concealed_lair() -> str:
    """Plot thermal + terrain scenes and the fused anomaly map with the lair marked."""
    scenario = build_scenario()
    volcano = scenario["volcano"]
    thermal = volcano["thermal"]
    elevation = volcano["elevation"]
    regions, meta = detect_concealed_lair(thermal, elevation)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    im0 = axes[0].imshow(thermal, cmap="hot")
    axes[0].set_title("Thermal scene")
    fig.colorbar(im0, ax=axes[0], shrink=0.8)
    im1 = axes[1].imshow(elevation, cmap="terrain")
    axes[1].set_title("Terrain scene")
    fig.colorbar(im1, ax=axes[1], shrink=0.8)
    im2 = axes[2].imshow(meta["fused_score"], cmap="viridis")
    axes[2].set_title("Fused anomaly score")
    fig.colorbar(im2, ax=axes[2], shrink=0.8)
    for region in regions[:1]:
        for ax in axes:
            rect = plt.Rectangle(
                (region.col0 - 0.5, region.row0 - 0.5),
                region.col1 - region.col0,
                region.row1 - region.row0,
                fill=False,
                edgecolor="white",
                lw=1.6,
            )
            ax.add_patch(rect)
        axes[2].set_title(
            f"Fused anomaly score (top candidate z={region.fused_score:.2f})"
        )
    fig.tight_layout()
    return _save(fig, "concealed_lair_detection.png")


def plot_pattern_of_life() -> str:
    """Plot the weekly activity profile, daily rhythm, and peak windows."""
    scenario = build_scenario()
    activity: tuple[BaseActivity, ...] = scenario["activity"]
    profile = daily_activity_profile(activity)
    hist = hourly_histogram(activity)
    windows = peak_activity_windows(profile)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=False)
    ax1.bar(range(168), hist, color="tab:purple", alpha=0.8)
    ax1.set_title("Base activity — weekly pattern of life (VOLCANO)")
    ax1.set_xlabel("Hour of week")
    ax1.set_ylabel("Events")
    hours = list(range(24))
    ax2.bar(hours, profile, color="tab:cyan")
    for start, end in windows:
        ax2.axvspan(start, end, color="tab:orange", alpha=0.3)
    ax2.set_title("Mean daily activity profile")
    ax2.set_xlabel("Hour of day")
    ax2.set_ylabel("Mean events/hour")
    fig.tight_layout()
    return _save(fig, "pattern_of_life.png")


def plot_orbital_capture(
    dt_s: float = 300.0,
    t_start: float = 0.0,
    t_end: float = 86400.0,
) -> str:
    """Plot capture range + relative speed vs time with the capture window shaded."""
    from you_only_live_twice.orbital_capture import (
        capture_windows,
        relative_state,
    )
    from you_only_live_twice.scenario import (
        CAPTURE_MAX_RANGE_KM,
        CAPTURE_MAX_SPEED_M_S,
    )

    scenario = build_scenario()
    chaser = scenario["orbits"]["chaser"]
    target = scenario["orbits"]["target"]
    times = list(range(int(t_start), int(t_end) + int(dt_s), int(dt_s)))
    ranges: list[float] = []
    speeds: list[float] = []
    for t in times:
        rho, rho_dot = relative_state(chaser, target, float(t))
        ranges.append(float(math.hypot(rho[0], rho[1]) / 1e3))
        speeds.append(float(math.hypot(rho_dot[0], rho_dot[1])))

    windows = capture_windows(
        chaser,
        target,
        t_start=t_start,
        t_end=t_end,
        dt=dt_s,
        max_range_km=CAPTURE_MAX_RANGE_KM,
        max_speed_m_s=CAPTURE_MAX_SPEED_M_S,
    )

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    for win in windows:
        for ax in (ax1, ax2):
            ax.axvspan(win.start_s, win.end_s, color="tab:olive", alpha=0.25)
    ax1.plot(times, ranges, color="tab:blue")
    ax1.set_ylabel("Slant range (km)")
    ax1.set_title("Orbital capture envelope — VOLCANO")
    ax2.plot(times, speeds, color="tab:red")
    ax2.set_ylabel("Relative speed (m/s)")
    ax2.set_xlabel("Time since mission start (s)")
    ax2.axhline(
        CAPTURE_MAX_SPEED_M_S, color="grey", ls="--", lw=0.8, label="max grapple speed"
    )
    ax2.legend(loc="best", fontsize="small")
    fig.tight_layout()
    return _save(fig, "orbital_capture.png")


def plot_hidden_base_discovery() -> str:
    """Plot the posterior map and search rank order with the true base marked."""

    scenario = build_scenario()
    posterior = scenario["discovery"]["posterior"]
    true_cell = scenario["discovery"]["true_cell"]

    fig, ax = plt.subplots(1, 1, figsize=(7, 6))
    im = ax.imshow(posterior, cmap="inferno")
    fig.colorbar(im, ax=ax, shrink=0.85, label="P(base at cell)")
    if true_cell is not None:
        ax.plot(
            true_cell[1],
            true_cell[0],
            marker="x",
            color="cyan",
            ms=12,
            mew=2.5,
            label="true base",
        )
    ax.set_title("Hidden-base discovery posterior — VOLCANO")
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")
    ax.legend(loc="best", fontsize="small")
    fig.tight_layout()
    return _save(fig, "hidden_base_discovery.png")


def plot_infiltration_route() -> str:
    """Plot the combined cost field with the optimal infiltration route overlaid."""
    from you_only_live_twice.infiltration_planning import combined_cost_field

    scenario = build_scenario()
    volcano = scenario["volcano"]
    infil = scenario["infiltration"]
    thermal_z = scenario["thermal_z"]

    cost = combined_cost_field(
        volcano["elevation"],
        thermal_z,
        infil["guard_posts"],
        impassable=infil["impassable"],
    )
    from you_only_live_twice.infiltration_planning import astar_path

    route = astar_path(cost, infil["start"], infil["goal"])
    rows = [p[0] for p in route.path]
    cols = [p[1] for p in route.path]

    fig, ax = plt.subplots(1, 1, figsize=(7, 6))
    im = ax.imshow(cost, cmap="terrain")
    fig.colorbar(im, ax=ax, shrink=0.85, label="movement cost")
    ax.plot(cols, rows, color="tab:red", lw=2.0, label="optimal route")
    ax.plot(
        infil["start"][1],
        infil["start"][0],
        marker="o",
        color="tab:green",
        ms=9,
        label="entry",
    )
    ax.plot(
        infil["goal"][1],
        infil["goal"][0],
        marker="*",
        color="tab:cyan",
        ms=14,
        label="lair",
    )
    for post in infil["guard_posts"]:
        ax.plot(post[1], post[0], marker="^", color="tab:orange", ms=8)
    ax.set_title("Infiltration route into the lair — VOLCANO")
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")
    ax.legend(loc="best", fontsize="small")
    fig.tight_layout()
    return _save(fig, "infiltration_route.png")
