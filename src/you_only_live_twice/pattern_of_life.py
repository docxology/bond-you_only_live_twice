"""Base pattern-of-life analysis.

The third VOLCANO capability: given a time series of observed activities at an
adversary base (ingress / egress movements, dispatch events, RF bursts), derive a
quantitative *pattern of life* — the operational rhythm the base keeps. This is
standard time-series analysis over real (synthetic-but-methodical) event data:

* hourly activity histogram across a week (168 one-hour bins);
* a daily activity profile (mean activity per hour of day) → tells when the
  base is busiest;
* autocorrelation-based dominant periodicity → distinguishes a daily (24 h)
  rhythm from weekly (168 h) or non-periodic behaviour;
* contiguous peak-activity windows and an operational-tempo classification.

Everything is deterministic and dependency-light (stdlib + numpy). Fixed seeds
govern the synthetic schedule so results are reproducible byte-for-byte.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = [
    "BaseActivity",
    "aggregate_autocorrelation",
    "build_weekly_activity_schedule",
    "daily_activity_profile",
    "dominant_period_hours",
    "duty_cycle",
    "hourly_histogram",
    "operational_tempo",
    "pattern_summary",
    "peak_activity_windows",
]

#: Seconds in one hour.
SECONDS_PER_HOUR = 3_600.0
#: Seconds in one day.
SECONDS_PER_DAY = 86_400.0
#: Seconds in a seven-day week.
SECONDS_PER_WEEK = 7 * SECONDS_PER_DAY

#: Activity kinds modelled by the synthetic schedule.
ACTIVITY_KINDS = ("ingress", "egress", "dispatch", "rf")


@dataclass(frozen=True)
class BaseActivity:
    """A single observed activity event at the base.

    ``timestamp_s`` is seconds since the start of the observation week and
    ``kind`` is one of the modelled activity kinds.
    """

    timestamp_s: float
    kind: str

    def __post_init__(self) -> None:
        if self.timestamp_s < 0.0 or self.timestamp_s >= SECONDS_PER_WEEK:
            raise ValueError("timestamp_s must lie within the observation week [0, 7d)")
        if self.kind not in ACTIVITY_KINDS:
            raise ValueError(f"kind must be one of {ACTIVITY_KINDS}")


def build_weekly_activity_schedule(
    base_rate_per_hour: float = 4.0,
    seed: int = 1967,
    num_days: int = 7,
) -> tuple[BaseActivity, ...]:
    """Generate a deterministic weekly activity schedule.

    Activity follows a diurnal rhythm — quiet overnight, peaking twice a day
    (a morning and an evening window) — plus a smooth noise floor. Events are
    drawn by rejection sampling against the rate envelope, so the *shape* of
    the pattern of life is exactly controlled and reproducible.

    Returns an ascending tuple of :class:`BaseActivity`.
    """
    if base_rate_per_hour <= 0.0:
        raise ValueError("base_rate_per_hour must be positive")
    if num_days < 1:
        raise ValueError("num_days must be >= 1")
    rng = np.random.default_rng(seed)
    horizon_s = num_days * SECONDS_PER_DAY

    def rate_at(t: float) -> float:
        hour = (t % SECONDS_PER_DAY) / SECONDS_PER_HOUR
        morning = math.exp(-((hour - 8.0) ** 2) / (2.0 * 1.6**2))
        evening = math.exp(-((hour - 20.0) ** 2) / (2.0 * 2.0**2))
        return base_rate_per_hour * (0.15 + morning + evening)

    # Rejection sampling: draw candidate times uniformly against a max rate,
    # keep with probability rate/max_rate. Times are in seconds, and the
    # candidate arrival rate is max_rate per hour, so the exponential scale
    # (mean inter-arrival) is 3600/max_rate seconds.
    max_rate = max(rate_at(t) for t in np.linspace(0.0, horizon_s, 2000))
    scale_s = SECONDS_PER_HOUR / max_rate
    events: list[BaseActivity] = []
    t = 0.0
    attempts = 0
    while t < horizon_s and attempts < 200_000:
        attempts += 1
        t += rng.exponential(scale_s)
        if t >= horizon_s:
            break
        if rng.uniform() <= rate_at(t) / max_rate:
            kind = ACTIVITY_KINDS[int(rng.integers(0, len(ACTIVITY_KINDS)))]
            events.append(BaseActivity(timestamp_s=t, kind=kind))
    events.sort(key=lambda e: e.timestamp_s)
    return tuple(events)


def hourly_histogram(events: tuple[BaseActivity, ...], num_days: int = 7) -> np.ndarray:
    """Count activity per one-hour bin over the observation window.

    Returns a vector of length ``num_days * 24``.
    """
    bins = num_days * 24
    counts = np.zeros(bins, dtype=int)
    for event in events:
        idx = min(int(event.timestamp_s // SECONDS_PER_HOUR), bins - 1)
        counts[idx] += 1
    return counts.astype(float)


def daily_activity_profile(events: tuple[BaseActivity, ...]) -> np.ndarray:
    """Mean activity per hour of day across the observed days (length 24)."""
    hist = hourly_histogram(events, num_days=7)
    return hist.reshape(7, 24).mean(axis=0)  # type: ignore[no-any-return]


def aggregate_autocorrelation(
    series: np.ndarray, max_lag: int | None = None
) -> np.ndarray:
    """Normalized autocorrelation of ``series`` for lags ``0..max_lag``."""
    x = series - float(series.mean())
    n = len(x)
    variance = float(np.dot(x, x))
    if variance <= 0.0:
        return np.zeros(max_lag + 1 if max_lag is not None else n, dtype=float)
    max_lag = n - 1 if max_lag is None else min(max_lag, n - 1)
    acf: list[float] = []
    for lag in range(max_lag + 1):
        acf.append(float(np.dot(x[: n - lag], x[lag:])) / variance)
    return np.asarray(acf)


def dominant_period_hours(
    series: np.ndarray,
    min_hours: float = 8.0,
    max_hours: float = 192.0,
) -> float:
    """Estimated dominant periodicity of an hourly series, in hours.

    Finds the lag (in whole hours) that maximizes autocorrelation within the
    plausible operational range ``[min_hours, max_hours]``. Returns NaN when the
    series shows no meaningful periodicity (all-zero).
    """
    series = np.asarray(series, dtype=float)
    if float(series.max()) <= 0.0:
        return float("nan")
    max_lag = int(min(max_hours, len(series) - 1))
    min_lag = int(max(1, math.ceil(min_hours)))
    acf = aggregate_autocorrelation(series, max_lag=max_lag)
    search = acf[min_lag : max_lag + 1]
    if search.size == 0:
        return float("nan")
    best = min_lag + int(np.argmax(search))
    return float(best)


def peak_activity_windows(
    profile: np.ndarray,
    percentile: float = 85.0,
    min_duration_h: int = 1,
) -> tuple[tuple[int, int], ...]:
    """Contiguous hours of the day above the given activity percentile.

    ``profile`` is a 24-length daily activity profile. Returns tuples of
    ``(start_hour, end_hour_exclusive)`` for windows lasting at least
    ``min_duration_h``.
    """
    if profile.shape != (24,):
        raise ValueError("profile must be a length-24 daily activity profile")
    if not 0.0 < percentile < 100.0:
        raise ValueError("percentile must be in (0, 100)")
    threshold = float(np.percentile(profile, percentile))
    windows: list[tuple[int, int]] = []
    i = 0
    while i < 24:
        if profile[i] < threshold:
            i += 1
            continue
        j = i
        while j < 24 and profile[j] >= threshold:
            j += 1
        if (j - i) >= min_duration_h:
            windows.append((i, j))
        i = j
    return tuple(windows)


def duty_cycle(events: tuple[BaseActivity, ...], num_days: int = 7) -> float:
    """Fraction of hourly bins that contain at least one activity event."""
    hist = hourly_histogram(events, num_days=num_days)
    if hist.size == 0:
        return 0.0
    return float(np.count_nonzero(hist > 0)) / float(hist.size)


def operational_tempo(
    events: tuple[BaseActivity, ...],
    low_h: float = 1.0,
    high_h: float = 4.0,
) -> str:
    """Classify operational tempo from mean activity rate (events/hour)."""
    mean_rate = len(events) / (7 * 24.0)
    if mean_rate < low_h:
        return "low"
    if mean_rate <= high_h:
        return "medium"
    return "high"


def pattern_summary(events: tuple[BaseActivity, ...]) -> dict[str, Any]:
    """One-call characterization of a base's pattern of life.

    Returns a dict of the headline metrics: histogram, daily profile, dominant
    period, peak windows, duty cycle, tempo, and event counts by kind.
    """
    hist = hourly_histogram(events)
    profile = daily_activity_profile(events)
    period = dominant_period_hours(profile)
    by_kind: dict[str, int] = {}
    for kind in ACTIVITY_KINDS:
        by_kind[kind] = sum(1 for e in events if e.kind == kind)
    return {
        "num_events": len(events),
        "hourly_histogram": hist,
        "daily_profile": profile,
        "dominant_period_hours": period,
        "peak_windows": peak_activity_windows(profile),
        "duty_cycle": duty_cycle(events),
        "tempo": operational_tempo(events),
        "events_by_kind": by_kind,
    }
