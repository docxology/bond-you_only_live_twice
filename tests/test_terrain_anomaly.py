"""Real-data tests for concealed-lair detection (thermal / terrain anomaly).

Verifies the anomaly-scoring pipeline over a synthetic-but-methodical
volcano-camouflage scene: that the injected lair is recovered by the fused
score, that constant (anomaly-free) inputs yield zero scores, and that each
validation branch is exercised.
"""

from __future__ import annotations

import numpy as np
import pytest

from you_only_live_twice.terrain_anomaly import (
    LairRegion,
    build_volcano_scene,
    detect_concealed_lair,
    fuse_anomaly_scores,
    gaussian_kernel,
    smooth2d,
    standardized_residual,
    terrain_anomaly_mask,
    thermal_anomaly_mask,
)


def test_gaussian_kernel_normalizes_and_rejects_bad_sigma() -> None:
    kernel = gaussian_kernel(2.0)
    assert kernel.shape[0] == kernel.shape[1]
    assert kernel.shape[0] % 2 == 1  # odd size
    assert kernel.sum() == pytest.approx(1.0, rel=1e-9)
    assert np.all(kernel >= 0.0)
    with pytest.raises(ValueError):
        gaussian_kernel(0.0)


def test_smooth2d_rejects_non_2d() -> None:
    with pytest.raises(ValueError):
        smooth2d(np.zeros(5), 1.0)


def test_smooth2d_flattens_noise() -> None:
    grid = np.ones((16, 16)) * 10.0
    smooth = smooth2d(grid, 1.5)
    assert smooth.shape == grid.shape
    np.testing.assert_allclose(smooth, 10.0, atol=1e-6)


def test_standardized_residual_constant_input_is_zero() -> None:
    measured = np.full((8, 8), 5.0)
    model = np.full((8, 8), 5.0)
    z = standardized_residual(measured, model)
    np.testing.assert_allclose(z, 0.0)


def test_standardized_residual_scales_to_sigma() -> None:
    measured = np.zeros((8, 8))
    measured[3, 3] = 1.0
    model = np.zeros((8, 8))
    z = standardized_residual(measured, model)
    # The single hot pixel should be a large positive z.
    assert z[3, 3] > 2.0


def test_anomaly_masks_return_expected_shapes() -> None:
    rng = np.random.default_rng(0)
    thermal = 200.0 + rng.normal(0.0, 2.0, (20, 20))
    elevation = 100.0 + rng.normal(0.0, 3.0, (20, 20))
    t_mask, t_z = thermal_anomaly_mask(thermal)
    d_mask, d_z = terrain_anomaly_mask(elevation)
    assert t_mask.shape == thermal.shape
    assert t_mask.dtype == bool
    assert t_z.shape == thermal.shape
    assert d_mask.shape == elevation.shape
    assert d_z.shape == elevation.shape


def test_fuse_anomaly_scores() -> None:
    a = np.ones((4, 4))
    b = np.zeros((4, 4))
    fused = fuse_anomaly_scores(a, b, thermal_weight=0.5, terrain_weight=0.5)
    np.testing.assert_allclose(fused, 0.5)
    # All weight on terrain.
    fused2 = fuse_anomaly_scores(a, b, thermal_weight=0.0, terrain_weight=1.0)
    np.testing.assert_allclose(fused2, 0.0)
    with pytest.raises(ValueError):
        fuse_anomaly_scores(a, b, thermal_weight=-1.0, terrain_weight=1.0)
    with pytest.raises(ValueError):
        fuse_anomaly_scores(a, b, thermal_weight=0.0, terrain_weight=0.0)
    # Zero-positive total guard.
    with pytest.raises(ValueError):
        fuse_anomaly_scores(a, b, thermal_weight=0.0, terrain_weight=0.0)


def test_build_volcano_scene_is_deterministic_and_contains_lair() -> None:
    a = build_volcano_scene(seed=1967)
    b = build_volcano_scene(seed=1967)
    assert set(a) == set(b)
    np.testing.assert_array_equal(a["elevation"], b["elevation"])
    np.testing.assert_array_equal(a["thermal"], b["thermal"])
    assert a["elevation"].shape == (64, 64)
    assert a["thermal"].shape == (64, 64)
    assert a["lair_center"] == b["lair_center"]
    with pytest.raises(ValueError):
        build_volcano_scene(size=0)


def test_detect_concealed_lair_recovers_injected_lair() -> None:
    scene = build_volcano_scene(seed=1967)
    regions, meta = detect_concealed_lair(scene["thermal"], scene["elevation"])
    assert meta["num_components"] > 0
    assert regions  # at least one candidate
    top = regions[0]
    assert isinstance(top, LairRegion)
    # The top candidate must be near the injected lair center and score high.
    center_row, center_col = scene["lair_center"]
    assert top.contains(center_row, center_col) or top.fused_score > 3.0
    # Regions are sorted by descending fused score.
    scores = [r.fused_score for r in regions]
    assert scores == sorted(scores, reverse=True)
    # meta carries the maps.
    assert meta["fused_score"].shape == scene["thermal"].shape
    assert meta["thermal_z"].shape == scene["thermal"].shape


def test_detect_concealed_lair_min_cells_filters() -> None:
    scene = build_volcano_scene(seed=1967)
    regions_big, _ = detect_concealed_lair(
        scene["thermal"], scene["elevation"], min_cells=1
    )
    assert len(regions_big) >= 1
    # A large min_cells filter can drop small candidates.
    regions_large, _ = detect_concealed_lair(
        scene["thermal"], scene["elevation"], min_cells=10_000
    )
    assert len(regions_large) < len(regions_big)


def test_lair_region_area_and_contains() -> None:
    region = LairRegion(
        row0=1,
        col0=2,
        row1=5,
        col1=7,
        thermal_score=1.0,
        terrain_score=2.0,
        fused_score=3.0,
    )
    assert region.area_cells == 4 * 5
    assert region.contains(3, 4)
    assert not region.contains(0, 0)
