# Markov Processes

A process is **Markov** when the future is conditionally independent of the past
given the present:

$$
\Pr(X_{t+1} \in A \mid X_t, X_{t-1}, \dots, X_0) = \Pr(X_{t+1} \in A \mid X_t)
$$

"Memorylessness" is the usual gloss, and it misleads — the process has plenty of
memory, all of it compressed into $X_t$. The real claim is **state sufficiency**:
$X_t$ is a sufficient statistic of the whole history for predicting the future.

!!! note "Not a property of the world, a property of your state variable"
    Whether a series is Markov depends on where you drew the state boundary. An
    order-$k$ chain ($\Pr(X_{t+1} \mid X_{0:t}) = \Pr(X_{t+1} \mid X_{t-k+1:t})$)
    becomes first-order on the stacked state $\tilde{X}_t = (X_{t-k+1}, \dots, X_t)$,
    and a non-Markov observable becomes Markov once you add a latent state. You pay
    in dimension: a $k$-th order chain on $K$ states has $K^k(K-1)$ free parameters.

## Finite chains

A finite-state, discrete-time chain is one **row-stochastic** transition matrix:

$$
P_{ij} = \Pr(X_{t+1} = j \mid X_t = i), \qquad P_{ij} \ge 0, \quad \sum_j P_{ij} = 1
$$

With the marginal as a row vector, one step is $\pi_{t+1} = \pi_t P$, and $n$ steps
are the $n$-th matrix power, $\pi_{t+n} = \pi_t P^n$ — the **Chapman–Kolmogorov**
equation. Long-run behaviour is therefore spectral.

- **Irreducible** — every state reachable from every other. States communicate in a
  single class.
- **Period** $d(i) = \gcd\{n \ge 1 : (P^n)_{ii} > 0\}$; $d = 1$ is **aperiodic**. A
  single self-loop in an irreducible chain makes the whole chain aperiodic.
- **Recurrent** vs **transient** — return certain or not. On a finite space every
  recurrent state is positive recurrent, so the distinction only bites on infinite
  spaces.
- **Ergodic** — irreducible, aperiodic, positive recurrent.

### Stationary distribution

$\pi$ is stationary when $\pi P = \pi$ — a left eigenvector for eigenvalue 1,
normalised to sum to 1. Two statements that get conflated:

$$
\begin{aligned}
\text{irreducible} &\;\Longrightarrow\; \exists!\,\pi : \pi P = \pi
  && \text{existence and uniqueness} \\
\text{irreducible} + \text{aperiodic} &\;\Longrightarrow\; \pi_0 P^n \to \pi \;\; \forall \pi_0
  && \text{convergence}
\end{aligned}
$$

A period-2 chain has a unique $\pi$ it never converges to — it oscillates forever.
Aperiodicity is what kills the oscillation.

Two quantities worth computing on any fitted chain:

$$
\mathbb{E}[T_i \mid X_0 = i] = \frac{1}{\pi_i},
\qquad
\tau_{\text{rel}} = \frac{1}{1 - |\lambda_2|}
$$

the expected return time, and the **relaxation time** set by the second-largest
eigenvalue modulus $|\lambda_2|$ — how long before the initial condition is
forgotten. For two states, $\lambda_2 = P_{11} + P_{22} - 1$.

**Reversibility.** $\pi_i P_{ij} = \pi_j P_{ji}$ (detailed balance) implies
stationarity but is strictly stronger — flux balances pairwise, not just in
aggregate. It is the design principle behind Markov Chain Monte Carlo (MCMC).

### Geometric dwell times

The Markov property forces the time spent in a state to be geometric:

$$
\Pr(D_i = d) = P_{ii}^{\,d-1}(1 - P_{ii}), \qquad \mathbb{E}[D_i] = \frac{1}{1 - P_{ii}}
$$

which is monotone decreasing — the single most likely duration of any regime is one
period. Real regimes usually have a hump-shaped duration distribution. Fixes:
**hidden semi-Markov** models, which parametrise $\Pr(D_i = d)$ directly, or chaining
$m$ sub-states in series to get an Erlang duration.

