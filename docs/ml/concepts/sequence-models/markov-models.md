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
$t$; see [leakage](markov-inference.md#avoiding-leakage)).

## Where this goes next

Defining the chain is half the subject. Fitting one to data, recovering the hidden
state, and doing both without leaking the future are covered in
[Markov Inference](markov-inference.md).

## Related

- [Markov Inference](markov-inference.md) — forward–backward, Viterbi, Baum–Welch, and the leakage traps specific to regime models
- [Bayesian Markov Models](bayesian-markov-models.md) — the same structure as one joint distribution: filtering as iterated Bayes, sticky priors, FFBS, and the evidence as a model-selection criterion
- [MarkovAutoregression](../../statsmodels/markov-autoregression.md) — the switching-autoregression sibling, where the regime path enters the likelihood
- [MarkovRegression](../../statsmodels/markov-regression.md) — the `statsmodels` implementation: constructor defaults, restarts, and frozen-parameter filtering
- [Switching distributions](../../statsmodels/switching-distributions.md) — each distribution on this page matched to the `statsmodels` attribute that estimates it
- [Long Short-Term Memory](lstm.md) — the learned alternative to an explicit latent state, with the same look-ahead trap in its bidirectional form
