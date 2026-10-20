# Switching distributions

Hamilton's model is three probability distributions, and
[`MarkovRegression`](markov-regression.md) returns an estimate of each one plus the
posterior laws its filter produces on the way. Every attribute on the results object is
one of those distributions — this page is the dictionary. The
[theory](../concepts/markov-models.md) is elsewhere; the point here is which symbol each
number is.

$$
\begin{aligned}
\Pr(s_1 = i) &= \pi_i
  && \text{initial state} \\
\Pr(s_t = j \mid s_{t-1} = i) &= p_{ij}
  && \text{transition kernel} \\
y_t \mid s_t = i, x_t &\sim \mathcal{N}\!\left(x_t^{\top}\beta_i,\ \sigma_i^2\right)
  && \text{emission}
\end{aligned}
$$

Those three — with the Markov property and conditional independence of the $y_t$ given the
states — determine everything else by summation.

## The generative model

| distribution | fitted estimate |
|---|---|
| $\pi_i$ | `mod.initial_probabilities(res.params)` |
| $p_{ij}$ | `res.params["p[i->j]"]`, or all of them as `res.regime_transition` |
| $\beta_i$ | `res.params[mod.parameters[i, "exog"]]` |
| $\sigma_i^2$ | `res.params[mod.parameters[i, "variance"]]` |
| $\mathbb{E}[y_t \mid s_t = i, x_t] = x_t^{\top}\beta_i$ | `mod.predict_conditional(res.params)[i]` |

The [`mod.parameters` index map](switching-parameters.md) is what makes those slices
survive a non-switching parameter; `res.params["sigma2[0]"]` does not.

Only $K(K-1)$ transition probabilities are estimated. statsmodels reports the destinations
$j < K-1$ and leaves the last implied by the row sum:

$$
p_{i,K-1} = 1 - \sum_{j=0}^{K-2} p_{ij}
$$

so a two-regime fit prints `p[0->0]` and `p[1->0]`, and $p_{01} = 1 - p_{00}$ is yours to
compute — or to read off `res.regime_transition`, which contains the full matrix.

Mind the index order when you do: the array is **transposed** relative to the subscripts
here, `res.regime_transition[j, i, 0]` $= p_{ij}$, so the normalisation that reads
$\sum_{j} p_{ij} = 1$ in symbols is a *column* sum of the array.

