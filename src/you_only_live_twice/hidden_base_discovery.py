"""Hidden-base discovery: Bayesian cue fusion over candidate sites.

Given a field of candidate hide sites (the volcano grid), the mission must
decide *where* the concealed base is before committing a strike. This module
implements the classic Bayesian search formulation (Pearl's belief-updating
framework applied to a spatial hypothesis set):

* each cell carries a prior probability that the base is hidden there;
* sensors deliver per-cell *cue maps* (thermal anomaly, terrain anomaly, RF
  emission), each modelled as a standardized measurement whose likelihood
  ratio is Gaussian;
* :func:`fuse_posteriors` combines priors and likelihood ratios into the
  posterior probability map :math:`P(\\text{base at } c \\mid \\text{cues})`;
* :func:`rank_search_order` turns the posterior into a deterministic search
  plan (greedy: search the most probable site first);
* :func:`discovery_probability_curve` / :func:`expected_discovery_effort`
  quantify how quickly the search would find the base.

Everything is deterministic — the cue maps come from fixed-seed scene data and
fixed sensor models — and the module is infrastructure-free.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

__all__ = [
    "build_discovery_scene",
    "discovery_probability_curve",
    "expected_discovery_effort",
    "fuse_posteriors",
    "gaussian_likelihood_ratio",
    "rank_search_order",
    "terrain_weighted_priors",
]


def terrain_weighted_priors(terrain_z: np.ndarray, beta: float = 1.0) -> np.ndarray:
    """Prior probability per cell, weighted toward terrain anomalies.

    A hidden base is more likely where the terrain deviates from the natural
    cone, so the prior is proportional to ``1 + beta * max(0, terrain_z)`` and
    normalized to sum to one.
    """
    if terrain_z.ndim != 2:
        raise ValueError("terrain_z must be 2-D")
    if beta < 0.0:
        raise ValueError("beta must be non-negative")
    weights = 1.0 + beta * np.maximum(0.0, terrain_z)
    total = float(weights.sum())
    if total <= 0.0 or not math.isfinite(total):
        raise ValueError("prior weights must sum to a positive finite value")
    return weights / total  # type: ignore[no-any-return]


def gaussian_likelihood_ratio(
    z_map: np.ndarray, mu_hot: float, sigma: float = 1.0
) -> np.ndarray:
    """Per-cell likelihood ratio of a Gaussian sensor measurement.

    Under the model ``z | base ~ N(mu_hot, sigma)`` vs ``z | no base ~ N(0,
    sigma)`` the likelihood ratio, normalised so a neutral cell maps to 1, is

    .. math:: LR(z) = \\exp\\left(\\frac{\\mu z}{\\sigma^2}\\right).

    A cell whose cue sits at the expected base signature (``z = mu_hot``) gets
    ``LR = exp(mu^2/sigma^2) > 1``; a neutral cell (``z = 0``) gets ``LR = 1``;
    a cell below the noise floor (``z < 0``) gets ``LR < 1``.
    """
    if z_map.ndim != 2:
        raise ValueError("z_map must be 2-D")
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    exponent = (mu_hot * z_map) / (sigma * sigma)
    return np.exp(exponent)


def fuse_posteriors(priors: np.ndarray, *likelihood_ratios: np.ndarray) -> np.ndarray:
    """Combine priors and likelihood-ratio cue maps into posterior probabilities.

    The posterior over the hypothesis set ``{base at cell c}`` is

    .. math:: P(c \\mid \\text{cues}) \\propto P(c) \\prod_i LR_i(c),

    normalized so the map sums to one. Requires at least one likelihood-ratio
    map with the same shape as the priors.
    """
    if priors.ndim != 2:
        raise ValueError("priors must be 2-D")
    if not likelihood_ratios:
        raise ValueError("at least one likelihood-ratio map is required")
    score = priors.astype(float).copy()
    for lr in likelihood_ratios:
        if lr.shape != priors.shape:
            raise ValueError("all cue maps must match the prior shape")
        score = score * lr
    total = float(score.sum())
    if total <= 0.0 or not math.isfinite(total):
        raise ValueError("posterior scores must sum to a positive finite value")
    return score / total


def rank_search_order(posterior: np.ndarray) -> tuple[tuple[int, int], ...]:
    """Cells sorted by descending posterior probability (row, col).

    Deterministic: ties are broken by row, then column, so the order is
    reproducible for a given posterior map.
    """
    if posterior.ndim != 2:
        raise ValueError("posterior must be 2-D")
    rows, cols = np.indices(posterior.shape)
    flat = np.lexsort((cols.ravel(), rows.ravel(), -posterior.ravel()))
    order: list[tuple[int, int]] = []
    for index in flat:
        r = int(rows.ravel()[index])
        c = int(cols.ravel()[index])
        order.append((r, c))
    return tuple(order)


def discovery_probability_curve(
    posterior: np.ndarray, max_cells: int | None = None
) -> np.ndarray:
    """Cumulative probability the base is found within the first k searched cells.

    Searching in posterior order, the probability of having found the base
    after ``k`` cells is the sum of the top-``k`` posteriors.
    """
    if posterior.ndim != 2:
        raise ValueError("posterior must be 2-D")
    sorted_values = np.sort(posterior.ravel())[::-1]
    if max_cells is not None:
        sorted_values = sorted_values[:max_cells]
    return np.cumsum(sorted_values)


def expected_discovery_effort(
    posterior: np.ndarray, true_cell: tuple[int, int]
) -> float:
    """Number of cells the greedy search inspects before finding the base.

    Returns the 1-based rank of ``true_cell`` in :func:`rank_search_order`, or
    ``inf`` if the cell has zero posterior (it would never be searched).
    """
    if posterior.ndim != 2:
        raise ValueError("posterior must be 2-D")
    if float(posterior[true_cell]) <= 0.0:
        # A site the sensors assign no probability to is never searched first
        # in the greedy plan, so the expected effort is unbounded.
        return float("inf")
    order = rank_search_order(posterior)
    for rank, cell in enumerate(order, start=1):
        if cell == true_cell:
            return float(rank)
    return float("inf")


def _rf_power_map(
    size: int,
    emitter: tuple[int, int],
    decay_cells: float,
    power: float,
    noise: float,
    seed: int,
) -> np.ndarray:
    """Deterministic RF emission map: power falls with distance from emitter."""
    rng = np.random.default_rng(seed)
    ys, xs = np.mgrid[0:size, 0:size].astype(float)
    dist = np.sqrt((ys - emitter[0]) ** 2 + (xs - emitter[1]) ** 2)
    signal = power / (1.0 + (dist / decay_cells) ** 2)
    return signal + rng.normal(0.0, noise, (size, size))  # type: ignore[no-any-return]


def build_discovery_scene(
    volcano: dict[str, Any],
    thermal_z: np.ndarray,
    terrain_z: np.ndarray,
    seed: int = 1967,
    mu_hot: float = 2.5,
    beta: float = 1.5,
    rf_power: float = 8.0,
    rf_decay_cells: float = 6.0,
    rf_noise: float = 0.35,
    true_cell: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Assemble the deterministic hidden-base discovery scene.

    Consumes the volcano scene and the anomaly Z-maps, adds a fixed-seed RF
    emission map, and returns the priors, the three cue likelihood-ratio maps,
    and the posterior. ``true_cell`` is the ground-truth base site (defaults to
    the volcano scene's recorded lair centre — pass the *detected* centroid for
    self-consistency with the anomaly signatures).

    Returns a dict with ``priors``, ``lr_thermal``, ``lr_terrain``, ``lr_rf``,
    ``posterior``, ``true_cell`` (the injected lair centre) and ``parameters``.
    """
    if thermal_z.shape != terrain_z.shape:
        raise ValueError("thermal_z and terrain_z must share the same shape")
    size = thermal_z.shape[0]
    if true_cell is None:
        true_cell = (int(volcano["lair_center"][0]), int(volcano["lair_center"][1]))

    priors = terrain_weighted_priors(terrain_z, beta=beta)
    rf = _rf_power_map(
        size,
        emitter=true_cell,
        decay_cells=rf_decay_cells,
        power=rf_power,
        noise=rf_noise,
        seed=seed,
    )
    rf_z = (rf - float(rf.mean())) / float(rf.std())

    lr_thermal = gaussian_likelihood_ratio(thermal_z, mu_hot=mu_hot)
    lr_terrain = gaussian_likelihood_ratio(terrain_z, mu_hot=mu_hot)
    lr_rf = gaussian_likelihood_ratio(rf_z, mu_hot=mu_hot)
    posterior = fuse_posteriors(priors, lr_thermal, lr_terrain, lr_rf)

    return {
        "priors": priors,
        "lr_thermal": lr_thermal,
        "lr_terrain": lr_terrain,
        "lr_rf": lr_rf,
        "posterior": posterior,
        "true_cell": true_cell,
        "parameters": {
            "mu_hot": mu_hot,
            "beta": beta,
            "rf_power": rf_power,
            "rf_decay_cells": rf_decay_cells,
            "seed": seed,
        },
    }
