# Methodology

This section states the mathematics behind each of the seven capabilities.
Everything is standard, deterministic, and free of hidden randomness.

## 1. Rendezvous / intercept window solving

Both spacecraft are modelled as two-body circular orbits. The mean orbital
motion of a circular orbit of radius $a$ under gravitational parameter
$\mu$ is

$$ n = \sqrt{\frac{\mu}{a^3}} $$

and the position and velocity in the Earth-centred inertial (ECI) frame follow
from the classical orbital elements $(a, e=0, i, \Omega, \nu)$ via the standard
perifocal → ECI 3-1-3 rotation. The true anomaly advances linearly,
$\nu(t) = u_0 + n t$, so a candidate orbit is fully described by its altitude,
inclination, RAAN, and initial argument of latitude $u_0$.

Given the chaser state $(\mathbf{r}_c, \mathbf{v}_c)$ and the target position
$\mathbf{r}_t$, the line-of-sight vector is
$\boldsymbol{\rho} = \mathbf{r}_t - \mathbf{r}_c$ with slant range
$\rho = \lVert \mathbf{r}_t - \mathbf{r}_c \rVert$ and target elevation
$\varepsilon$ above the chaser's local horizontal plane. A **rendezvous
window** is a contiguous interval on which $\rho \le \rho_\text{max}$ and
$\varepsilon \ge \varepsilon_\text{min}$. The intercept burn is a coplanar
Hohmann transfer with the two-impulse budget
$\Delta v$ and transfer time equal to half the transfer-orbit period.

## 2. Orbital capture and phasing

