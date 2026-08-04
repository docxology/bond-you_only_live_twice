"""Space-capsule rendezvous / intercept window solving.

This module implements deterministic, real orbital mechanics for the VOLCANO
mission's first capability: deciding *when* a chase spacecraft can rendezvous
with, or intercept, a target spacecraft.

The physics is standard two-body / Keplerian orbital mechanics (Vallado's
*Fundamentals of Astrodynamics and Applications*):

* circular-orbit propagation from the classical orbital elements
  (semi-major axis :math:`a`, inclination :math:`i`, right ascension of the
  ascending node :math:`\\Omega`, argument of latitude :math:`u`);
* the line-of-sight geometry between two satellites — slant range and the
  elevation of the target above the chaser's local horizontal plane;
* rendezvous window search: contiguous intervals where range :math:`\\le`
  ``max_range`` **and** elevation :math:`\\ge` ``min_elevation``;
* :math:`\\Delta v` budget and transfer time for a coplanar Hohmann transfer
  intercept.

All outputs are deterministic: no random draws, no wall-clock dependence, no
external calls. The module is infrastructure-free and importable without
BOND-API; :mod:`you_only_live_twice.mission` wires it into the protocol.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

__all__ = [
    "CircularOrbit",
    "RendezvousWindow",
    "circular_state",
    "find_rendezvous_windows",
    "hohmann_transfer",
    "mean_motion",
    "orbit_to_eci",
    "orbital_period",
    "range_and_elevation",
]

#: Standard gravitational parameter of Earth, m^3 / s^2 (WGS-84).
MU_EARTH = 3.986004418e14

#: Mean radius of Earth, m.
R_EARTH = 6_371_000.0

#: Degrees per radian.
_DEG = 180.0 / math.pi


@dataclass(frozen=True)
class CircularOrbit:
    """A circular orbit characterized by its radius and plane.

    ``initial_phase`` is the argument of latitude :math:`u_0` (in-plane angle
    from the ascending node) at :math:`t=0`, in radians.
    """

    radius: float  #: orbital radius (semi-major axis), metres.
    inclination: float  #: inclination, radians.
    raan: float  #: right ascension of the ascending node, radians.
    initial_phase: float  #: argument of latitude at t=0, radians.

    @classmethod
    def from_altitude(
        cls,
        altitude_km: float,
        inclination: float = 0.0,
        raan: float = 0.0,
        initial_phase: float = 0.0,
    ) -> CircularOrbit:
        """Build an orbit from a circular altitude above Earth's surface.

        Args:
            altitude_km: altitude above the mean Earth radius, kilometres.
            inclination: orbital inclination, radians.
            raan: right ascension of the ascending node, radians.
            initial_phase: argument of latitude at t=0, radians.
        """
        if altitude_km < 0.0:
            raise ValueError("altitude_km must be >= 0")
        return cls(
            radius=R_EARTH + altitude_km * 1e3,
            inclination=inclination,
            raan=raan,
            initial_phase=initial_phase,
        )


@dataclass(frozen=True)
class RendezvousWindow:
    """A contiguous window during which a rendezvous / intercept is possible.

    Geometry satisfies ``range <= max_range`` and ``elevation >= min_elevation``
    for the whole window. ``min_range_km`` is the closest approach reached and
    ``peak_elevation_deg`` the highest target elevation over the window.
    """

    start_s: float  #: window start, seconds since mission t0.
    end_s: float  #: window end, seconds since mission t0.
    min_range_km: float  #: closest approach during the window, km.
    peak_elevation_deg: float  #: peak elevation during the window, degrees.

    @property
    def duration_s(self) -> float:
        """Window length in seconds."""
        return self.end_s - self.start_s


def mean_motion(radius: float, mu: float = MU_EARTH) -> float:
    """Mean orbital motion :math:`n = \\sqrt{\\mu / a^3}` for a circular orbit, rad/s."""
    _require_positive(radius, "radius")
    return math.sqrt(mu / radius**3)


def orbital_period(radius: float, mu: float = MU_EARTH) -> float:
    """Orbital period :math:`T = 2\\pi \\sqrt{a^3/\\mu}`, seconds."""
    return 2.0 * math.pi / mean_motion(radius, mu)


def orbit_to_eci(
    radius: float,
    eccentricity: float,
    inclination: float,
    raan: float,
    argp: float,
    true_anomaly: float,
    mu: float = MU_EARTH,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert classical orbital elements to ECI position and velocity.

    Uses the standard perifocal → ECI 3-1-3 rotation sequence. For circular
    orbits pass ``eccentricity=0`` and ``true_anomaly`` coinciding with mean
    anomaly.

    Returns:
        ``(position_eci, velocity_eci)`` 3-vectors, metres.
    """
    if eccentricity < 0.0:
        raise ValueError("eccentricity must be >= 0")
    if eccentricity >= 1.0:
        raise ValueError("eccentricity must be < 1 (bound orbit)")
    p = radius * (1.0 - eccentricity * eccentricity)  # semi-latus rectum
    r = p / (1.0 + eccentricity * math.cos(true_anomaly))

    r_pf = np.array([r * math.cos(true_anomaly), r * math.sin(true_anomaly), 0.0])
    v_pf = math.sqrt(mu / p) * np.array(
        [-math.sin(true_anomaly), eccentricity + math.cos(true_anomaly), 0.0]
    )

    co, so = math.cos(raan), math.sin(raan)
    ci, si = math.cos(inclination), math.sin(inclination)
    cw, sw = math.cos(argp + true_anomaly), math.sin(argp + true_anomaly)
    rotation = np.array(
        [
            [co * cw - so * sw * ci, -co * sw - so * cw * ci, so * si],
            [so * cw + co * sw * ci, -so * sw + co * cw * ci, -co * si],
            [sw * si, cw * si, ci],
        ]
    )
    return rotation @ r_pf, rotation @ v_pf