With [time-varying transition probabilities](markov-regression.md#time-varying-transition-probabilities)
the kernel gains a covariate and the stored parameters are logit coefficients $\delta$,
not probabilities — a multinomial logit per origin regime, with the implied destination
$K-1$ as the reference category ($\delta_{i,K-1} = 0$):

$$
p_{ij}(z_t) = \frac{\exp\!\left(z_t^{\top}\delta_{ij}\right)}
                   {1 + \sum_{k=0}^{K-2} \exp\!\left(z_t^{\top}\delta_{ik}\right)},
\qquad j \leq K-2
$$

## The filter's posteriors

Three laws over the same state, differing only in the conditioning set — which is the
whole of the [filtering vs smoothing](../concepts/markov-models.md#filtering-vs-smoothing)
distinction:

| posterior | attribute |
|---|---|
| $\Pr(s_t = i \mid y_{1:t-1})$ | `res.predicted_marginal_probabilities` |
| $\Pr(s_t = i \mid y_{1:t})$ | `res.filtered_marginal_probabilities` |
| $\Pr(s_t = i \mid y_{1:T})$ | `res.smoothed_marginal_probabilities` |
| $\Pr(s_t = i, s_{t-1} = j \mid y_{1:t})$ | `res.filter_results.filtered_joint_probabilities` |
| $f(y_t \mid y_{1:t-1})$ | `np.exp(res.llf_obs)` |
| $\sum_{t} \log f(y_t \mid y_{1:t-1})$ | `res.llf` |
| $\mathbb{E}[y_t \mid y_{1:T}, x_t]$ | `res.predict()` |
| $\mathbb{E}[y_t \mid y_{1:t-1}, x_t]$ | `res.predict(probabilities="predicted")` |

The marginals are DataFrames indexed like `endog`; the joint arrays are raw filter output
with regime axes first and time last, and the marginals are those with the lagged axis
summed out.

### The three recursion steps

Each table row above is one step of the Hamilton filter, and each step is a line of
algebra on the three model distributions. Prediction propagates through the kernel:

$$
\Pr(s_t = j \mid y_{1:t-1}) = \sum_{i} p_{ij} \Pr(s_{t-1} = i \mid y_{1:t-1})
$$

The observation $y_t$ then enters by Bayes' rule, with the mixture density as the
normalising constant:

$$
\Pr(s_t = i \mid y_{1:t}) =
\frac{\Pr(s_t = i \mid y_{1:t-1})\, f(y_t \mid s_t = i, x_t)}
     {f(y_t \mid y_{1:t-1})},
\qquad
f(y_t \mid y_{1:t-1}) = \sum_{i} \Pr(s_t = i \mid y_{1:t-1})\, f(y_t \mid s_t = i, x_t)
$$

!!! note "`llf` is the forecast density, not a fit statistic"
    That normalising constant *is* the one-step-ahead predictive density of $y_t$, and
    `res.llf` is $\sum_t \log$ of it. The likelihood these models maximise is therefore
    already a genuinely out-of-sample-in-spirit quantity at each $t$ — which is why
    `res.llf` from `mod.filter(frozen_params)` is a legitimate forecast score, while
    anything built from the smoothed probabilities is not.

The backward pass redistributes using the whole sample, giving the smoothed law:

$$
\Pr(s_t = i \mid y_{1:T}) = \Pr(s_t = i \mid y_{1:t})
\sum_{j} \frac{p_{ij} \Pr(s_{t+1} = j \mid y_{1:T})}{\Pr(s_{t+1} = j \mid y_{1:t})}
$$

## Durations

`res.expected_durations` is not a fourth distribution but a consequence of the kernel: the
time spent in regime $i$ before leaving is
[geometric](../concepts/markov-models.md#geometric-dwell-times),

$$
\Pr(D_i = d) = p_{ii}^{\,d-1}(1 - p_{ii}),
\qquad \mathbb{E}[D_i] = \frac{1}{1 - p_{ii}}
$$

and the ergodic distribution $\pi$ solving $\pi = P\pi$ is the long-run share of time in
each regime — for $K = 2$ exactly the duration-weighted one, $\pi_0 = d_0 / (d_0 + d_1)$.

!!! warning "A vector of marginals is not a path"
    `res.smoothed_marginal_probabilities` gives $\Pr(s_t = i \mid y_{1:T})$ **one $t$ at a
    time**. Taking `argmax` along the regime axis does not yield
    $\arg\max \Pr(s_{1:T} \mid y_{1:T})$ — the pointwise-optimal sequence can even have
    zero probability under the model when a transition it implies has $p_{ij} = 0$.
    statsmodels ships no Viterbi decoder, so a maximum-a-posteriori *path* is yours to
    write; see [Viterbi vs pointwise decoding](../concepts/markov-models.md#viterbi-vs-pointwise-decoding).

## Related

- [MarkovRegression](markov-regression.md) — the class these attributes hang off, and the constructor arguments that decide which $\beta_i$ and $\sigma_i^2$ exist
- [Switching parameters](switching-parameters.md) — the mechanics of slicing the vector, where this page gives the meaning
- [predict](predict.md) — the weighting argument behind the two expectation rows
- [Markov Processes](../concepts/markov-models.md) — the derivations summarised here
- [Bayesian Markov Models](../concepts/bayesian-markov-models.md) — what these point estimates hide, since every table entry is a plug-in at $\hat\theta$
