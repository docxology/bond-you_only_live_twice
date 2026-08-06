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


def _discovery_scene(offset: tuple[float, float] | None = None) -> dict:
    """Build a discovery scene whose truth comes from the scene generator.

    The ``true_cell`` is the *injected* lair centre — fixed by the cone centre
    plus ``lair_offset_cells`` before any anomaly map exists — never the argmax
    of the maps the posterior consumes. The returned dict carries the volcano
    scene alongside, so tests can reference the injected footprint.
    """
    from you_only_live_twice.terrain_anomaly import (
        terrain_anomaly_mask,
        thermal_anomaly_mask,
    )

    volcano = build_volcano_scene(seed=1967, lair_offset_cells=offset)
    _t, thermal_z = thermal_anomaly_mask(volcano["thermal"])
    _d, terrain_z = terrain_anomaly_mask(volcano["elevation"])
    true_cell = (int(volcano["lair_center"][0]), int(volcano["lair_center"][1]))
    scene = build_discovery_scene(
        volcano, thermal_z, terrain_z, seed=1967, true_cell=true_cell
    )
    scene["volcano"] = volcano
    return scene


@pytest.fixture(scope="module")
def _scene() -> dict:
    return _discovery_scene()


def _footprint_rank(posterior, footprint) -> int:
    for rank, cell in enumerate(rank_search_order(posterior), start=1):
        if cell in footprint:
            return rank
    raise AssertionError("footprint never appears in the search order")


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


def test_canonical_scene_isolates_the_injected_footprint(_scene: dict) -> None:
    """What is actually established: footprint-level recovery, not centroid.

    The truth here is the injected lair, not the argmax of the maps the
    posterior is built from, so this is a measurement. It is also a hard
    target: the footprint is 80 of 4096 cells (~2 %).
    """
    post = _scene["posterior"]
    footprint = _scene["volcano"]["lair_footprint"]
    assert 0 < len(footprint) < post.size / 10

    assert rank_search_order(post)[0] in footprint
    assert _footprint_rank(post, footprint) == 1
    # The manuscript reports this mass to 6 dp and says the remainder falls
    # below the reported precision; pin exactly that, not a vaguer bound.
    assert sum(float(post[c]) for c in footprint) > 1.0 - 5e-7
    curve = discovery_probability_curve(post, max_cells=10)
    assert float(curve[9]) >= 0.99


def test_injected_centre_cell_is_not_recovered(_scene: dict) -> None:
    """The stricter centroid claim fails, and is pinned so it cannot be re-made.

    Both the anomaly maps and the posterior peak on the carved rim, not the
    centroid. Recording it here keeps the manuscript's weaker (true) claim
    honest: any change that made the centroid rank 1 would have to update this
    test deliberately.
    """
    post = _scene["posterior"]
    true = _scene["true_cell"]
    assert rank_search_order(post)[0] != true
    assert expected_discovery_effort(post, true) > 1.0
    assert float(post[true]) < 1e-6


@pytest.mark.parametrize("offset", [(-10.0, -10.0), (12.0, -6.0)])
def test_posterior_follows_a_moved_injected_lair(
    offset: tuple[float, float],
) -> None:
    """Positive control for the discovery chain: move the truth, it must follow.

    A posterior whose "true cell" was defined as its own argmax would pass any
    single-scene check; it cannot pass this one.
    """
    scene = _discovery_scene(offset)
    footprint = scene["volcano"]["lair_footprint"]
    post = scene["posterior"]
    assert rank_search_order(post)[0] in footprint
    assert sum(float(post[c]) for c in footprint) > 0.9
    assert not (footprint & build_volcano_scene(seed=1967)["lair_footprint"])


def test_single_cue_ranks_show_fusion_was_not_necessary(_scene: dict) -> None:
    """Each cue alone already ranks the footprint first — so say that, not 'weak cues'.

    If this ever fails because a cue stops being individually decisive, the
    manuscript's "fusion was not what found the base" wording must change too.
    """
    footprint = _scene["volcano"]["lair_footprint"]
    priors = _scene["priors"]
    for name in ("thermal", "terrain", "rf"):
        single = fuse_posteriors(priors, _scene[f"lr_{name}"])
        assert _footprint_rank(single, footprint) == 1, name
    assert _footprint_rank(priors / float(priors.sum()), footprint) == 1


def test_scenario_discovery_truth_is_not_derived_from_the_cue_maps() -> None:
    """The scenario's truth is the injected lair; the detector's answer differs.

    This is the anti-circularity gate. It fails the moment ``build_scenario``
    goes back to defining the true site as the argmax of the fused Z-maps,
    because then truth and estimate would coincide.
    """
    scenario = build_scenario()
    post = scenario["discovery"]["posterior"]
    assert float(post.sum()) == pytest.approx(1.0)

    truth = scenario["lair_site"]
    assert truth == tuple(scenario["volcano"]["lair_center"])
    assert scenario["discovery"]["true_cell"] == truth
    # The detector's estimate is tracked separately and is a different cell.
    assert scenario["detected_site"] != truth
    assert scenario["detected_site"] in scenario["lair_footprint"]
    # Every downstream "truth" is the injected site, not the estimate.
    assert scenario["infiltration"]["goal"] == truth
    assert scenario["emitter"]["emitter_m"] == (
        float(truth[0]) * 1000.0,
        float(truth[1]) * 1000.0,
    )


