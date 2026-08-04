"""Concealed-lair detection via thermal / terrain anomaly scoring.

The volcano-camouflage case: a hidden base is camouflaged inside / atop a
volcanic cone, but it leaks a *thermal* signature (machinery heat, ventilation)
and leaves a *terrain* footprint (a man-made flat shelf or opening where a
natural cone would be smooth). This module detects it by scoring both channels
against a locally modelled background and fusing the scores.

Pipeline (all deterministic, numpy only):

* :func:`build_volcano_scene` maps a synthetic cone + concealed lair to two
  grids: terrain elevation and thermal radiance.
* Smooth background models are fit per channel (Gaussian low-pass); each pixel
  is scored as the standardized residual (Z-score) of measurement vs model.
* Thermal and terrain Z-scores are fused with weights into one anomaly map.
* :func:`detect_concealed_lair` thresholds the fused map, labels connected
  components, and reports ranked candidate lair regions.

Everything is a real computation over real (synthetic-but-methodical) data with
fixed seeds — no mocks, no external calls.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = [
    "LairRegion",
    "build_volcano_scene",
    "detect_concealed_lair",
    "fuse_anomaly_scores",
    "gaussian_kernel",
    "smooth2d",
    "standardized_residual",
    "terrain_anomaly_mask",
    "thermal_anomaly_mask",
]

#: m per grid cell (default 64x64 grid over a ~64 km scene).
M_PER_CELL = 1_000.0


@dataclass(frozen=True)
class LairRegion:
    """A detected candidate concealed-lair region.

    ``row0/col0``/``row1/col1`` bound the region (row-major, upper-left
    inclusive-style box) and the three scores summarise how anomalous it is.
    """

    row0: int
    col0: int
    row1: int
    col1: int
    thermal_score: float  #: peak standardized thermal residual in the region.
    terrain_score: float  #: peak standardized terrain residual in the region.
    fused_score: float  #: peak weighted-fused anomaly score in the region.

    @property
    def area_cells(self) -> int:
        """Number of grid cells in the bounding box."""
        return max(0, (self.row1 - self.row0)) * max(0, (self.col1 - self.col0))

    def contains(self, row: int, col: int) -> bool:
        """True when the grid cell ``(row, col)`` lies inside the box."""
        return self.row0 <= row < self.row1 and self.col0 <= col < self.col1


def gaussian_kernel(sigma: float, size: int | None = None) -> np.ndarray:
    """A 2-D Gaussian kernel of standard deviation ``sigma`` (rows=cols)."""
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    radius = math.ceil(3 * sigma)
    size = int(size) if size is not None else 2 * radius + 1
    if size % 2 == 0:
        size += 1
    ax = np.linspace(-(size // 2), size // 2, size)
    g = np.exp(-0.5 * (ax / sigma) ** 2)
    kernel2d = np.outer(g, g)
    return kernel2d / kernel2d.sum()  # type: ignore[no-any-return]


def smooth2d(grid: np.ndarray, sigma: float) -> np.ndarray:
    """Low-pass filter ``grid`` with a Gaussian of standard deviation ``sigma``.

    The array is padded with a reflected edge before convolution to reduce
    boundary drop-off.
    """
    if grid.ndim != 2:
        raise ValueError("grid must be 2-D")
    kernel = gaussian_kernel(sigma)
    r = kernel.shape[0] // 2
    padded = np.pad(grid.astype(float), r, mode="reflect")
    out = np.zeros_like(padded, dtype=float)
    # Direct convolution (grids are small; deterministic and dependency-free).
    for i in range(r, padded.shape[0] - r):
        for j in range(r, padded.shape[1] - r):
            patch = padded[i - r : i + r + 1, j - r : j + r + 1]
            out[i, j] = float(np.sum(patch * kernel))
    return out[r : grid.shape[0] + r, r : grid.shape[1] + r]


def standardized_residual(measured: np.ndarray, model: np.ndarray) -> np.ndarray:
    """Z-score of ``measured - model`` over the whole map.

    The residual is divided by its robust standard deviation (the standard
    deviation of the finite residuals), giving a map of how many sigma each
    pixel stands above the local background model.
    """
    residual = measured.astype(float) - model.astype(float)
    std = float(np.std(residual))
    if std <= 0.0 or not math.isfinite(std):
        return np.zeros_like(residual, dtype=float)
    return residual / std  # type: ignore[no-any-return]


def _threshold_mask(zmap: np.ndarray, z_threshold: float) -> np.ndarray:
    return zmap >= z_threshold


def thermal_anomaly_mask(
    thermal: np.ndarray, sigma: float = 2.0, z_threshold: float = 2.0
) -> tuple[np.ndarray, np.ndarray]:
    """Thermal anomaly map: standardized residual above the smoothed background.

    Returns ``(mask, zmap)`` where ``mask`` is boolean pixels whose thermal
    signature exceeds ``z_threshold`` standard deviations over the local
    background.
    """
    model = smooth2d(thermal, sigma)
    zmap = standardized_residual(thermal, model)
    return _threshold_mask(zmap, z_threshold), zmap


def terrain_anomaly_mask(
    elevation: np.ndarray, sigma: float = 3.0, z_threshold: float = 1.5
) -> tuple[np.ndarray, np.ndarray]:
    """Terrain anomaly map: magnitude of deviation from the natural cone profile.

    The natural volcanic cone is smooth and largely survives low-pass
    smoothing, whereas a man-made shelf — whether raised or carved down into a
    depression — stands out as a large *magnitude* standardized residual
    against that smooth model. The absolute deviation is used so both a built-up
    bump and an excavated lair produce a positive anomaly.
    """
    model = smooth2d(elevation, sigma)
    zmap = np.abs(standardized_residual(elevation, model))
    return _threshold_mask(zmap, z_threshold), zmap


def fuse_anomaly_scores(
    thermal_z: np.ndarray,
    terrain_z: np.ndarray,
    thermal_weight: float = 0.5,
    terrain_weight: float = 0.5,
) -> np.ndarray:
    """Weighted sum of the two standardized anomaly maps."""
    if thermal_weight < 0.0 or terrain_weight < 0.0:
        raise ValueError("weights must be non-negative")
    total = thermal_weight + terrain_weight
    if total <= 0.0:
        raise ValueError("at least one weight must be positive")
    return (thermal_weight * thermal_z + terrain_weight * terrain_z) / total


def _label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """Connected-component labeling (4-connectivity) via flood fill."""
    labels = np.zeros(mask.shape, dtype=int)
    next_label = 0
    for i in range(mask.shape[0]):
        for j in range(mask.shape[1]):
            if mask[i, j] and labels[i, j] == 0:
                next_label += 1
                _flood_fill(mask, labels, i, j, next_label)
    return labels, next_label


def _flood_fill(
    mask: np.ndarray, labels: np.ndarray, i0: int, j0: int, label: int
) -> None:
    stack: list[tuple[int, int]] = [(i0, j0)]
    labels[i0, j0] = label
    while stack:
        i, j = stack.pop()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ni, nj = i + di, j + dj
            if (
                0 <= ni < mask.shape[0]
                and 0 <= nj < mask.shape[1]
                and mask[ni, nj]
                and labels[ni, nj] == 0
            ):
                labels[ni, nj] = label
                stack.append((ni, nj))


def _min_cell_size(thermal: np.ndarray, elevation: np.ndarray) -> int:
    size = int(
        min(thermal.shape[0], thermal.shape[1], elevation.shape[0], elevation.shape[1])
    )
    return max(1, size // 32)


def detect_concealed_lair(
    thermal: np.ndarray,
    elevation: np.ndarray,
    thermal_weight: float = 0.5,
    terrain_weight: float = 0.5,
    z_threshold: float = 1.5,
    min_cells: int | None = None,
) -> tuple[tuple[LairRegion, ...], dict[str, Any]]:
    """Rank candidate concealed-lair regions from thermal + terrain grids.

    Returns ``(regions, meta)`` where ``regions`` is the tuple of candidate
    :class:`LairRegion` sorted by descending fused score, and ``meta`` carries
    the fused score map and the Z-maps for downstream figure / reporting use.
    """
    thermal_mask, thermal_z = thermal_anomaly_mask(thermal)
    terrain_mask, terrain_z = terrain_anomaly_mask(elevation)
    fused = fuse_anomaly_scores(thermal_z, terrain_z, thermal_weight, terrain_weight)

    union = thermal_mask | terrain_mask
    labels, count = _label_components(union)
    min_cells = _min_cell_size(thermal, elevation) if min_cells is None else min_cells

    regions: list[LairRegion] = []
    for label in range(1, count + 1):
        rows, cols = np.nonzero(labels == label)
        if rows.size < min_cells:
            continue
        fused_here = fused[rows, cols]
        peak = int(np.argmax(fused_here))
        r0, r1 = int(rows.min()), int(rows.max()) + 1
        c0, c1 = int(cols.min()), int(cols.max()) + 1
        regions.append(
            LairRegion(
                row0=r0,
                col0=c0,
                row1=r1,
                col1=c1,
                thermal_score=float(thermal_z[rows[peak], cols[peak]]),
                terrain_score=float(terrain_z[rows[peak], cols[peak]]),
                fused_score=float(fused_here[peak]),
            )
        )
    regions.sort(key=lambda r: r.fused_score, reverse=True)
    meta: dict[str, Any] = {
        "fused_score": fused,
        "thermal_z": thermal_z,
        "terrain_z": terrain_z,
        "thermal_mask": thermal_mask,
        "terrain_mask": terrain_mask,
        "num_components": count,
    }
    return tuple(regions), meta


def build_volcano_scene(
    size: int = 64,
    cone_radius_cells: float = 20.0,
    cone_height_m: float = 2_000.0,
    lair_radius_cells: float = 5.0,
    lair_heat_kelvin: float = 25.0,
    thermal_noise_kelvin: float = 1.5,
    terrain_noise_m: float = 6.0,
    seed: int = 1967,
) -> dict[str, Any]:
    """Build a deterministic volcano-camouflage scene.

    A Gaussian volcanic cone sits in the middle of the grid. The concealed lair
    is a flat circular shelf cut into the cone's flank, and it emits a strong
    local thermal excess. Thermal background follows a lapse rate with altitude
    plus a fixed-seed noise floor.

    Returns a dict with ``elevation``, ``thermal`` (2-D grids), the ground-truth
    ``lair_center`` (row, col) and ``lair_radius_cells``, and ``parameters``.
    """
    if size <= 0:
        raise ValueError("size must be positive")
    rng = np.random.default_rng(seed)
    ys, xs = np.mgrid[0:size, 0:size].astype(float)
    cy = cx = (size - 1) / 2.0
    dist = np.sqrt((ys - cy) ** 2 + (xs - cx) ** 2)

    # Smooth cone elevation.
    elevation = cone_height_m * np.exp(-(dist**2) / (2.0 * cone_radius_cells**2))

    # Concealed lair: flatten a circular shelf on the flank (terrain anomaly)
    # by carving the cone down to a low plateau on the hot side.
    # Lair offset toward the lower-right so it sits clearly on one flank.
    lair_row = cy + cone_radius_cells * 0.5
    lair_col = cx + cone_radius_cells * 0.5
    lair_dist = np.sqrt((ys - lair_row) ** 2 + (xs - lair_col) ** 2)
    lair_mask = lair_dist <= lair_radius_cells
    # Carve: inside the lair, elevation drops to a low flat shelf.
    base_shelf = elevation[lair_mask].mean() - cone_height_m * 0.25
    carved = elevation.copy()
    carved[lair_mask] = base_shelf

    # Thermal background: lapse rate with altitude (smooth) + noise floor.
    thermal = (
        283.0 - 0.0065 * carved + rng.normal(0.0, thermal_noise_kelvin, (size, size))
    )
    # Lair mechanism heat: strong local excess over the carved shelf.
    carve_window_rows, carve_window_cols = np.nonzero(lair_mask)
    thermal[lair_mask] += lair_heat_kelvin

    terrain = carved + rng.normal(0.0, terrain_noise_m, (size, size))

    return {
        "elevation": terrain,
        "thermal": thermal,
        "lair_center": (round(lair_row), round(lair_col)),
        "lair_radius_cells": float(lair_radius_cells),
        "parameters": {
            "size": size,
            "cone_radius_cells": cone_radius_cells,
            "cone_height_m": cone_height_m,
            "lair_heat_kelvin": lair_heat_kelvin,
            "seed": seed,
        },
        "lair_raw_cells": (carve_window_rows.tolist(), carve_window_cols.tolist()),
    }
