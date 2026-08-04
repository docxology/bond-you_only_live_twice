# Methodology

This section states the mathematics behind each of the three capabilities.
Everything is standard, deterministic, and free of hidden randomness.

## 1. Rendezvous / intercept window solving

Both spacecraft are modelled as two-body circular orbits. The mean orbital
motion of a circular orbit of radius $a$ under gravitational parameter
$\mu$ is

$$ n = \sqrt{\frac{\mu}{a^3}} $$

and the position and velocity in the Earth-centred inertial (ECI) frame follow
from the classical orbital elements $(a, e=0, i, \Omega, \nu)$ via the standard
perifocal → ECI 3-1-3 rotation. The true anomaly advances linearly,

$$ \nu(t) = u_0 + n\,t, $$

so a candidate orbit is fully described by its altitude (radius), inclination,
RAAN, and initial argument of latitude $u_0$.

Given the chaser state $(\mathbf{r}_c, \mathbf{v}_c)$ and the target position
$\mathbf{r}_t$, the line-of-sight vector is $\boldsymbol{\rho} = \mathbf{r}_t -
\mathbf{r}_c$ with slant range

$$ \rho = \lVert \mathbf{r}_t - \mathbf{r}_c \rVert $$

and the target elevation $\varepsilon$ above the chaser's local horizontal
plane (the plane perpendicular to the local radial direction
$\hat{\mathbf{r}}_c$) is

$$ \varepsilon = \operatorname{atan2}\!\left( \boldsymbol{\rho}\cdot\hat{\mathbf{r}}_c,\,
   \lVert \boldsymbol{\rho} - (\boldsymbol{\rho}\cdot\hat{\mathbf{r}}_c)\hat{\mathbf{r}}_c \rVert \right). $$

A **rendezvous window** is a contiguous time interval on which both
$\rho \le \rho_\text{max}$ and $\varepsilon \ge \varepsilon_\text{min}$ hold.
The solver steps the clock, propagates both satellites, and merges consecutive
satisfying samples into windows. For the intercept burn, a coplanar Hohmann
transfer between the two circular orbits yields the two-impulse $\Delta v$
budget

$$ \Delta v = \left|\sqrt{\mu\left(\tfrac{2}{a_1}-\tfrac{1}{a_t}\right)}-\sqrt{\tfrac{\mu}{a_1}}\right|
   + \left|\sqrt{\tfrac{\mu}{a_2}}-\sqrt{\mu\left(\tfrac{2}{a_2}-\tfrac{1}{a_t}\right)}\right| $$

with transfer semi-major axis $a_t = (a_1+a_2)/2$ and transfer time equal to
half the transfer-orbit period.

## 2. Concealed-lair detection via thermal + terrain anomaly

A concealed lair is found by scoring each channel against a locally modelled
background. A Gaussian low-pass

$$ \tilde{g} = K_\sigma * g $$

approximates the smooth natural signal (the thermal lapse with altitude, the
smooth volcanic cone). Each pixel is then expressed as a standardized residual,

$$ z_{ij} = \frac{g_{ij} - \tilde{g}_{ij}}{\sigma_{\text{res}}}, $$

where $\sigma_{\text{res}}$ is the standard deviation of the residuals over the
map. The **thermal anomaly** is the one-tailed $z$ (we look for excess heat); the
**terrain anomaly** is the magnitude $|z|$ (a lair may be a raised shelf *or* an
excavated depression, both of which deviate from the smooth cone). The two maps
are fused with weights $w_T, w_D$ as

$$ s_{ij} = \frac{w_T\, z^T_{ij} + w_D\, z^D_{ij}}{w_T + w_D}. $$

Connected components of the thresholded fused map are labelled by flood fill
and reported as candidate regions, ranked by peak fused score.

## 3. Pattern-of-life analysis

A base's activity is modelled as a Poisson point process whose instantaneous
rate follows a diurnal envelope (a quiet overnight floor plus morning and
evening operating peaks). The observed events are binned into a
$7\times 24$ hourly histogram $h_{d,h}$, giving a mean daily profile

$$ \bar{p}_h = \frac{1}{7}\sum_{d=0}^{6} h_{d,h}. $$

The dominant operational periodicity is read from the normalized
autocorrelation of the weekly series, and contiguous hours of the daily profile
above a given percentile are reported as **peak operating windows**. Tempo is
classified from the mean event rate, and duty cycle is the fraction of hourly
bins containing activity.
