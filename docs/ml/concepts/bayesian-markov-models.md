# Bayesian Markov Models

The [frequentist account](markov-models.md) of a hidden Markov model is a story about
algorithms — a forward recursion, a backward recursion, an Expectation–Maximisation (EM)
loop maximising a likelihood. The Bayesian account is that there is one joint
distribution and everything you compute is a conditional of it:

$$
p(\theta, s_{1:T}, y_{1:T})
= \underbrace{p(\theta)}_{\text{prior}}
\;\underbrace{\pi_{s_1}\prod_{t=2}^{T} P_{s_{t-1} s_t}}_{\text{latent chain}}
\;\underbrace{\prod_{t=1}^{T} p(y_t \mid s_t, \theta)}_{\text{emissions}}
$$

The Markov property is not an assumption bolted on — it *is* the statement that $s_t$
appears in only two factors, so conditioning on it severs the chain. Reading the model as
a directed graph, d-separation gives the rest: $s_{t+1} \perp s_{1:t-1} \mid s_t$,
$y_t \perp y_{-t} \mid s_t$, but $y_{t+1} \not\perp y_{1:t}$ — long memory in $y$ from
short memory in $s$.

## Filtering is Bayes' rule, iterated

The forward recursion is **predict–update**, the same two moves as in any sequential
Bayesian problem. With $\mathbf{b}_t(i) = \Pr(S_t = i \mid y_{1:t})$ — the *belief*:

$$
\begin{aligned}
\textbf{predict:} \quad & \Pr(S_t = j \mid y_{1:t-1}) = \sum_i \mathbf{b}_{t-1}(i)\, P_{ij} \\
\textbf{update:} \quad & \mathbf{b}_t(j) = \frac{p(y_t \mid S_t = j)\,\Pr(S_t = j \mid y_{1:t-1})}{p(y_t \mid y_{1:t-1})}
\end{aligned}
$$

- **Yesterday's posterior is today's prior**, which is why the recursion closes. A
  distribution on $K$ points stays a distribution on $K$ points; the linear-Gaussian
  (Kalman) case closes for the same conjugacy reason. Those are the only two common models
  where sequential Bayes is exact — anything else needs a particle filter.
- **The likelihood is the normalising constant.** The denominator is the one-step
  predictive density, so $\log p(y_{1:T}) = \sum_t \log p(y_t \mid y_{1:t-1})$ is the
  chain rule, not a bonus. Hamilton's filter "returning the log-likelihood for free" is
  this identity.
- **The belief is a sufficient statistic** for $y_{1:t}$, lives on the $(K-1)$-simplex,
  and evolves deterministically from $(\mathbf{b}_{t-1}, y_t)$ — so the belief is itself a
  Markov process. That is the construction behind partially observed Markov decision
  processes (POMDPs), where policies are functions of the belief.

!!! note "Filtering, smoothing and prediction are one object"
    All three are $\Pr(S_t \mid \cdot)$, differing only in what sits right of the bar:
    $y_{1:t}$, $y_{1:T}$, or $y_{1:t}$ pushed $h$ steps forward. Smoothing has lower
    variance because it conditions on more data — not because it is a better estimator —
    and it is inadmissible as a feature for exactly the same reason. The forward–backward
    product $\gamma_t \propto \alpha_t\beta_t$ works because $s_t$ d-separates past from
    future.

## States and parameters diverge asymptotically

Both are unobserved random variables with priors, and that is where the similarity ends.

| | Parameters $\theta$ | States $s_{1:T}$ |
|---|---|---|
| Dimension | fixed | grows with $T$ |
| Data informing each | all $T$ observations | a handful near $t$ |
| As $T \to \infty$ | concentrates, $\mathcal{O}(T^{-1/2})$ | never concentrates |
| Limit | Bernstein–von Mises: Gaussian around the maximum likelihood estimate | no limit |

!!! warning "More data will not tell you which regime you are in today"
    It pins down the transition matrix and the regime means to high precision, but
    $\Pr(S_t \mid y_{1:t})$ is informed by a few observations near $t$ and stays genuinely
    spread out. Irreducible uncertainty about the current state is structural, not a bad
    fit. A crisp regime label is almost always a smoothed Viterbi path hiding this.

The honest real-time objects integrate over both sources of uncertainty:

$$
p(s_t \mid y_{1:t}) = \int p(s_t \mid y_{1:t}, \theta)\, p(\theta \mid y_{1:t})\,\mathrm{d}\theta
$$

[`MarkovRegression`](../statsmodels/markov-regression.md) returns the **plug-in** inner
term $p(s_t \mid y_{1:t}, \hat\theta)$, which understates uncertainty — most where it
matters: early in the sample, after a refit, and when regimes are poorly separated. The
same integral over $y_{t+1}$ gives a posterior predictive that is a **mixture**, hence
multimodal whenever the regimes separate. A point forecast can sit in a trough of its own
predictive density, so score it with a log predictive density, not a root mean squared
error on the posterior mean.

