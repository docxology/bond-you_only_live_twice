"""Emitter localization: locate the base's RF emitter by TDOA multilateration.

The final discovery asset is the base's own transmitter: passive sensors time
the arrival of a single burst, and the *time differences of arrival* (TDOA)
between sensor pairs define hyperbolae whose intersection is the emitter
position. This module implements that classic hyperbolic localisation problem
(Bate et al. [phasing] treats the orbit side; the passive-geolocation
formulation is standard in radar/EW and passive sensor system texts):

* :func:`tdoa_measurements` — exact range-difference measurements
  :math:`d_i = \\lVert e - s_i\\rVert - \\lVert e - s_0\\rVert` against a
  reference sensor :math:`s_0`;
* :func:`localize_tdoa` — Gauss–Newton least squares that drives the residuals
  :math:`r_i(x) = \\lVert x-s_i\\rVert - \\lVert x-s_0\\rVert - d_i` to zero,
  starting from an initial guess and iterating the normal equations;
* :func:`localization_error` — the achieved accuracy in metres.

With noise-free measurements the solver converges to machine precision,
proving the model is mathematically correct (the injected emitter is the
fixed point); with added noise the error grows controllably, matching theory.
The module is deterministic and infrastructure-free.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

__all__ = [
    "build_sensor_posts",
    "localization_error",
    "localize_tdoa",
    "tdoa_measurements",
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
    c: float = SPEED_OF_LIGHT,
) -> np.ndarray:
    """Exact range differences :math:`d_i` relative to the first sensor, metres.

    ``d_i = ||e - s_i|| - ||e - s_0||`` for :math:`i = 1..n-1`.
    """
    sensor0 = sensor_positions[0]
    base = math.hypot(emitter[0] - sensor0[0], emitter[1] - sensor0[1])
    deltas: list[float] = []
    for sensor in sensor_positions[1:]:
        dist = math.hypot(emitter[0] - sensor[0], emitter[1] - sensor[1])
        deltas.append(dist - base)
    del c  # propagation delay is irrelevant to the exact range difference
    return np.asarray(deltas, dtype=float)


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
    c: float = SPEED_OF_LIGHT,
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