Capturing the capsule is a *phasing* problem [@bate1971; @vallado2013;
@fehse2003]. The
chaser (the capture platform on the target's orbit) must wait until the target
leads it by exactly the angle

$$ \lambda = (\pi - n_t T_t) \bmod 2\pi, $$

where $T_t$ is the Hohmann transfer time and $n_t$ the target mean motion — the
transfer sweeps $\pi$ rad, so the target must start ahead by
$\pi - n_t T_t$. The relative phase evolves as
$\phi(t) = \phi_0 + (n_t - n_c)t$, so the **phasing wait time** is the first
non-negative solution of $\phi(t) \equiv \lambda \pmod{2\pi}$.

A **capture window** is a contiguous interval where the capsule is inside the
grapple envelope (range constraint) *and* slow enough that the platform can
match its velocity; the **velocity-matching burn** is exactly the relative
speed $\lVert \mathbf{v}_t - \mathbf{v}_c\rVert$ at that epoch, nulling the
relative velocity for a physical grapple.

## 3. Concealed-lair detection via thermal + terrain anomaly

A concealed lair is found by scoring each channel against a locally modelled
background — the standard formulation of statistical anomaly detection, where
"anomalous" means *improbable under the fitted background model* rather than
merely bright [@reed1990; @chandola2009]. A Gaussian low-pass
$\tilde{g} = K_\sigma \ast g$ approximates the
smooth natural signal, and each pixel is expressed as a standardized residual
$z_{ij} = (g_{ij} - \tilde{g}_{ij})/\sigma_{\text{res}}$. The **thermal
anomaly** is the one-tailed $z$ (we look for excess heat); the **terrain
anomaly** is the magnitude $|z|$ (a lair may be a raised shelf *or* an
excavated depression). The two maps are fused with weights
$w_T, w_D$ as $s_{ij} = (w_T z^T_{ij} + w_D z^D_{ij})/(w_T + w_D)$.
Connected components of the thresholded fused map are labelled and reported as
candidate regions, ranked by peak fused score.

## 4. Hidden-base discovery by Bayesian cue fusion

To decide *where* the base is before a strike, the mission treats each of the
$N$ candidate cells as a hypothesis and applies Bayesian belief updating
[@pearl1988].

*What counts as ground truth here.* The evaluated truth is the lair the scene
generator injects — its centre cell and its carved footprint — determined by
the cone centre and a fixed offset before any anomaly map exists. It is not the
argmax of the fused anomaly map, and the passive-RF cue is generated at the
injected site rather than at the detector's answer. Nothing the posterior
consumes is derived from the quantity the posterior is asked to recover, so the
reported ranks are measurements and not identities.

Cell $c$ carries a prior $P(c) \propto 1 + \beta\max(0,z^D_c)$
(terrain anomalies raise the prior). Each sensor cue $z$ is modelled as a
Gaussian measurement with likelihood ratio

$$ \text{LR}(z) = \exp\!\left(\frac{\mu z}{\sigma^2}\right), $$

so a neutral cell maps to 1, a hot cell to $>1$, a cold cell to $<1$. The
posterior is the normalized product

$$ P(c \mid \text{cues}) \propto P(c)\prod_i \text{LR}_i(c). $$

Searching greedily by descending posterior gives a deterministic **search
order** — the optimal policy for a uniform-cost, perfect-detection search
[@stone1975]. Two distinct effort statistics are reported and must not be
conflated: the **realised effort** is the rank of the known true site (an
after-the-fact validation number), while the **posterior expected effort**
$E[K] = \sum_{k} k\,P(c_k)$ is a property of the posterior alone and is the
number a planner can quote before the base is confirmed. The **discovery
curve** $\sum_{k} P(c_k)$ is the probability the base is found within the first
$k$ searches. Combining heterogeneous sensors this way is the standard
multisensor-fusion construction [@waltz1990].

## 5. Infiltration planning

The agent must reach the lair core while minimizing detection risk. Each cell
carries a movement cost

$$ \text{cost} = 1 + w_s\,\hat{s} + w_T\,z^T_+ + w_G\,\hat{g}, $$

combining normalized slope $\hat{s}$, positive thermal-exposure $z^T_+$,
guard line-of-sight exposure $\hat{g}$ (an elevation-occluded visibility count
from every watch post), and an impassable-lava mask. A deterministic 4-connected
**A*** search [@hart1968; @cormen2009] with an admissible Manhattan heuristic
returns the optimal route — admissibility holds because every step costs at
least $1$ and the heuristic counts steps, so A* is guaranteed optimal.

The baseline is a greedy depth-first walk over the *same* search space: it
always steps to the cheapest-looking unvisited neighbour and retraces one cell
when it dead-ends, paying that cell's cost again. Two conditions are needed for
the reported reduction to be non-negative by optimality rather than by a
favourable comparator, and both are enforced in code. The baseline must live in
the same 4-connected space over the same cost field — it does — *and* it must
actually reach the goal, because A* minimises over goal-reaching walks only. A
baseline that abandoned the search at a dead end would report the cost of a
shorter journey, which can be below the optimal cost of the full journey and
would make the reduction negative; the implementation therefore backtracks and
raises when the goal is unreachable instead of returning a truncated route.
`tests/test_infiltration_planning.py` pins a concrete grid on which the
non-backtracking version returns a truncated walk cheaper than the optimum.

## 6. Emitter localization by TDOA

Passive sensors at positions $\mathbf{s}_i$ time the arrival of the base's RF
burst. The range differences against a reference sensor,
$d_i = \lVert e-\mathbf{s}_i\rVert - \lVert e-\mathbf{s}_0\rVert$, define
hyperbolae whose intersection is the emitter $e$ [@skolnik2001; @chan1994]. The
estimate $\hat{e}$ minimizes the residuals via the Taylor-series (Gauss–Newton)
iteration on the normal equations [@foy1976], which converges to the true
emitter for exact measurements. Receivers report *time* differences; these are
converted to the range differences the geometry is solved in by multiplying by
the propagation speed, so the speed of light never enters the estimator itself.

Exact measurements make the solve a round-trip identity of the forward model:
it returns the injected point to machine precision by construction, which
checks solver–model consistency but measures no accuracy. The reported figure
therefore comes from receiver timings perturbed by a fixed-seed Gaussian jitter
of $\sigma_t$ before the conversion to ranges, so the error reflects a
geometry-dependent dilution of precision and can degrade.

## 7. Pattern-of-life analysis

A base's activity is modelled as an inhomogeneous Poisson point process
[@daley2003] whose instantaneous rate follows a diurnal envelope; events are
drawn by rejection sampling against that envelope, so the injected rhythm is
exactly known and the analysis can be checked against it. The observed events
are binned into a
$7\times 24$ hourly histogram, giving a mean daily profile
$\bar{p}_h = \tfrac{1}{7}\sum_d h_{d,h}$. The dominant operational periodicity
comes from the normalized autocorrelation, contiguous hours above a percentile
are **peak operating windows**, and tempo is classified from the mean event
rate.
