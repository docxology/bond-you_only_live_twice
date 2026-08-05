"""Real-data tests for the hidden-base discovery (Bayesian cue fusion) module.

Verifies prior construction, Gaussian likelihood ratios, posterior fusion, the
deterministic search order, and the effort/curve metrics over a real discovery
scene built from the volcano imagery.
"""

from __future__ import annotations

import numpy as np
import pytest

from you_only_live_twice.hidden_base_discovery import (
    build_discovery_scene,
    discovery_probability_curve,
    expected_discovery_effort,
    fuse_posteriors,
    gaussian_likelihood_ratio,
    posterior_expected_effort,
    rank_search_order,
    terrain_weighted_priors,
)
from you_only_live_twice.scenario import build_scenario
from you_only_live_twice.terrain_anomaly import build_volcano_scene


@pytest.fixture(scope="module")
def _scene() -> dict:
    from you_only_live_twice.terrain_anomaly import (
        terrain_anomaly_mask,
        thermal_anomaly_mask,
    )

    volcano = build_volcano_scene(seed=1967)
    _t, thermal_z = thermal_anomaly_mask(volcano["thermal"])
    _d, terrain_z = terrain_anomaly_mask(volcano["elevation"])
    # The concealed base sits where its thermal + terrain signatures peak (the
    # same semantics the mission scenario uses), so the cue fusion is coherent.
    fused_peak = 0.5 * thermal_z + 0.5 * terrain_z
    size_grid = fused_peak.shape[0]
    flat_idx = int(np.argmax(fused_peak))
    true_cell = (flat_idx // size_grid, flat_idx % size_grid)
    return build_discovery_scene(
        volcano, thermal_z, terrain_z, seed=1967, true_cell=true_cell
    )


def test_terrain_weighted_priors_normalize() -> None:
    z = np.zeros((8, 8))
    priors = terrain_weighted_priors(z, beta=1.0)
    assert priors.shape == (8, 8)
    assert priors.sum() == pytest.approx(1.0)
    assert np.all(priors > 0.0)
    # Uniform terrain -> uniform priors.
    np.testing.assert_allclose(priors, 1.0 / 64.0)
    with pytest.raises(ValueError):
        terrain_weighted_priors(np.zeros(5))
    with pytest.raises(ValueError):
        terrain_weighted_priors(np.zeros((4, 4)), beta=-1.0)


def test_gaussian_likelihood_ratio_shape_and_extremes() -> None:
    z = np.zeros((4, 4))
    lr = gaussian_likelihood_ratio(z, mu_hot=2.0)
    assert lr.shape == (4, 4)
    # Neutral cell -> LR == 1.
    np.testing.assert_allclose(lr, 1.0)
    # Hot cell -> LR > 1; cold cell -> LR < 1.
    hot = gaussian_likelihood_ratio(np.array([[4.0]]), mu_hot=2.0)
    assert float(hot[0, 0]) > 1.0
    cold = gaussian_likelihood_ratio(np.array([[-4.0]]), mu_hot=2.0)
    assert float(cold[0, 0]) < 1.0
    with pytest.raises(ValueError):
        gaussian_likelihood_ratio(np.zeros(3), mu_hot=1.0)
    with pytest.raises(ValueError):
        gaussian_likelihood_ratio(np.zeros((3, 3)), mu_hot=1.0, sigma=0.0)


def test_fuse_posteriors_normalizes_and_validates() -> None:
    priors = np.full((4, 4), 1.0 / 16.0)
    lr = np.ones((4, 4))
    post = fuse_posteriors(priors, lr)
    assert post.sum() == pytest.approx(1.0)
    np.testing.assert_allclose(post, 1.0 / 16.0)
    # A hot cue concentrates mass on the strongest cell.
    lr_hot = np.ones((4, 4))
    lr_hot[2, 2] = 50.0
    post_hot = fuse_posteriors(priors, lr_hot)
    assert post_hot[2, 2] > 0.7
    assert post_hot[2, 2] > post_hot[0, 0]
    with pytest.raises(ValueError):
        fuse_posteriors(np.zeros(4))
    with pytest.raises(ValueError):
        fuse_posteriors(np.ones((4, 4)))
    with pytest.raises(ValueError):
        fuse_posteriors(priors, np.ones((3, 3)))


def test_rank_search_order_is_deterministic_and_sorted() -> None:
    post = np.zeros((5, 5))
    post[1, 2] = 0.5
    post[0, 0] = 0.3
    post[3, 3] = 0.2
    order = rank_search_order(post)
    assert order[0] == (1, 2)
    assert order[1] == (0, 0)
    assert len(order) == 25
    assert rank_search_order(post) == rank_search_order(post)
    with pytest.raises(ValueError):
        rank_search_order(np.zeros(4))
    # Ties broken deterministically by (row, col).
    tie = np.zeros((3, 3))
    tie[0, 2] = 1.0
    tie[2, 0] = 1.0
    order_tie = rank_search_order(tie)
    assert order_tie[0] == (0, 2)
    assert order_tie[1] == (2, 0)


def test_discovery_probability_curve() -> None:
    post = np.zeros((4, 4))
    post[0, 0] = 0.7
    post[1, 1] = 0.2
    post[2, 2] = 0.1
    curve = discovery_probability_curve(post, max_cells=16)
    assert curve[0] == pytest.approx(0.7)
    assert curve[-1] == pytest.approx(1.0, abs=1e-9)
    assert np.all(np.diff(curve) >= 0.0)  # cumulative and non-decreasing
    with pytest.raises(ValueError):
        discovery_probability_curve(np.zeros(4))


def test_expected_discovery_effort() -> None:
    post = np.zeros((4, 4))
    post[0, 0] = 0.8
    post[2, 3] = 0.2
    assert expected_discovery_effort(post, (0, 0)) == 1.0
    assert expected_discovery_effort(post, (2, 3)) == 2.0
    assert expected_discovery_effort(post, (1, 1)) == float("inf")
    with pytest.raises(ValueError):
        expected_discovery_effort(np.zeros(4), (0, 0))


def test_posterior_expected_effort_matches_closed_forms() -> None:
    """E[K] = sum_k k*P(c_k): check both analytic extremes and an asymmetric case."""
    # Point mass -> the search always stops on the first cell.
    point = np.zeros((4, 4))
    point[2, 1] = 1.0
    assert posterior_expected_effort(point) == pytest.approx(1.0)

    # Uniform over N cells -> (N + 1) / 2.
    n = 16
    uniform = np.full((4, 4), 1.0 / n)
    assert posterior_expected_effort(uniform) == pytest.approx((n + 1) / 2.0)

    # Asymmetric case computed by hand: ranks 1..4 carry 0.5/0.3/0.15/0.05
    # over a 2x2 grid -> 1(.5) + 2(.3) + 3(.15) + 4(.05) = 1.75.
    asym = np.array([[0.5, 0.3], [0.15, 0.05]])
    assert posterior_expected_effort(asym) == pytest.approx(1.75)

    with pytest.raises(ValueError):
        posterior_expected_effort(np.zeros(4))
    with pytest.raises(ValueError):
        posterior_expected_effort(np.zeros((3, 3)))


def test_posterior_expected_effort_is_bounded_by_the_realised_rank_regime(
    _scene: dict,
) -> None:
    """A concentrated posterior must beat the uniform-search expectation."""
    post = _scene["posterior"]
    n_cells = post.size
    expected = posterior_expected_effort(post)
    assert 1.0 <= expected < (n_cells + 1) / 2.0
    # This posterior is near a point mass, so it sits close to the floor.
    assert expected < 1.5


def test_canonical_scene_isolates_true_base(_scene: dict) -> None:
    post = _scene["posterior"]
    true = _scene["true_cell"]
    # The Bayesian fusion ranks the true base first with near-certainty.
    assert rank_search_order(post)[0] == true
    assert float(post[true]) > 0.9
    assert expected_discovery_effort(post, true) == 1.0
    curve = discovery_probability_curve(post, max_cells=10)
    assert float(curve[9]) >= 0.99


def test_scenario_discovery_consistent_with_mission() -> None:
    scenario = build_scenario()
    post = scenario["discovery"]["posterior"]
    assert float(post.sum()) == pytest.approx(1.0)
    assert scenario["discovery"]["true_cell"] in rank_search_order(post)[:3]
