"""Orbital capture: how the hidden base swallows a space capsule.

In *You Only Live Twice* the adversary's volcano base captures an orbiting
capsule whole. This module models the *orbital mechanics of that capture* with
real two-body mathematics built on the same propagation core as the rendezvous
solver:

* :func:`relative_state` / :func:`relative_speed` — the ECI relative position
  and velocity of the target with respect to the capture platform;
* :func:`capture_windows` — contiguous intervals where the capsule is both
  inside the capture envelope (range constraint) *and* slow enough relative to
  the platform (relative-speed constraint) to be grappled — a genuinely
  different condition from line-of-sight rendezvous;
* :func:`velocity_matching_budget` — the delta-v the platform must expend to
  null the relative velocity at a given epoch (the "grapple" burn);
* :func:`phasing_lead_angle` / :func:`phasing_wait_time` — the classic phasing
  problem: the angular separation the target must lead the platform by at the
  start of a Hohmann transfer, and how long the platform must wait for the
  relative phase to reach that lead.

All outputs are deterministic and depend only on the fixed orbital elements.
The module is infrastructure-free and importable without BOND-API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from you_only_live_twice.rendezvous_windows import (
    MU_EARTH,
    CircularOrbit,
    circular_state,
    mean_motion,
)

__all__ = [
    "CaptureWindow",
    "capture_windows",
    "phasing_lead_angle",
    "phasing_wait_time",
    "relative_speed",
    "relative_state",
    "velocity_matching_budget",
]

_TWO_PI = 2.0 * math.pi


@dataclass(frozen=True)
class CaptureWindow:
    """A contiguous interval where the capsule is inside the capture envelope.

    Within the window both ``range <= max_range_km`` and the relative speed is
    ``<= max_speed_m_s``, so the platform can physically reach out and grapple
    the capsule. ``min_range_km`` and ``min_speed_m_s`` record the best (closest
    / slowest) geometry reached.
    """

    start_s: float  #: window start, seconds since mission t0.
    end_s: float  #: window end, seconds since mission t0.
    min_range_km: float  #: closest approach during the window, km.
    min_speed_m_s: float  #: slowest relative speed during the window, m/s.

    @property
    def duration_s(self) -> float:
        """Window length in seconds."""
        return self.end_s - self.start_s


def relative_state(
    chaser: CircularOrbit,
    target: CircularOrbit,
    t_s: float,
    mu: float = MU_EARTH,
) -> tuple[np.ndarray, np.ndarray]:
    """ECI relative position and velocity of the target w.r.t. the chaser.

    Returns ``(rho, rho_dot)`` where ``rho = r_target - r_chaser`` (m) and
    ``rho_dot = v_target - v_chaser`` (m/s) at time ``t_s``.
    """
    chaser_pos, chaser_vel = circular_state(chaser, t_s, mu)
    target_pos, target_vel = circular_state(target, t_s, mu)
    return target_pos - chaser_pos, target_vel - chaser_vel


def relative_speed(
    chaser: CircularOrbit,
    target: CircularOrbit,
    t_s: float,
    mu: float = MU_EARTH,
) -> float:
    """Magnitude of the relative velocity vector at time ``t_s``, m/s."""
    _rho, rho_dot = relative_state(chaser, target, t_s, mu)
    return float(np.linalg.norm(rho_dot))


def velocity_matching_budget(
    chaser: CircularOrbit,
    target: CircularOrbit,
    t_s: float,
    mu: float = MU_EARTH,
) -> float:
    """Delta-v (m/s) to null the relative velocity at time ``t_s``.

    A grapple requires the platform to match the capsule's velocity vector; the
    required burn is exactly the magnitude of the relative velocity.
    """
    return relative_speed(chaser, target, t_s, mu)


def capture_windows(
    chaser: CircularOrbit,
    target: CircularOrbit,
    t_start: float = 0.0,
    t_end: float = 86400.0,
    dt: float = 60.0,
    max_range_km: float = 200.0,
    max_speed_m_s: float = 500.0,
    mu: float = MU_EARTH,
) -> tuple[CaptureWindow, ...]:
    """Find contiguous capture windows over the time span.

    A capture window is a run of steps where the capsule is simultaneously
    inside the grapple envelope (``range <= max_range_km``) and slow enough
    (``relative speed <= max_speed_m_s``). The search is a deterministic grid
    over time, mirroring :func:`rendezvous_windows.find_rendezvous_windows` but
    with the physical constraint replaced by the capture condition.
    """
    if t_end <= t_start:
        raise ValueError("t_end must be greater than t_start")
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    max_range_m = max_range_km * 1e3

    times = np.arange(t_start, t_end + dt, dt)
    inside: list[bool] = []
    for t in times:
        rho, rho_dot = relative_state(chaser, target, float(t), mu)
        rng = float(np.linalg.norm(rho))
        speed = float(np.linalg.norm(rho_dot))
        inside.append(rng <= max_range_m and speed <= max_speed_m_s)

    windows: list[CaptureWindow] = []
    i = 0
    n = len(times)
    while i < n:
        if not inside[i]:
            i += 1
            continue
        start = float(times[i])
        best_range_m = float("inf")
        best_speed_m_s = float("inf")
        j = i
        while j < n and inside[j]:
            rho, rho_dot = relative_state(chaser, target, float(times[j]), mu)
            rng = float(np.linalg.norm(rho))
            speed = float(np.linalg.norm(rho_dot))
            best_range_m = min(best_range_m, rng)
            best_speed_m_s = min(best_speed_m_s, speed)
            j += 1
        end = float(times[j - 1]) + float(dt)
        windows.append(
            CaptureWindow(
                start_s=start,
                end_s=end,
                min_range_km=best_range_m / 1e3,
                min_speed_m_s=best_speed_m_s,
            )
        )
        i = j
    return tuple(windows)


def phasing_lead_angle(
    chaser_radius: float,
    target_radius: float,
    mu: float = MU_EARTH,
) -> float:
    """Required target lead angle for a Hohmann intercept, radians in [0, 2π).

    For the chaser to arrive at the target after a coplanar Hohmann transfer of
    duration ``T_t``, the target must start ahead of the chaser by

    .. math:: \\lambda = (\\pi - n_t T_t) \\bmod 2\\pi

    where :math:`n_t` is the target's mean motion. Derivation: the transfer
    sweeps exactly :math:`\\pi`` radians, so the chaser arrives at
    :math:`\\theta_c(0)+\\pi`; matching the target's position there gives
    :math:`\\theta_t(0) = \\theta_c(0) + \\pi - n_t T_t`.
    """
    _require_positive(chaser_radius, "chaser_radius")
    _require_positive(target_radius, "target_radius")
    a_transfer = 0.5 * (chaser_radius + target_radius)
    transfer_time = math.pi * math.sqrt(a_transfer**3 / mu)
    target_mean_motion = mean_motion(target_radius, mu)
    return (math.pi - target_mean_motion * transfer_time) % _TWO_PI


def phasing_wait_time(
    chaser_radius: float,
    target_radius: float,
    initial_relative_phase: float,
    mu: float = MU_EARTH,
) -> float:
    """Seconds until the relative phase first reaches the required lead angle.

    The relative phase evolves as
    :math:`\\phi(t) = \\phi_0 + (n_t - n_c) t`, so the smallest non-negative
    solution of :math:`\\phi(t) \\equiv \\lambda \\pmod{2\\pi}` is returned.
    Returns ``inf`` when both orbits share a mean motion and the phase is not
    already correct (the geometry never changes).
    """
    _require_positive(chaser_radius, "chaser_radius")
    _require_positive(target_radius, "target_radius")
    lead = phasing_lead_angle(chaser_radius, target_radius, mu)
    phase0 = initial_relative_phase % _TWO_PI
    delta = (lead - phase0) % _TWO_PI  # angular advance still needed, in [0, 2π)
    rate = mean_motion(target_radius, mu) - mean_motion(chaser_radius, mu)
    if rate == 0.0:
        return 0.0 if delta == 0.0 else float("inf")
    period = _TWO_PI / abs(rate)
    # Python modulo maps a negative quotient to the positive residue — exactly
    # the "wrap forward until the next opportunity" semantics we want.
    return (delta / rate) % period


def _require_positive(value: float, label: str) -> None:
    if not (
        isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0.0
    ):
        raise ValueError(f"{label} must be a positive number")
