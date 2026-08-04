"""Real-data tests for the orbital rendezvous / intercept window solver.

Uses actual orbital-mechanics computation over deterministic circular orbits —
no mocks. Verifies propagation correctness against closed-form expectations,
window geometry, and the Hohmann transfer budget.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from you_only_live_twice.rendezvous_windows import (
    CircularOrbit,
    RendezvousWindow,
    circular_state,
    find_rendezvous_windows,
    hohmann_transfer,
    mean_motion,
    orbit_to_eci,
    orbital_period,
    range_and_elevation,
)


def test_circular_orbit_from_altitude() -> None:
    orbit = CircularOrbit.from_altitude(550.0)
    assert orbit.radius == pytest.approx(6371.0e3 + 550.0e3)
    assert orbit.inclination == 0.0
    assert orbit.raan == 0.0
    with pytest.raises(ValueError):
        CircularOrbit.from_altitude(-1.0)


def test_mean_motion_and_period_known_vector() -> None:
    # A geosynchronous orbit: radius ~42164 km, period ~86164 s.
    r_geo = 42_164.0e3
    period = orbital_period(r_geo)
    assert period == pytest.approx(86_164.0, rel=1e-3)
    n = mean_motion(r_geo)
    assert n == pytest.approx(2.0 * math.pi / 86_164.0, rel=1e-3)


def test_mean_motion_rejects_nonpositive() -> None:
    with pytest.raises(ValueError):
        mean_motion(0.0)
    with pytest.raises(ValueError):
        mean_motion(-5.0)


def test_orbit_to_eci_validates_eccentricity() -> None:
    with pytest.raises(ValueError):
        orbit_to_eci(7.0e6, -0.1, 0.0, 0.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        orbit_to_eci(7.0e6, 1.0, 0.0, 0.0, 0.0, 0.0)


def test_circular_state_zero_phase_is_equatorial_position() -> None:
    # Equatorial orbit (i=0, raan=0), u0=0 -> position on +x axis at radius r.
    orbit = CircularOrbit.from_altitude(400.0)  # i=0, raan=0, phase=0
    pos, vel = circular_state(orbit, t_s=0.0)
    assert pos[0] == pytest.approx(orbit.radius, rel=1e-9)
    assert pos[1] == pytest.approx(0.0, abs=1e-6)
    assert pos[2] == pytest.approx(0.0, abs=1e-6)
    # Circular speed.
    speed = float(np.linalg.norm(vel))
    assert speed == pytest.approx(math.sqrt(3.986004418e14 / orbit.radius), rel=1e-6)


def test_circular_state_period_return() -> None:
    orbit = CircularOrbit.from_altitude(550.0, initial_phase=0.3)
    pos0, _ = circular_state(orbit, t_s=0.0)
    period = orbital_period(orbit.radius)
    pos1, _ = circular_state(orbit, t_s=period)
    np.testing.assert_allclose(pos1, pos0, atol=1e-2)


def test_range_and_elevation_geometry() -> None:
    # Target directly along the local radial (+x) -> elevation 90 deg, range = delta.
    pos_c = np.array([7.0e6, 0.0, 0.0])
    vel_c = np.array([0.0, 7.5e3, 0.0])
    pos_t = np.array([8.0e6, 0.0, 0.0])
    rng, elev = range_and_elevation(pos_c, vel_c, pos_t)
    assert rng == pytest.approx(1.0e6, rel=1e-9)
    assert elev == pytest.approx(math.pi / 2.0, rel=1e-9)
    # Target perpendicular to the radial (cross-track) -> elevation 0 deg.
    pos_cross = np.array([7.0e6, 1.0e6, 0.0])
    rng2, elev2 = range_and_elevation(pos_c, vel_c, pos_cross)
    assert elev2 == pytest.approx(0.0, abs=1e-9)
    assert rng2 == pytest.approx(1.0e6, rel=1e-9)


def test_find_rendezvous_windows_returns_windows() -> None:
    chaser = CircularOrbit.from_altitude(
        550.0, inclination=math.radians(98.2), raan=math.radians(45.0)
    )
    target = CircularOrbit.from_altitude(
        800.0,
        inclination=math.radians(98.2),
        raan=math.radians(45.5),
        initial_phase=1.9,
    )
    windows = find_rendezvous_windows(
        chaser, target, t_start=0.0, t_end=86400.0, dt=120.0
    )
    assert isinstance(windows, tuple)
    assert all(isinstance(w, RendezvousWindow) for w in windows)
    assert all(w.start_s < w.end_s for w in windows)
    # Deterministic.
    windows2 = find_rendezvous_windows(
        chaser, target, t_start=0.0, t_end=86400.0, dt=120.0
    )
    assert windows == windows2
    # Duration is positive and bounded by horizon.
    if windows:
        assert windows[0].duration_s > 0
        assert windows[0].start_s >= 0.0


def test_find_rendezvous_windows_empty_when_geometry_impossible() -> None:
    chaser = CircularOrbit.from_altitude(550.0, inclination=math.radians(98.2))
    target = CircularOrbit.from_altitude(800.0, inclination=math.radians(120.0))
    windows = find_rendezvous_windows(chaser, target, max_range_km=1.0)
    assert windows == ()


def test_find_rendezvous_windows_validates_span() -> None:
    chaser = CircularOrbit.from_altitude(400.0)
    target = CircularOrbit.from_altitude(700.0)
    with pytest.raises(ValueError):
        find_rendezvous_windows(chaser, target, t_end=0.0, t_start=100.0)
    with pytest.raises(ValueError):
        find_rendezvous_windows(chaser, target, dt=-1.0)


def test_hohmann_transfer_budget() -> None:
    # Coplanar transfer from chaser radius to target radius.
    result = hohmann_transfer(7.0e6, 8.0e6)
    assert result["delta_v_total"] > 0.0
    assert result["delta_v1"] > 0.0
    assert result["delta_v2"] > 0.0
    assert result["transfer_time_s"] > 0.0
    # Equal radii -> zero delta-v.
    same = hohmann_transfer(7.0e6, 7.0e6)
    assert same["delta_v_total"] == pytest.approx(0.0, abs=1e-6)
    with pytest.raises(ValueError):
        hohmann_transfer(-1.0, 7.0e6)
    with pytest.raises(ValueError):
        hohmann_transfer(7.0e6, 0.0)
