"""Emitter localization: locate the base's RF emitter by TDOA multilateration.

The final discovery asset is the base's own transmitter: passive sensors time
the arrival of a single burst, and the *time differences of arrival* (TDOA)
between sensor pairs define hyperbolae whose intersection is the emitter
position. This module implements that classic hyperbolic localisation problem
using the Taylor-series (Gauss–Newton) estimator of Foy (1976), the standard
iterative solution to the passive-geolocation equations also treated by
Chan & Ho (1994) and in radar/EW texts (Skolnik 2001):

* :func:`tdoa_measurements` — exact range-difference measurements
  :math:`d_i = \\lVert e - s_i\\rVert - \\lVert e - s_0\\rVert` against a
  reference sensor :math:`s_0`;
* :func:`localize_tdoa` — Gauss–Newton least squares that drives the residuals
  :math:`r_i(x) = \\lVert x-s_i\\rVert - \\lVert x-s_0\\rVert - d_i` to zero,
  starting from an initial guess and iterating the normal equations;
* :func:`time_differences_to_ranges` — the receiver-side conversion from
  measured arrival-time differences (seconds) to range differences (metres);
* :func:`localization_error` — the achieved accuracy in metres.

What the noise-free case does and does not prove: feeding
:func:`localize_tdoa` the output of :func:`tdoa_measurements` for the same
point is a *round-trip identity of the forward model*. Convergence to machine
precision shows the solver inverts the model it was handed — a real and
necessary correctness check — but it is not a measurement, and it cannot
corroborate the emitter's position against any other sensor. Only measurements
carrying independent error (see ``EMITTER_TIME_NOISE_S`` in
:mod:`you_only_live_twice.scenario`, which perturbs the receiver-side arrival
times before the solve) produce an accuracy figure that could have come out
worse. The module is deterministic and infrastructure-free.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

__all__ = [
    "build_sensor_posts",
    "localization_error",
    "localize_tdoa",
    "tdoa_error_sweep",
    "tdoa_measurements",
    "time_differences_to_ranges",
]

#: Speed of light, m/s.
SPEED_OF_LIGHT = 2.99792458e8


def build_sensor_posts(
    center: tuple[float, float],
    ring_radius_m: float,
    count: int = 5,
    start_angle_deg: float = 0.0,
) -> tuple[tuple[float, float], ...]:
    """Place ``count`` sensors on a circle around ``center`` at a fixed radius.

    Sensor angles are equally spaced from ``start_angle_deg``, so the post
    layout is fully deterministic.
    """
    if count < 4:
        raise ValueError("TDOA localisation needs at least 4 sensors (3 baselines)")
    posts: list[tuple[float, float]] = []
    start = math.radians(start_angle_deg)
    for i in range(count):
        angle = start + 2.0 * math.pi * i / count
        x = center[0] + ring_radius_m * math.cos(angle)
        y = center[1] + ring_radius_m * math.sin(angle)
        posts.append((x, y))
    return tuple(posts)


def tdoa_measurements(
    sensor_positions: tuple[tuple[float, float], ...],
    emitter: tuple[float, float],
) -> np.ndarray:
    """Exact range differences :math:`d_i` relative to the first sensor, metres.

    ``d_i = ||e - s_i|| - ||e - s_0||`` for :math:`i = 1..n-1`. The measured
    quantity in the field is a *time* difference; multiplying it by
    :data:`SPEED_OF_LIGHT` converts it to the range difference this module
    works in, so the propagation speed never enters the geometry itself.
    """
    sensor0 = sensor_positions[0]
    base = math.hypot(emitter[0] - sensor0[0], emitter[1] - sensor0[1])
    deltas: list[float] = []
    for sensor in sensor_positions[1:]:
        dist = math.hypot(emitter[0] - sensor[0], emitter[1] - sensor[1])
        deltas.append(dist - base)
    return np.asarray(deltas, dtype=float)


def time_differences_to_ranges(
    time_deltas: np.ndarray, c: float = SPEED_OF_LIGHT
) -> np.ndarray:
    """Convert measured arrival-time differences (s) to range differences (m).

    This is the one place :data:`SPEED_OF_LIGHT` is used: TDOA receivers report
    seconds, while :func:`localize_tdoa` solves the geometry in metres.
    """
    if c <= 0.0:
        raise ValueError("propagation speed must be positive")
    return np.asarray(time_deltas, dtype=float) * c


def _residuals_and_jacobian(
    x: np.ndarray,
    sensor_positions: tuple[tuple[float, float], ...],
    deltas: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Residual vector and Jacobian of the TDOA equations at ``x``."""
    sensor0 = np.asarray(sensor_positions[0], dtype=float)
    s0_dist = float(np.linalg.norm(x - sensor0))
    residuals: list[float] = []
    jacobian: list[np.ndarray] = []
    for i, sensor in enumerate(sensor_positions[1:], start=1):
        si = np.asarray(sensor, dtype=float)
        dist = float(np.linalg.norm(x - si))
        residuals.append(dist - s0_dist - float(deltas[i - 1]))
        jacobian.append(((x - si) / dist) - ((x - sensor0) / s0_dist))
    return np.asarray(residuals, dtype=float), np.asarray(jacobian, dtype=float)