## EM is Bayes with the parameter posterior collapsed

With an approximating family $q$ and the evidence lower bound (ELBO)
$\mathcal{L}[q] = \mathbb{E}_q[\log p(\theta, s, y) - \log q(\theta, s)]$, a whole family
of algorithms is one choice: how much of the posterior to keep.

$$
\begin{aligned}
\text{EM} \quad & q = \delta(\theta - \theta^{(n)})\,q(s) && \text{E-step } q(s) = p(s \mid y, \theta^{(n)}) \\
\text{MAP-EM} \quad & \text{same, } p(\theta) \text{ retained in the M-step} \\
\text{Variational Bayes} \quad & q = q(\theta)\,q(s) && \text{mean-field; underestimates variance} \\
\text{Markov chain Monte Carlo} \quad & \text{exact draws from } p(\theta, s \mid y)
\end{aligned}
$$

Forward–backward in the E-step *is* Bayesian inference over states; only the M-step
collapses $\theta$ to a point. "EM then quasi-Newton" is therefore not a rival paradigm —
it is this computation with parameter uncertainty discarded and reconstructed afterwards
from a numerical Hessian.

## Priors kill named pathologies

Each failure mode of the maximum-likelihood fit is a feature of the likelihood *surface*
that a proper prior flattens.

### Dirichlet rows and stickiness

Each transition row is a probability vector, so the conjugate prior is Dirichlet, and the
update is pseudo-counts plus observed transition counts $n_{ij}$:

$$
P_{i\cdot} \sim \mathrm{Dir}(\alpha_{i1}, \dots, \alpha_{iK}),
\qquad
P_{i\cdot} \mid s \sim \mathrm{Dir}(\alpha_{i1} + n_{i1}, \dots, \alpha_{iK} + n_{iK})
$$

A **sticky** prior adds $\kappa$ to the diagonal,
$\mathrm{Dir}(\alpha, \dots, \alpha + \kappa, \dots, \alpha)$, encoding persistence
*a priori*. This is the fix for the jittery
state sequence full of one-period excursions: it pushes $P_{ii}$ toward 1, so expected
durations $1/(1-P_{ii})$ come out plausible. Maximum likelihood has no vocabulary for "I
believe regimes last months, not days"; here it is one hyperparameter.

### Inverse-Gamma variances

A Gaussian mixture likelihood is **unbounded** — park a regime's mean on one observation
and send $\sigma_i^2 \to 0$. The frequentist variance floor is a hack; with
$\sigma_i^2 \sim \mathcal{IG}(a, b)$ the prior vanishes at the origin fast enough that the
posterior has no spike. The infinity was an artefact of maximising a density with respect
to a parameter controlling its own scale.

### Hierarchical coefficients

A regime occupying 8% of the sample has 8% of the data behind its $\beta_i$. A hierarchy
pools partially:

$$
\beta_i \sim \mathcal{N}(\beta_0, \tau^2 I), \qquad \tau \sim \text{half-Cauchy}
$$

with $\tau$ learned. The limits are the two models you would otherwise pick between by
hand — $\tau \to 0$ is a pooled regression, $\tau \to \infty$ independent regimes — so
`switching_exog=[True, False, False]` becomes a continuous, data-driven degree of
switching per coefficient. Maximum likelihood cannot do this.

### Near-boundary transition probabilities

No `cov_type` gives a trustworthy standard error for $p_{ii}$ near 1, the normal case for
a persistent regime. The diagnosis: the posterior for a probability near the boundary is
**skewed**, so a mode-centred Gaussian of Hessian width is the wrong shape and puts mass
above 1. A Beta/Dirichlet posterior needs no asymptotics and never leaves the simplex —
report an asymmetric credible interval on the expected duration instead.

## Fitting: FFBS and marginalised HMC

The classical scheme (Chib, 1996) is **data augmentation** — sampling $\theta$ is easy
given the path, and the path is easy given $\theta$:

**The path**, by forward-filtering backward-sampling (FFBS): run the filter for all
$\mathbf{b}_t$, then sample backwards,

$$
s_T \sim \mathbf{b}_T, \qquad \Pr(s_t \mid s_{t+1}, y_{1:t}) \propto \mathbf{b}_t(s_t)\,P_{s_t s_{t+1}}
$$

drawing an entire path from $p(s_{1:T} \mid \theta, y)$ per sweep. Single-site Gibbs
(resampling one $s_t$ at a time) mixes catastrophically under a persistent chain, since
flipping a regime requires passing through improbable intermediate paths. FFBS is also the
sampling analogue of Viterbi: it respects the transition structure, so it cannot emit a
zero-probability path.

**The parameters**, given a path, split into conjugate blocks: Dirichlet per transition
row, Normal–Inverse-Gamma regression within each regime's subsample.

