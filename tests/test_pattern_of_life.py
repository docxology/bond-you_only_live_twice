"""Real-data tests for the pattern-of-life analyzer.

Exercises the activity model, weekly/daily profiles, periodicity, peak windows,
tempo classification, and validation branches — all over deterministic data
with zero mocks.
"""

from __future__ import annotations

import numpy as np
import pytest

from you_only_live_twice.pattern_of_life import (
    ACTIVITY_KINDS,
    BaseActivity,
    aggregate_autocorrelation,
    build_weekly_activity_schedule,
    daily_activity_profile,
    dominant_period_hours,
    duty_cycle,
    hourly_histogram,
    operational_tempo,
    pattern_summary,
    peak_activity_windows,
)


def test_base_activity_validates() -> None:
    event = BaseActivity(timestamp_s=3600.0, kind="ingress")
    assert event.kind == "ingress"
    with pytest.raises(ValueError):
        BaseActivity(timestamp_s=-1.0, kind="ingress")
    with pytest.raises(ValueError):
        BaseActivity(timestamp_s=7 * 86400.0, kind="ingress")
    with pytest.raises(ValueError):
        BaseActivity(timestamp_s=3600.0, kind="teleport")


def test_build_schedule_is_deterministic_and_valid() -> None:
    a = build_weekly_activity_schedule(seed=1967)
    b = build_weekly_activity_schedule(seed=1967)
    assert a == b
    assert a
    assert all(0.0 <= e.timestamp_s < 7 * 86400.0 for e in a)
    assert all(e.kind in ACTIVITY_KINDS for e in a)
    timestamps = [e.timestamp_s for e in a]
    assert timestamps == sorted(timestamps)
    # A different seed gives a different (but still valid) schedule.
    c = build_weekly_activity_schedule(seed=1)
    assert a != c


def test_build_schedule_validates() -> None:
    with pytest.raises(ValueError):
        build_weekly_activity_schedule(base_rate_per_hour=0.0)
    with pytest.raises(ValueError):
        build_weekly_activity_schedule(num_days=0)
    with pytest.raises(ValueError):
        build_weekly_activity_schedule(base_rate_per_hour=-2.0)


def test_hourly_histogram_and_daily_profile() -> None:
    events = (
        BaseActivity(3600.0, "ingress"),  # hour 1
        BaseActivity(2 * 3600.0, "rf"),  # hour 2
        BaseActivity(24 * 3600.0, "egress"),  # hour 24 (day 1 hour 0)
    )
    hist = hourly_histogram(events)
    assert hist.shape == (168,)
    assert hist[1] == 1.0
    assert hist[2] == 1.0
    assert hist[24] == 1.0
    profile = daily_activity_profile(events)
    assert profile.shape == (24,)
    # Across 7 days, hourly mean bins are small.
    assert profile[1] == pytest.approx(1.0 / 7.0)
    assert profile[0] == pytest.approx(1.0 / 7.0)


def test_aggregate_autocorrelation() -> None:
    series = np.array([1.0, 2.0, 3.0, 2.0, 1.0])
    acf = aggregate_autocorrelation(series, max_lag=4)
    assert acf[0] == pytest.approx(1.0)
    assert acf.shape == (5,)
    # Constant series -> zero autocorrelation (variance = 0 branch).
    flat = np.ones(6)
    flat_acf = aggregate_autocorrelation(flat, max_lag=3)
    np.testing.assert_allclose(flat_acf, 0.0)


def test_dominant_period_hours() -> None:
    # A clean 24-hour periodicity (one spike per day).
    spikes = np.zeros(7 * 24)
    for day in range(7):
        spikes[day * 24] = 1.0
    period = dominant_period_hours(spikes, min_hours=8.0, max_hours=192.0)
    assert period == pytest.approx(24.0, abs=1.0)
    # Zero series -> NaN.
    assert np.isnan(dominant_period_hours(np.zeros(168)))


def test_peak_activity_windows() -> None:
    # Craft a profile with a uniform background and clearly-tall peak block.
    profile = np.full(24, 1.0)
    profile[7:10] = 6.0  # a 3-hour morning spike
    profile[20] = 5.0  # a 1-hour evening spike below the top
    windows = peak_activity_windows(profile, percentile=90.0)
    assert windows == ((7, 10),)
    with pytest.raises(ValueError):
        peak_activity_windows(np.zeros(23))
    with pytest.raises(ValueError):
        peak_activity_windows(np.zeros(24), percentile=0.0)
    with pytest.raises(ValueError):
        peak_activity_windows(np.zeros(24), percentile=100.0)
    # min_duration filters a single-hour spike (length 1 < min_duration_h).
    short = np.full(24, 1.0)
    short[5] = 9.0
    assert peak_activity_windows(short, percentile=99.0, min_duration_h=2) == ()


def test_duty_cycle() -> None:
    events = (BaseActivity(0.0, "rf"), BaseActivity(3600.0, "rf"))
    # 2 occupied hours out of 168.
    assert duty_cycle(events) == pytest.approx(2.0 / 168.0)


def test_operational_tempo_classification() -> None:
    # Very low rate -> low.
    low = build_weekly_activity_schedule(base_rate_per_hour=0.2, seed=3)
    assert operational_tempo(low, low_h=0.5, high_h=6.0) == "low"
    # Medium default scenario (mean rate safely inside [1, 4] events/hour).
    med = build_weekly_activity_schedule(base_rate_per_hour=3.0, seed=5)
    assert operational_tempo(med) == "medium"
    # Very high rate -> high.
    high = build_weekly_activity_schedule(base_rate_per_hour=12.0, seed=7)
    assert operational_tempo(high, low_h=1.0, high_h=4.0) == "high"


def test_pattern_summary() -> None:
    events = build_weekly_activity_schedule(seed=1967)
    summary = pattern_summary(events)
    assert summary["num_events"] == len(events)
    assert summary["hourly_histogram"].shape == (168,)
    assert summary["daily_profile"].shape == (24,)
    assert "tempo" in summary
    assert "duty_cycle" in summary
    assert set(summary["events_by_kind"]) == set(ACTIVITY_KINDS)
    assert sum(summary["events_by_kind"].values()) == len(events)


def test_dominant_period_hours_empty_search_returns_nan() -> None:
    """A search window with no valid lags (max < min) must yield NaN, not a bogus period."""
    series = np.ones(100)
    assert np.isnan(dominant_period_hours(series, min_hours=5.0, max_hours=3.0))


def test_duty_cycle_empty_histogram_is_zero() -> None:
    """A degenerate (zero-bin) histogram must map to a 0.0 duty cycle."""
    assert duty_cycle((), num_days=0) == 0.0


def test_build_schedule_terminates_via_attempt_guard() -> None:
    """A pathological (very high) base rate must still terminate via the
    attempt cap rather than looping forever toward the week's end."""
    high = build_weekly_activity_schedule(base_rate_per_hour=3000.0, seed=1)
    assert high  # it terminated and returned events
    # The loop stopped on the attempt cap, before the observation week ended.
    assert high[-1].timestamp_s < 7 * 86400.0
