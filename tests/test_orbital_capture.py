"""Real-data tests for the orbital capture module.

Verifies relative-motion geometry, capture-window search, velocity matching, and
the phasing-lead / wait-time solution over deterministic circular orbits.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from you_only_live_twice.orbital_capture import (
    CaptureWindow,
    capture_windows,
    phasing_lead_angle,
    phasing_wait_time,
    relative_speed,
    relative_state,
    velocity_matching_budget,
)
from you_only_live_twice.rendezvous_windows import CircularOrbit, orbital_period


def _orbits() -> tuple[CircularOrbit, CircularOrbit]:
    chaser = CircularOrbit.from_altitude(
        550.0, inclination=math.radians(98.2), raan=math.radians(45.0)
    )
    target = CircularOrbit.from_altitude(
        800.0,
        inclination=math.radians(98.2),
        raan=math.radians(45.5),
        initial_phase=1.9,
    )
    return chaser, target


def test_relative_state_and_speed() -> None:
    chaser, target = _orbits()
    rho, rho_dot = relative_state(chaser, target, t_s=0.0)
    assert rho.shape == (3,)
    assert rho_dot.shape == (3,)
    speed = relative_speed(chaser, target, t_s=0.0)
    assert speed == pytest.approx(float(np.linalg.norm(rho_dot)), rel=1e-9)
    assert speed > 0.0


def test_velocity_matching_budget_matches_relative_speed() -> None:
    chaser, target = _orbits()
    t = 1000.0
    budget = velocity_matching_budget(chaser, target, t)
    assert budget == pytest.approx(relative_speed(chaser, target, t), rel=1e-9)


def test_capture_windows_reports_and_is_deterministic() -> None:
    chaser, target = _orbits()
    a = capture_windows(chaser, target, t_start=0.0, t_end=86400.0, dt=120.0)
    b = capture_windows(chaser, target, t_start=0.0, t_end=86400.0, dt=120.0)
    assert a == b
    assert all(isinstance(w, CaptureWindow) for w in a)
    for win in a:
        assert win.start_s < win.end_s
        assert win.duration_s > 0.0
        assert win.min_speed_m_s >= 0.0
        assert win.min_range_km >= 0.0


def test_capture_windows_empty_when_envelope_impossible() -> None:
    chaser, target = _orbits()
    windows = capture_windows(chaser, target, max_range_km=0.0001, max_speed_m_s=0.0001)
    assert windows == ()


def test_capture_windows_validates_span_and_dt() -> None:
    chaser, target = _orbits()
    with pytest.raises(ValueError):
        capture_windows(chaser, target, t_end=0.0, t_start=100.0)
    with pytest.raises(ValueError):
        capture_windows(chaser, target, dt=-5.0)


def test_capture_window_duration() -> None:
    win = CaptureWindow(start_s=10.0, end_s=25.0, min_range_km=1.0, min_speed_m_s=2.0)
    assert win.duration_s == pytest.approx(15.0)


def test_phasing_lead_angle_same_orbit_is_zero() -> None:
    r = 7.0e6
    lead = phasing_lead_angle(r, r)
    assert lead == pytest.approx(0.0, abs=1e-9)


def test_phasing_lead_angle_is_in_unit_range() -> None:
    lead = phasing_lead_angle(7.0e6, 8.0e6)
    assert 0.0 <= lead < 2.0 * math.pi


def test_phasing_lead_angle_validates() -> None:
    with pytest.raises(ValueError):
        phasing_lead_angle(-1.0, 8.0e6)
    with pytest.raises(ValueError):
        phasing_lead_angle(7.0e6, 0.0)


def test_phasing_wait_time_is_finite_and_deterministic() -> None:
    wait_a = phasing_wait_time(7.0e6, 8.0e6, initial_relative_phase=0.0)
    wait_b = phasing_wait_time(7.0e6, 8.0e6, initial_relative_phase=0.0)
    assert wait_a == wait_b
    assert wait_a >= 0.0
    assert math.isfinite(wait_a)
    # Advancing the initial phase by one full revolution returns the same wait.
    wait_shifted = phasing_wait_time(7.0e6, 8.0e6, initial_relative_phase=2.0 * math.pi)
    assert wait_shifted == pytest.approx(wait_a, rel=1e-6)


def test_phasing_wait_time_same_orbit() -> None:
    # Same orbit: phase is frozen, so already-correct -> 0, otherwise inf.
    assert phasing_wait_time(7.0e6, 7.0e6, initial_relative_phase=0.0) == 0.0
    assert phasing_wait_time(7.0e6, 7.0e6, initial_relative_phase=1.0) == float("inf")


def test_phasing_wait_time_validates() -> None:
    with pytest.raises(ValueError):
        phasing_wait_time(-1.0, 8.0e6, initial_relative_phase=0.0)


def test_orbital_period_consistency() -> None:
    chaser, _ = _orbits()
    # velocity matching over a full chaser period returns to the same value.
    period = orbital_period(chaser.radius)
    v0 = relative_speed(chaser, chaser, t_s=0.0)
    v1 = relative_speed(chaser, chaser, t_s=period)
    assert v0 == pytest.approx(v1, abs=1e-9)