!!! tip "Marginalise the states, then use Hamiltonian Monte Carlo"
    Stan, PyMC and NumPyro cannot sample discrete latents, so sum the states out with the
    forward algorithm and run Hamiltonian Monte Carlo (HMC) on the smooth marginal
    $p(y \mid \theta)$. This is Rao–Blackwellisation — strictly lower Monte Carlo variance
    than Gibbs — and it is why "you can't fit a Hidden Markov Model (HMM) in Stan" is a
    myth. Recover $p(s_t \mid y)$ afterwards as a generated quantity.

```python
import numpyro
import numpyro.distributions as dist
from jax import numpy as jnp

def model(y, K=2, kappa=20.0):
    alpha = jnp.ones((K, K)) + kappa * jnp.eye(K)          # sticky rows
    P = numpyro.sample("P", dist.Dirichlet(alpha))         # (K, K)
    sigma = numpyro.sample("sigma", dist.InverseGamma(2.0, 1.0).expand([K]))
    # ... forward algorithm in a scan, then numpyro.factor on the log-likelihood
```

### Label switching is worse here than in EM

The posterior has $K!$ symmetric modes, so **a well-mixing chain is the problem**: visit
several modes and every regime's posterior mean converges to the same value while all
convergence diagnostics look healthy.

- **Identify the model** — enforce $\sigma^2_1 < \dots < \sigma^2_K$ as an ordered vector.
  This also makes "the low-volatility regime" mean something.
- **Relabel after sampling** — permute each draw to a canonical order, if the constraint
  distorts the geometry.

Same issue as canonicalising labels across refits, one level up: there across *fits*, here
across *draws*.

## Choosing $K$

The likelihood-ratio test for $K$ vs $K+1$ has no $\chi^2$ null distribution — the extra
regime's parameters are unidentified under the null and the null sits on the
parameter-space boundary. Comparing probabilities has no such problem, but the options
differ in practicality.

- **Marginal likelihood.**
  $p(y \mid K) = \int p(y \mid \theta, K)\,p(\theta \mid K)\,\mathrm{d}\theta$ penalises
  complexity through the Occam factor, with no boundary or identifiability issue. Two
  caveats: it is awkward to compute (Chib's method, bridge
  sampling), and it stays **prior-sensitive in large samples** — by the
  Jeffreys–Lindley paradox a deliberately vague prior on the extra regime always rejects
  it. Improper or arbitrary-scale priors are unusable here.
- **Predictive scoring — the practical choice.** The evidence factorises into one-step
  predictive log scores, $\log p(y_{1:T}) = \sum_t \log p(y_t \mid y_{1:t-1})$, so the
  marginal likelihood *is* a prequential out-of-sample score. Score the held-out block's
  predictive density. Leave-one-out cross-validation and the Watanabe–Akaike information
  criterion (WAIC) estimate the same thing cheaply, but plain leave-one-out conditions on
  future data — use leave-future-out. See
  [Time-Series Validation](time-series-validation.md).
- **The Bayesian information criterion (BIC)** is a crude Laplace approximation to
  $\log p(y \mid K)$, which is why it works at all for this problem.
- **Don't choose.** The hierarchical Dirichlet process HMM (HDP-HMM) puts a prior on an
  unbounded number of states and lets the posterior concentrate on the occupied ones. The
  sticky variant (Fox et al.) addresses both problems at once — plain HDP-HMM invents
  noise regimes to explain short excursions — and returns a posterior *over* $K$.

## What it changes operationally

- **Walk-forward refitting is sequential updating.** Freeze-and-filter with a periodic
  refit approximates maintaining $p(\theta \mid y_{1:t})$ and integrating over it each
  step; the cadence exists only because a plug-in estimate cannot update continuously.
  Filter burn-in is handled by the prior on the initial state.
- **Causality becomes notational.** Smoothed features, full-sample fits, and choosing $K$
  on all the data are one error — conditioning on $y_{1:T}$ when the decision only gives
  you $y_{1:t}$. Write the conditioning set and the bug is visible. See
  [Data Leakage](data-leakage.md).
- **Tooling.** `statsmodels` is maximum likelihood only — no priors, no parameter
  posterior. Use NumPyro or Stan with the states marginalised, `pymc` for a hand-rolled
  sampler, or `hmmlearn`'s variational Bayes classes for a quick mean-field fit with a
  Dirichlet prior.

## Related

- [Markov Processes](markov-models.md) — the chain structure, forward–backward, and the maximum-likelihood treatment this reframes
- [MarkovRegression](../statsmodels/markov-regression.md) — the plug-in implementation, and the near-boundary standard errors discussed above
- [MarkovAutoregression](../statsmodels/markov-autoregression.md) — where the mixture predictive gets $K^{p+1}$ components
- [Data Leakage](data-leakage.md) — the conditioning-set errors, in their general form
- [Time-Series Validation](time-series-validation.md) — the leave-future-out protocol predictive scoring needs