!!! tip "Continuous analogues"
    Continuous time swaps $P$ for a generator $Q$ (rows summing to zero), giving
    $P(t) = e^{tQ}$ and exponential holding times. Continuous state swaps it for a
    kernel $p(x' \mid x)$: the AR(1) process $x_t = \phi x_{t-1} + \varepsilon_t$ is
    Markov, AR($p$) is Markov only in the stacked vector, and the
    Ornstein–Uhlenbeck process $dx_t = \theta(\mu - x_t)\,dt + \sigma\,dW_t$ is the
    continuous-time AR(1).

## Hidden states

Observable series are rarely Markov. Posit a latent chain $S_t \in \{1,\dots,K\}$
driving observations $Y_t$ — a **Hidden Markov Model (HMM)** — under two conditional
independence assumptions, giving

$$
p(y_{1:T}, s_{1:T}) = \pi_{s_1} p(y_1 \mid s_1) \prod_{t=2}^{T} P_{s_{t-1}s_t} \, p(y_t \mid s_t)
$$

$Y_t$ itself is *not* Markov — marginalising $S$ out induces dependence on the whole
history. That is the point: long-memory observable behaviour from a short-memory
latent mechanism. With a continuous latent state and linear-Gaussian dynamics the
same model is the Kalman filter; the recursions below have the same shape there.

Everything runs off the **forward recursion** on $\alpha_t(i) = p(y_{1:t}, S_t = i)$:

$$
\alpha_1(i) = \pi_i \, p(y_1 \mid i),
\qquad
\alpha_t(j) = p(y_t \mid j) \sum_{i} \alpha_{t-1}(i) P_{ij}
$$

in $O(TK^2)$ instead of the $K^T$ paths. Its normalising constants are the one-step
predictive densities, so the log-likelihood comes out of the filter for free:
$\log p(y_{1:T}) = \sum_t \log p(y_t \mid y_{1:t-1})$. In econometrics this is
**Hamilton's filter**.

!!! warning "Rescale or work in logs"
    $\alpha_t$ is a joint density over $t$ observations and underflows exponentially.
    Either rescale each step (the logs of the scale factors sum to the
    log-likelihood) or run the recursion with `logsumexp`.

## Exogenous variables

A covariate $z_t$ can enter in three places, with different meanings.

**In the emission** — regime-dependent coefficients, i.e. Hamilton's
Markov-switching regression:

$$
y_t = x_t^{\top}\beta_{s_t} + \varepsilon_t, \qquad \varepsilon_t \sim \mathcal{N}(0, \sigma^2_{s_t})
$$

The *relationship* between $x$ and $y$ changes with the regime. Switching the
variance only gives a discrete-state stochastic volatility model; letting lagged $y$
enter gives Markov-switching autoregression (and, if the autoregressive coefficients
switch too, a state space of $K^{r+1}$ that Kim's filter collapses back down).

**In the transition** — time-varying transition probabilities (TVTP), a multinomial
logit per row with one category fixed for identification:

$$
P_{ij}(z_t) = \frac{\exp(z_t^{\top}\delta_{ij})}{\sum_{k} \exp(z_t^{\top}\delta_{ik})},
\qquad \delta_{iK} \equiv 0
$$

This is the qualitatively interesting case: instead of "the model switched because
the data demanded it" you get "a widening spread raises the hazard of entering the
stressed regime", and expected durations become covariate-dependent,
$\mathbb{E}[D_i \mid z] = 1/(1 - P_{ii}(z))$. In machine learning the same structure
is the **input–output HMM (IOHMM)**. Cost: $K(K-1)\dim(z)$ parameters and the loss of
a closed-form M-step.

**In the initial distribution** — $\pi_i(z_1)$, which matters only for short series
or panels of many short sequences.

Exogeneity requires two things that are easy to assume and easy to violate: **no
feedback** ($z_t$ not caused by $S_t$ or past $Y$ — weak exogeneity, not merely "a
different variable"), and **availability** ($z_t$ genuinely in the information set at
$t$; see leakage below).

## Filtering vs smoothing

Three conditioning sets, three different objects:

$$
\begin{aligned}
\textbf{prediction} \quad & \Pr(S_{t+h} = i \mid y_{1:t}), \; h > 0 \\
\textbf{filtering} \quad & \Pr(S_t = i \mid y_{1:t}) \\
\textbf{smoothing} \quad & \Pr(S_t = i \mid y_{1:T}), \; T > t
\end{aligned}
$$

Filtering is the normalised forward recursion — causal, online, $O(K^2)$ per new
observation. Smoothing adds a backward pass over
$\beta_t(i) = p(y_{t+1:T} \mid S_t = i)$:

$$
\beta_T(i) = 1, \qquad \beta_t(i) = \sum_j P_{ij} \, p(y_{t+1} \mid j) \, \beta_{t+1}(j)
$$

$$
\gamma_t(i) = \Pr(S_t = i \mid y_{1:T}) = \frac{\alpha_t(i)\beta_t(i)}{\sum_j \alpha_t(j)\beta_t(j)}
$$

The forward term carries the past, the backward term the future, and the Markov
property is exactly what lets them multiply. The Kalman analogue is the
Rauch–Tung–Striebel (RTS) smoother — same architecture.

| | Filtered | Smoothed |
|---|---|---|
| Information set | $y_{1:t}$ | $y_{1:T}$ |
| Available in real time | **yes** | no |
| Variance of the estimate | higher | lower |
| Reacts to a switch | with delay | sharply, at the right date |
| Correct for forecasting features | **yes** | never |
| Correct for historical analysis | suboptimal | **yes** |

!!! warning "If the regime plot looks too good, check which recursion made it"
    Smoothed probabilities show crisp near-0/1 segments with switches dated to the
    right week, because they are allowed to see what the regime did next. That visual
    superiority is the warning sign, not the selling point.

### Viterbi vs pointwise decoding

Two different readings of "most likely state sequence":

$$
\begin{aligned}
\text{pointwise:} \quad & \hat{s}_t = \operatorname*{arg\,max}_i \gamma_t(i) \ \text{ independently per } t \\
\text{Viterbi:} \quad & \hat{s}_{1:T} = \operatorname*{arg\,max}_{s_{1:T}} p(s_{1:T} \mid y_{1:T})
\end{aligned}
$$

Pointwise decoding maximises expected per-step accuracy but can return a sequence of
**probability zero** — if $P_{13} = 0$ and the marginals peak at 1 then 3, that
transition is one the model forbids. Viterbi (a max-product pass over the same
trellis) is always feasible but can be pointwise worse, and one extra observation can
rewrite the whole path. Use Viterbi for a coherent segmentation, marginals for
per-period features.

## Estimation with EM

The likelihood sums over $K^T$ paths. **Expectation–Maximisation (EM)** — here
**Baum–Welch** — sidesteps it by exploiting the fact that *if the states were
observed*, estimation would be trivial weighted maximum likelihood. Setting
$q = p(S \mid y, \theta^{(n)})$ makes the evidence lower bound tight at the current
iterate, so maximising it cannot decrease the likelihood: EM's **monotone ascent**
guarantee.

**E-step** — run forward–backward at $\theta^{(n)}$ for $\gamma_t(i)$ and the pairwise
posteriors $\xi_t(i,j) = \Pr(S_t = i, S_{t+1} = j \mid y_{1:T})$. These are *smoothed*
quantities, which is correct here: in estimation you genuinely do have the whole
sample.

**M-step** — $Q(\theta \mid \theta^{(n)})$ separates additively into initial,
transition, and emission terms, each an ordinary maximum likelihood estimate (MLE)
with posterior weights:

$$
\hat{P}_{ij} = \frac{\sum_{t} \xi_t(i,j)}{\sum_{t} \gamma_t(i)},
\qquad
\hat{\mu}_i = \frac{\sum_t \gamma_t(i)\,y_t}{\sum_t \gamma_t(i)},
\qquad
\hat{\beta}_i = (X^{\top} W_i X)^{-1} X^{\top} W_i y
$$

with $W_i = \operatorname{diag}(\gamma_1(i), \dots, \gamma_T(i))$. The transition
update is just "expected $i \to j$ transitions over expected visits to $i$"; the
emission update is whatever that family's MLE is, with observation weights
$\gamma_t(i)$ — weighted least squares for a linear emission, weighted iteratively
reweighted least squares for a generalised linear model (GLM).

TVTP breaks the closed form: maximising over $\delta$ is a weighted multinomial
logistic regression. Take one Newton step instead of solving it — **generalised EM**
only needs to *increase* $Q$, and keeps monotone ascent.

### What goes wrong

- **Local optima.** EM finds a stationary point, rarely the global one. Use 20–100
  random restarts and keep the best final log-likelihood; never trust a single run.
- **Label switching.** The likelihood is invariant under the $K!$ permutations of
  state labels. Harmless within a run, fatal across restarts and refits — impose a
  fixed ordering afterwards (ascending emission variance, say).
- **Degeneracy.** A Gaussian state can collapse onto one observation, sending
  $\sigma^2_i \to 0$ and the likelihood to $+\infty$. Floor the variance or fit MAP-EM
  with a prior.
- **Slow tail convergence.** The rate is governed by the fraction of missing
  information. Stop on relative log-likelihood change ($\approx 10^{-6}$) and cap
  iterations.
- **Choosing $K$.** The likelihood ratio test for $K$ vs $K+1$ has **no $\chi^2$ null
  distribution** — the extra state's parameters are unidentified and the null is on
  the parameter-space boundary. Use the Bayesian information criterion (BIC), a
  parametric bootstrap, or out-of-sample predictive likelihood, and sanity-check
  expected durations: a regime lasting 1.3 periods is a noise state.

Alternatives: direct quasi-Newton maximisation of the filtered likelihood (gives a
numerical Hessian for standard errors, which EM does not), or Gibbs sampling with
forward-filtering backward-sampling (FFBS) for the Bayesian treatment.

## Avoiding leakage

Regime models are unusually good at producing a brilliant backtest with no predictive
content. The specific traps, on top of the general ones in
[Data Leakage](data-leakage.md):

- **Smoothed probabilities as features.** $\Pr(S_t = i \mid y_{1:T})$ conditions on
  data through $T$. Use filtered probabilities — or, when the target is $y_t$ itself,
  the one-step predicted $\Pr(S_t = i \mid y_{1:t-1}) = \sum_j \Pr(S_{t-1} = j \mid
  y_{1:t-1}) P_{ji}$, since the filtered value at $t$ has already consumed $y_t$.
- **Full-sample fitting.** Even with a filtered recursion, $\hat{\theta}$ was
  estimated on data including the test period. Fit on $y_{1:t_0}$, freeze
  $\hat{\theta}$, carry the filter state across the boundary, refit on a cadence.
- **Choosing $K$ on the full sample.** Picking three regimes because three "look
  right" over the whole history is feature-selection leakage wearing a different hat.
- **Stale exogenous data.** A macro variable for March published in late April was not
  available at end-March, and its revised value is partly a function of later
  information. Use point-in-time vintages, lagged by the real publication delay.
- **Label switching across refits.** `prob_state_1` is a meaningless series if EM
  labels the low-volatility cluster differently at each refit. Canonicalise by a
  fixed rule and assert the mapping is stable.
- **Reporting smoothed decoding as performance.** "Identified 91% of recession months"
  from a full-sample Viterbi path describes history. The forecasting number is the
  **decoding delay**: how many periods after a true switch did the *filtered*
  probability cross 0.5? Usually several — and that is what decides tradability.
- **Filter burn-in.** The out-of-sample filter starts diffuse and needs time to
  concentrate. Exclude burn-in from scoring, and never initialise it from smoothed
  in-sample output.

!!! warning "Both halves have to be causal"
    Full-sample fit with filtered inference is still leakage. Walk-forward fit with
    smoothed inference is still leakage. You need a causal parameter estimate *and* a
    causal state estimate.

## In practice

`statsmodels` covers the econometric form, `hmmlearn` the general HMM:

```python
import statsmodels.api as sm

mod = sm.tsa.MarkovRegression(
    y_train, k_regimes=2, exog=X_train, switching_variance=True
)
res = mod.fit()                       # EM-initialised, then numerical ML

res.filtered_marginal_probabilities   # causal — safe as a feature
res.smoothed_marginal_probabilities   # uses y_1:T — historical analysis only
res.expected_durations                # sanity check against 1 / (1 - P_ii)
```

```python
from hmmlearn.hmm import GaussianHMM

hmm = GaussianHMM(n_components=3, covariance_type="diag",
                  n_iter=200, tol=1e-6, random_state=0)
hmm.fit(Y_train)                      # Baum–Welch

hmm.predict(Y)                        # Viterbi path — whole-sequence MAP
hmm.predict_proba(Y)                  # SMOOTHED posteriors — not a causal feature
hmm.score(Y)                          # log-likelihood, for restart selection / BIC
```

Both `predict` and `predict_proba` are non-causal; a real-time pipeline has to run
the forward recursion itself, one observation at a time.

The order of operations that keeps you honest:

1. Split chronologically **first**.
2. Choose $K$ and the specification on the training block only.
3. Fit with many restarts; canonicalise the state labels.
4. Freeze $\theta$ and run the filter forward across the boundary.
5. Refit on an expanding or rolling window at a fixed cadence; re-canonicalise.
6. Score out-of-sample only, excluding burn-in, and report decoding delay next to
   accuracy.

## Related

- [Data Leakage](data-leakage.md) — the general taxonomy these traps instantiate
- [Time-Series Validation](time-series-validation.md) — the chronological protocol a walk-forward refit sits inside
- [Fold-Safe Transformers](../scikit-learn/fold-safe-transformers.md) — the same burn-in problem for rolling and recursive features
- [Long Short-Term Memory](lstm.md) — the learned alternative to an explicit latent state, with the same look-ahead trap in its bidirectional form
- [Purged Cross-Validation](purged-cross-validation.md) — splitting when labels and features overlap in time