def circular_state(
    orbit: CircularOrbit,
    t_s: float,
    mu: float = MU_EARTH,
) -> tuple[np.ndarray, np.ndarray]:
    """Propagate a circular orbit to time ``t_s``: ECI position and velocity.

    For a circular orbit the true anomaly advances linearly with mean motion,
    so :math:`\\nu(t) = u_0 + n t`.
    """
    nu = orbit.initial_phase + mean_motion(orbit.radius, mu) * t_s
    return orbit_to_eci(orbit.radius, 0.0, orbit.inclination, orbit.raan, 0.0, nu, mu)


def _rayleigh_distance(r: np.ndarray) -> float:
    """Euclidean magnitude of a 3-vector."""
    return float(np.linalg.norm(r))


def range_and_elevation(
    chaser_pos: np.ndarray,
    chaser_vel: np.ndarray,
    target_pos: np.ndarray,
) -> tuple[float, float]:
    """Slant range and elevation of ``target_pos`` as seen from the chaser.

    Elevation is the angle of the line-of-sight above the chaser's local
    horizontal plane (the plane perpendicular to the local radial direction),
    in radians.

    Returns:
        ``(range_m, elevation_rad)``.
    """
    rho = target_pos - chaser_pos
    r_hat = chaser_pos / _rayleigh_distance(chaser_pos)
    rho_radial = float(np.dot(rho, r_hat))
    rho_horiz = _rayleigh_distance(rho - rho_radial * r_hat)
    return _rayleigh_distance(rho), math.atan2(rho_radial, rho_horiz)


def _require_positive(value: float, label: str) -> None:
    if not (
        isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0.0
    ):
        raise ValueError(f"{label} must be a positive number")


def find_rendezvous_windows(
    chaser: CircularOrbit,
    target: CircularOrbit,
    t_start: float = 0.0,
    t_end: float = 86400.0,
    dt: float = 60.0,
    max_range_km: float = 500.0,
    min_elevation_deg: float = 10.0,
    mu: float = MU_EARTH,
) -> tuple[RendezvousWindow, ...]:
    """Find contiguous rendezvous / intercept windows over the time span.

    The search steps the clock from ``t_start`` to ``t_end`` in ``dt`` second
    steps, propagating both satellites and testing the line-of-sight geometry.
    Window geometry (min range, peak elevation) is sampled at the step where it
    is best inside each contiguous run, which keeps the result deterministic
    and cheap.

    Returns:
        A tuple of :class:`RendezvousWindow`, ordered by start time.
    """
    if t_end <= t_start:
        raise ValueError("t_end must be greater than t_start")
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    max_range_m = max_range_km * 1e3
    min_elevation = math.radians(min_elevation_deg)

    inside: list[bool] = []
    times = np.arange(t_start, t_end + dt, dt)
    for t in times:
        c_pos, c_vel = circular_state(chaser, float(t), mu)
        t_pos, _ = circular_state(target, float(t), mu)
        rng, elev = range_and_elevation(c_pos, c_vel, t_pos)
        inside.append(rng <= max_range_m and elev >= min_elevation)

    windows: list[RendezvousWindow] = []
    i = 0
    n = len(times)
    while i < n:
        if not inside[i]:
            i += 1
            continue
        start = float(times[i])
        best_range_m = float("inf")
        best_elev = -float("inf")
        j = i
        while j < n and inside[j]:
            c_pos, c_vel = circular_state(chaser, float(times[j]), mu)
            t_pos, _ = circular_state(target, float(times[j]), mu)
            rng, elev = range_and_elevation(c_pos, c_vel, t_pos)
            best_range_m = min(best_range_m, rng)
            best_elev = max(best_elev, elev)
            j += 1
        end = float(times[j - 1]) + float(dt)
        windows.append(
            RendezvousWindow(
                start_s=start,
                end_s=end,
                min_range_km=best_range_m / 1e3,
                peak_elevation_deg=math.degrees(best_elev),
            )
        )
        i = j
    return tuple(windows)


def hohmann_transfer(
    chaser_radius: float,
    target_radius: float,
    mu: float = MU_EARTH,
) -> dict[str, float]:
    """Coplanar Hohmann transfer: :math:`\\Delta v` budget and transfer time.

    Computes the classic two-burn Hohmann transfer between two circular orbits
    at radii ``chaser_radius`` and ``target_radius``.

    Returns a dict with ``delta_v1``, ``delta_v2``, ``delta_v_total`` (m/s) and
    ``transfer_time_s`` (s).
    """
    _require_positive(chaser_radius, "chaser_radius")
    _require_positive(target_radius, "target_radius")
    a1, a2 = chaser_radius, target_radius
    v1 = math.sqrt(mu / a1)  # chaser circular speed
    v2 = math.sqrt(mu / a2)  # target circular speed
    a_transfer = 0.5 * (a1 + a2)  # transfer orbit semi-major axis
    v_peri = math.sqrt(mu * (2.0 / a1 - 1.0 / a_transfer))
    v_apo = math.sqrt(mu * (2.0 / a2 - 1.0 / a_transfer))
    delta_v1 = abs(v_peri - v1)
    delta_v2 = abs(v2 - v_apo)
    transfer_time_s = math.pi * math.sqrt(a_transfer**3 / mu)
    return {
        "delta_v1": delta_v1,
        "delta_v2": delta_v2,
        "delta_v_total": delta_v1 + delta_v2,
        "transfer_time_s": transfer_time_s,
    }
