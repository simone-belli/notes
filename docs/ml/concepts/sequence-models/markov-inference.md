# Markov Inference

Given a fitted chain, three questions: what is the state now, what was it then, and
which parameters generated the data? The answers are the forward–backward
recursions, Viterbi decoding, and Baum–Welch — plus the discipline that keeps a
regime model from quietly reading the future. The model itself is defined in
[Markov Processes](markov-models.md).

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
  $\sigma^2_i \to 0$ and the likelihood to $+\infty$. Floor the variance or
  [fit MAP-EM with a prior](bayesian-markov-models.md), which removes the spike rather
  than clipping it.
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
[Data Leakage](../validation/data-leakage.md):

- **Smoothed probabilities as features.** $\Pr(S_t = i \mid y_{1:T})$ conditions on
  data through $T$. Use filtered probabilities — or, when the target is $y_t$ itself,
  the one-step predicted
  $\Pr(S_t = i \mid y_{1:t-1}) = \sum_j \Pr(S_{t-1} = j \mid y_{1:t-1}) P_{ji}$, since the
  filtered value at $t$ has already consumed $y_t$.
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

[`statsmodels`](../../statsmodels/markov-regression.md) covers the econometric form,
`hmmlearn` the general HMM:

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

- [Markov Processes](markov-models.md) — the model these recursions run on: state sufficiency, hidden states, exogenous variables
- [Bayesian Markov Models](bayesian-markov-models.md) — the same inference as one joint distribution: filtering as iterated Bayes, sticky priors, FFBS, and choosing $K$ by evidence
- [MarkovRegression](../../statsmodels/markov-regression.md) — the `statsmodels` implementation: restarts, frozen-parameter filtering, filtered vs smoothed attributes
- [Data Leakage](../validation/data-leakage.md) — the general taxonomy these traps instantiate
- [Time-Series Validation](../validation/time-series-validation.md) — the chronological protocol a walk-forward refit sits inside
- [Fold-Safe Transformers](../../scikit-learn/fold-safe-transformers.md) — the same burn-in problem for rolling and recursive features
- [Purged Cross-Validation](../validation/purged-cross-validation.md) — splitting when labels and features overlap in time