def test_build_discovery_scene_defaults_true_cell_to_the_lair_centre() -> None:
    """``build_discovery_scene``'s documented default: omit ``true_cell`` and it
    falls back to the volcano scene's injected lair centre."""
    from you_only_live_twice.terrain_anomaly import (
        terrain_anomaly_mask,
        thermal_anomaly_mask,
    )

    volcano = build_volcano_scene(seed=1967)
    _t, thz = thermal_anomaly_mask(volcano["thermal"])
    _d, tez = terrain_anomaly_mask(volcano["elevation"])
    scene = build_discovery_scene(volcano, thz, tez, seed=1967)  # true_cell omitted
    assert scene["true_cell"] == tuple(volcano["lair_center"])


def test_build_discovery_scene_rejects_shape_mismatch() -> None:
    volcano = build_volcano_scene(seed=1967)
    with pytest.raises(ValueError):
        build_discovery_scene(volcano, np.zeros((4, 4)), np.zeros((8, 8)), seed=1967)


def test_terrain_weighted_priors_reject_non_finite_weights() -> None:
    """A prior whose weights do not sum finite must raise, not silently NaN."""
    with pytest.raises(ValueError):
        terrain_weighted_priors(np.full((4, 4), np.inf), beta=1.0)


def test_fuse_posteriors_reject_non_finite_scores() -> None:
    """A cue map carrying non-finite mass must raise, not propagate the NaN."""
    priors = np.full((4, 4), 1.0 / 16.0)
    lr = np.ones((4, 4))
    lr[0, 0] = np.inf
    with pytest.raises(ValueError):
        fuse_posteriors(priors, lr)


def test_discovery_probability_curve_without_max_cells() -> None:
    """The default (``max_cells is None``) branch returns the full curve."""
    post = np.zeros((4, 4))
    post[0, 0] = 0.7
    post[1, 1] = 0.3
    curve = discovery_probability_curve(post)
    assert curve[-1] == pytest.approx(1.0, abs=1e-9)
    assert np.all(np.diff(curve) >= 0.0)


def test_terrain_weighted_prior_alone_ranks_the_footprint_first(_scene: dict) -> None:
    """V1 gate: the terrain-weighted prior carries information on its own.

    The prior (no likelihood-ratio cues) already locates the injected lair
    footprint first. This is a prior-specific assertion: if the prior were
    corrupted (e.g. made uniform, or misregistered away from the terrain
    anomaly), this rank would collapse from 1 to ~the field average, so the
    gate fails long before the cue-dominated posterior would. It binds the
    terrain-weighted prior itself to the find.
    """
    priors = _scene["priors"] / float(_scene["priors"].sum())
    footprint = _scene["volcano"]["lair_footprint"]
    assert _footprint_rank(priors, footprint) == 1
    # And it is not a silent uniform "prior": the scene must actually weight
    # terrain anomalies, otherwise there is nothing to gate.
    assert float(priors.max()) > 1.0 / float(priors.size)
    # The prior's own argmax lies inside the injected footprint.
    assert rank_search_order(priors)[0] in footprint


def test_footprint_posterior_mass_can_fall_under_cue_misregistration(
    _scene: dict,
) -> None:
    """V2 negative control: the reported 1.0 footprint mass is measured, not an artefact.

    Misregistering every likelihood-ratio cue map relative to the carved
    footprint must collapse the footprint's posterior mass. This is what proves
    ``DISCOVERY_FOOTPRINT_POSTERIOR == 1.0`` is a real concentration that
    depends on the cues actually pointing at the lair, rather than a value that
    cannot move.
    """
    footprint = _scene["volcano"]["lair_footprint"]
    post = _scene["posterior"]
    nominal = sum(float(post[c]) for c in footprint)
    assert nominal > 0.999  # the reported concentration

    off = 10
    degraded = fuse_posteriors(
        _scene["priors"],
        np.roll(_scene["lr_thermal"], off, axis=0),
        np.roll(_scene["lr_terrain"], off, axis=0),
        np.roll(_scene["lr_rf"], off, axis=0),
    )
    degraded_mass = sum(float(degraded[c]) for c in footprint)
    assert degraded_mass < 1e-10


def test_footprint_rank_raises_for_out_of_grid_footprint() -> None:
    """The injected-footprint invariant trips on a footprint disjoint from the grid.

    ``_footprint_rank`` enumerates the whole search grid; a footprint whose
    cells are all outside the grid can never be reached, so the documented
    invariant raises rather than returning a bogus rank.
    """
    from you_only_live_twice.scenario import _footprint_rank

    scenario = build_scenario()
    posterior = scenario["discovery"]["posterior"]
    with pytest.raises(AssertionError):
        _footprint_rank(posterior, frozenset({(999, 999)}))