def localize_tdoa(
    sensor_positions: tuple[tuple[float, float], ...],
    deltas: np.ndarray,
    x0: np.ndarray,
    max_iter: int = 100,
    tol: float = 1e-9,
) -> dict[str, Any]:
    """Gauss–Newton solution of the TDOA equations from an initial guess.

    Returns a dict with ``estimate`` (2-vector), ``iterations``, and the final
    ``residual_norm``. Raises ``ValueError`` when the normal equations are
    singular (degenerate sensor geometry) or the solver fails to converge.
    """
    if len(deltas) < 3:
        raise ValueError("at least 3 baselines (4 sensors) are required")
    x = np.asarray(x0, dtype=float).copy()
    for _ in range(max_iter):
        residuals, jacobian = _residuals_and_jacobian(x, sensor_positions, deltas)
        normal = jacobian.T @ jacobian
        rhs = -(jacobian.T @ residuals)
        try:
            step = np.linalg.solve(normal, rhs)
        except np.linalg.LinAlgError as exc:
            raise ValueError(
                "TDOA normal equations are singular (degenerate geometry)"
            ) from exc
        x = x + step
        if float(np.linalg.norm(step)) < tol:
            return {
                "estimate": x,
                "iterations": _ + 1,
                "residual_norm": float(np.linalg.norm(residuals)),
            }
    raise ValueError("TDOA Gauss-Newton failed to converge")


def localization_error(estimate: np.ndarray, true: tuple[float, float]) -> float:
    """Euclidean distance between the estimate and the true emitter, metres."""
    return float(np.linalg.norm(np.asarray(estimate) - np.asarray(true)))


def tdoa_error_sweep(
    sensor_positions: tuple[tuple[float, float], ...],
    emitter: tuple[float, float],
    noise_levels_s: tuple[float, ...],
    initial_guess: np.ndarray,
    realizations: int = 24,
    base_seed: int = 1967,
) -> list[dict[str, float]]:
    """Deterministic localisation-error envelope: mean error vs timing jitter.

    For each single-sigma jitter level the receiver arrival-time differences
    are perturbed by ``realizations`` fixed-seed Gaussian draws (each draw
    re-seeded deterministically from ``base_seed``), the TDOA problem is
    solved from the same initial guess, and the mean achieved localisation
    error is reported. Averaging over independent realizations removes the
    per-draw scatter, so the envelope rises smoothly with the timing jitter
    and turns the single-operating-point ``localize_tdoa`` error into an
    accuracy curve.

    Returns a list of ``{"noise_s": sigma, "error_m": mean_error}`` in the
    order of ``noise_levels_s``. Deterministic and infrastructure-free.
    """
    range_deltas = tdoa_measurements(sensor_positions, emitter)
    rows: list[dict[str, float]] = []
    for level_index, sigma in enumerate(noise_levels_s):
        errors: list[float] = []
        for realization in range(realizations):
            rng = np.random.default_rng(
                base_seed * 1000 + level_index * 1000 + realization
            )
            time_deltas = range_deltas / SPEED_OF_LIGHT + rng.normal(
                0.0, sigma, range_deltas.shape
            )
            measured = time_differences_to_ranges(time_deltas)
            estimate = localize_tdoa(
                sensor_positions,
                measured,
                x0=np.asarray(initial_guess, dtype=float),
            )
            errors.append(localization_error(estimate["estimate"], emitter))
        rows.append({"noise_s": float(sigma), "error_m": float(np.mean(errors))})
    return rows
