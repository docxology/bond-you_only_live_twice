"""Real-data tests for the emitter localisation (TDOA) module.

Verifies sensor layout, exact range-difference measurements, Gauss-Newton
convergence to the true emitter, error branches, and a noisy-measurement
regime, all deterministic and mock-free.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from you_only_live_twice.emitter_localization import (
    build_sensor_posts,
    localization_error,
    localize_tdoa,
    tdoa_measurements,
)


def _sensors() -> tuple[tuple[float, float], ...]:
    return build_sensor_posts((0.0, 0.0), ring_radius_m=30_000.0, count=5)


def test_build_sensor_posts_layout() -> None:
    posts = build_sensor_posts((1000.0, 2000.0), ring_radius_m=10_000.0, count=4)
    assert len(posts) == 4
    # Each post sits at the requested radius from the centre.
    for p in posts:
        assert math.hypot(p[0] - 1000.0, p[1] - 2000.0) == pytest.approx(10_000.0)
    # Deterministic.
    assert posts == build_sensor_posts(
        (1000.0, 2000.0), ring_radius_m=10_000.0, count=4
    )
    with pytest.raises(ValueError):
        build_sensor_posts((0.0, 0.0), ring_radius_m=100.0, count=3)


def test_tdoa_measurements() -> None:
    sensors = _sensors()
    emitter = (5000.0, -3000.0)
    deltas = tdoa_measurements(sensors, emitter)
    assert deltas.shape == (4,)
    # Reference sensor is index 0; all deltas are range differences in metres.
    for i in range(1, len(sensors)):
        d_true = math.hypot(
            emitter[0] - sensors[i][0], emitter[1] - sensors[i][1]
        ) - math.hypot(emitter[0] - sensors[0][0], emitter[1] - sensors[0][1])
        assert float(deltas[i - 1]) == pytest.approx(d_true, abs=1e-6)


def test_localize_tdoa_recovers_true_emitter() -> None:
    sensors = _sensors()
    true = (5000.0, -3000.0)
    deltas = tdoa_measurements(sensors, true)
    x0 = np.array([0.0, 0.0])
    result = localize_tdoa(sensors, deltas, x0=x0)
    error = localization_error(result["estimate"], true)
    assert error < 1.0  # metres (noiseless -> machine precision)
    assert result["iterations"] <= 50
    assert len(result["estimate"]) == 2


def test_localize_tdoa_farther_emitter() -> None:
    sensors = _sensors()
    true = (18_000.0, 12_000.0)
    deltas = tdoa_measurements(sensors, true)
    result = localize_tdoa(sensors, deltas, x0=np.array([0.0, 0.0]))
    assert localization_error(result["estimate"], true) < 1.0


def test_localize_tdoa_requires_baselines() -> None:
    sensors = build_sensor_posts((0.0, 0.0), ring_radius_m=1000.0, count=4)
    with pytest.raises(ValueError):
        localize_tdoa(sensors, np.array([1.0, 2.0]), x0=np.array([0.0, 0.0]))


def test_localize_tdoa_singular_geometry() -> None:
    # Collinear sensors make the normal equations singular (degenerate).
    sensors = (
        (0.0, 0.0),
        (1000.0, 0.0),
        (2000.0, 0.0),
        (3000.0, 0.0),
        (4000.0, 0.0),
    )
    emitter = (1500.0, 500.0)
    deltas = tdoa_measurements(sensors, emitter)
    with pytest.raises(ValueError):
        localize_tdoa(sensors, deltas, x0=np.array([500.0, 100.0]))


def test_tdoa_noisy_measurements_bounded_error() -> None:
    sensors = _sensors()
    true = (5000.0, -3000.0)
    clean = tdoa_measurements(sensors, true)
    noisy = clean + np.array([0.0, 5.0, -5.0, 5.0])  # small fixed perturbation
    result = localize_tdoa(sensors, noisy, x0=np.array([0.0, 0.0]))
    # With small measurement noise the error stays bounded (tens of metres),
    # proving the solver is well-behaved.
    assert localization_error(result["estimate"], true) < 200.0


def test_localization_error_simple() -> None:
    assert localization_error(np.array([1.0, 2.0]), (4.0, 6.0)) == pytest.approx(5.0)
