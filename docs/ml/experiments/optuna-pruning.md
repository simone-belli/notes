---
tags:
  - errors
  - performance
---

# Optuna — Pruning

Sampling decides *where* to evaluate; pruning decides *how long*. Any objective
with a learning curve is an *anytime* objective — after five epochs you hold a
noisy estimate of the final score, and if it is bad enough, finishing is paying
for information you already have.

The correlation between $\ell_i(t)$ at a small $t$ and $\ell_i(T)$ at the full
budget is positive but not $1$. That gap is pruning's entire error budget, and it
is why pruning systematically penalises configurations whose curves cross late:
low learning rates, heavy regularisation, long warmups.

```python
import optuna

def objective(trial: optuna.Trial) -> float:
    model = build(trial)
    for epoch in range(100):
        train_one_epoch(model)
        val = validate(model)
        trial.report(val, epoch)          # write the intermediate value
        if trial.should_prune():          # ask the study's pruner
            raise optuna.TrialPruned()
    return val
```

- `trial.report(value, step)` is a **write to storage**, not a decision. `step`
  is a non-negative int and must increase; a repeated step is ignored. The value
  has to be the same metric in the same direction as what you return — nothing
  checks that.
- `trial.should_prune()` delegates to `study.pruner.prune(study, trial)`, which
  reads *every* trial's reported values out of the storage backend. That is why
  pruning works across processes sharing a
  [`storage=`](optuna-studies.md#storage-and-parallelism).
- `raise optuna.TrialPruned()` is how the decision is recorded. Returning early
  instead marks the trial `COMPLETE` with an epoch-5 value competing against
  other trials' epoch-100 values.

## Why the budget collapses

With reduction factor $\eta$, starting budget $r_0$, and $K+1$ rungs, successive
halving quadruples the per-trial budget exactly as it quarters the population:

$$
\sum_{k=0}^{K} \frac{n}{\eta^{k}} \cdot \left(r_0 \eta^{k}\right) = n\,r_0\,(K+1)
$$

The cost is **flat in the rung index** — $K+1$ rungs of a cheap budget rather
than one rung of an expensive one, against $nT$ for unpruned random search.

## What `PRUNED` means downstream

| Consumer | Treatment of a `PRUNED` trial |
|---|---|
| `study.best_trial` / `best_value` | ignored — only `COMPLETE` trials are candidates |
| `MedianPruner`'s comparison pool | ignored — the median is over `COMPLETE` trials |
| `TPESampler`'s densities | ignored unless `consider_pruned_trials=True` |
| `SuccessiveHalvingPruner` | used — rung membership *is* the algorithm |
| `trials_dataframe()` | present, `value` empty, `state="PRUNED"` |

!!! warning "A pruned trial teaches the sampler nothing"
    Prune 80% of a 100-trial study and the Tree-structured Parzen Estimator (TPE)
    fits its densities on 20 observations — barely past `n_startup_trials=10`. You
    paid for Bayesian optimisation and got random search. Fixes, in order: raise
    `n_warmup_steps`; switch to `HyperbandPruner`, whose brackets guarantee some
    trials run long; or set `consider_pruned_trials=True` and accept the
    optimistic bias of using a truncated curve's last value.

## The pruners

A pruner is a standalone object handed to `create_study(pruner=...)`.

```python
optuna.pruners.MedianPruner(
    n_startup_trials=5,    # no pruning until 5 trials have COMPLETEd
    n_warmup_steps=0,      # no pruning before this step within a trial
    interval_steps=1,      # check every k steps after warmup
)
```

- **`MedianPruner`** (default) — cut if the best intermediate value so far is
  worse than the median of completed trials at the same step. Relative, with no
  model of the curve, so it prunes ~50% of trials by construction.
  `n_warmup_steps` is the dial that stops it murdering slow starters.
- **`SuccessiveHalvingPruner`** — Asynchronous Successive Halving (ASHA). Rungs
  sit at $r_k = r_{\min}\,\eta^{\,k+s}$ for `reduction_factor` $\eta$ and
  `min_early_stopping_rate` $s$; a trial reaching rung $k$ is promoted only if it
  ranks in the top $1/\eta$ there. *Asynchronous* means promotion on arrival
  rather than waiting for the rung to fill — it scales to hundreds of workers at
  the cost of ranking against a small, noisy rung.
- **`HyperbandPruner`** — refuses to choose $r_{\min}$, running several ASHA
  brackets at different $s$ and splitting the budget. A hedge, not an improvement
  within any one bracket. `max_resource="auto"` calibrates from the steps
  reported by trials that finish, so it needs at least one unpruned trial.
- **`ThresholdPruner(lower=, upper=)`** — absolute, not relative: cut when the
  reported value leaves the interval. Needs no comparison pool and no startup
  trials, and it is the only pruner expressing domain knowledge rather than a
  ranking. The right tool for divergence.
- **`PatientPruner(wrapped, patience, min_delta)`** — a decorator that only lets
  `wrapped` fire after `patience` steps without improvement, converting "one bad
  epoch" into "a sustained stall".
- **`WilcoxonPruner`** — for objectives that average over instances (folds,
  assets); report per-instance values and a signed-rank test decides whether the
  gap is real.
- **`NopPruner`** — prunes nothing. Run the search with it once as a control;
  otherwise you cannot know whether pruning cost you the winner.

## The score a diverging trial deserves

A trial whose training blew up has no meaningful final metric, but the objective
must still return a float or raise. Returning not-a-number (`nan`) is **not** an
option — Optuna marks that trial `FAIL`.

| State | How you get it | Has a value? | Sampler learns from it |
|---|---|---|---|
| `COMPLETE` | `return value` | yes | yes |
| `PRUNED` | `raise optuna.TrialPruned()` | no | no, by default |
| `FAIL` | any other exception, or returning `nan` | no | no |

!!! note "The question that decides it"
    Is the divergence a property of the **hyperparameters** or of the
    **infrastructure**? A learning rate past the stable region is reproducible
    from the sampled point — that is information about the space and the sampler
    must receive it as a bad value. An out-of-memory error or a preempted worker
    is not; scoring it badly permanently condemns a region that was fine.

So `FAIL` — "no observation here" — is right for infrastructure and wrong for
dynamics: the point still looks unexplored, and TPE will come back and burn the
budget again. The options for a genuine divergence:

- **`raise optuna.TrialPruned()`** — same revisit problem, since the sampler
  ignores pruned trials. Only right under ASHA/Hyperband, where rung position is
  itself the signal, or with `consider_pruned_trials=True`.
- **`return float("inf")`** — accepted where `nan` is not, ranks last, so TPE's
  quantile split files it under *bad*. But it breaks any sampler that regresses
  on $y$ (`GPSampler`), breaks `plot_optimization_history` and any mean over
  trial values, and makes "diverged at epoch 90 from 0.31" identical to "`nan` at
  step 3".
- **A large finite sentinel** — keeps plots and surrogates working, but the
  magnitude matters: a Gaussian process fitting $y \in [0.3, 0.5] \cup \{10^6\}$
  spends its whole output length-scale on the sentinel and models the interesting
  range as flat noise.

### Cap at the trivial baseline

There is a non-arbitrary worst score: what the **constant predictor** achieves on
the same validation data.

$$
\ell_{\text{cap}} =
\begin{cases}
\ln C & \text{balanced } C\text{-class cross-entropy},\\[2pt]
-\sum_c p_c \ln p_c & \text{class priors } p_c,\\[2pt]
\operatorname{Var}[y] & \text{mean-squared error, predicting } \bar y,\\[2pt]
0 & \text{coefficient of determination } R^2.
\end{cases}
$$

```python
return min(value, CAP)        # direction="minimize"
```

- **On the same scale as real scores**, so a surrogate's length scale stays sane.
- **Interpretable** — "no better than predicting the mean".
- **Monotone-correct** — every useful trial is strictly below the cap, so the cap
  can never outrank a real result.
- **Collapses divergence and uselessness into one event**, which for selection
  purposes they are: both models are undeployable.

The cost is ties — many trials land on `CAP` exactly, giving the sampler no
ordering among them. That is fine, because the ranking of useless configurations
carries nothing. If you want a tiebreak, add a penalty too small to reorder a
capped trial below a real one:

```python
return min(value, CAP) + 0.01 * CAP * (1 - diverged_at / total_steps)
```

### Final value or best value?

A separate choice: which point on the curve *is* the score.

- **Final** — honest if you ship the model as it stands at the end. A trial that
  reaches $0.31$ at epoch 30 and `nan` by epoch 60 scores as a divergence,
  because the artifact is garbage.
- **Best**, $\min_t \ell(t)$ — honest only if you checkpoint on validation and
  would ship the epoch-30 weights. Note that $\min_t$ over a noisy curve is a
  biased estimate of the achievable loss, and the bias grows with the number of
  epochs minimised over — the same selection-bias-on-the-extremum effect as
  reporting `study.best_value` as an expected out-of-sample result. See
  [Model Validation](../concepts/model-validation.md).

!!! warning "Mixing the two biases towards blow-ups"
    The failure mode is best-value scoring for diverging trials (because `nan`
    forced your hand) and final-value scoring for the rest. Diverging
    configurations then get scored on their most favourable epoch while
    well-behaved ones get scored on their last.

### A complete objective

```python
import math
import optuna
import torch

CAP = math.log(N_CLASSES)               # the constant-predictor loss

def objective(trial: optuna.Trial) -> float:
    lr = trial.suggest_float("lr", 1e-5, 1e-1, log=True)
    model, opt = build(trial, lr)

    best = math.inf
    for epoch in range(EPOCHS):
        train_loss = train_one_epoch(model, opt)
        if not math.isfinite(train_loss):            # hard divergence
            trial.set_user_attr("diverged_at", epoch)
            return CAP
        val = validate(model)
        best = min(best, val)
        trial.report(val, epoch)
        if trial.should_prune():                     # merely slow
            raise optuna.TrialPruned()
    return min(best, CAP)

study = optuna.create_study(
    direction="minimize",
    pruner=optuna.pruners.ThresholdPruner(upper=CAP, n_warmup_steps=5),
)
study.optimize(objective, n_trials=200,
               catch=(torch.cuda.OutOfMemoryError,))
```

Three distinct exits: divergence returns `CAP` as a `COMPLETE` trial so the
sampler avoids the region, with the forensics parked in a user attribute;
slow-but-healthy raises `TrialPruned`; infrastructure is swallowed by `catch=`
into `FAIL`, leaving the point retryable. `ThresholdPruner(upper=CAP)` is belt
and braces — it cuts a trial whose *validation* loss crosses the cap even while
training loss is still finite.

## Measuring divergence

Ordered by how early they fire. Earlier is better: `nan` is the *last* symptom,
arriving long after the weights were ruined.

### Non-finite loss — the backstop

```python
import math

if not math.isfinite(loss_value):      # catches nan and ±inf
    ...
```

`nan != nan`, so equality comparison against `float("nan")` is always `False` —
use `math.isfinite` (or `torch.isfinite` on a tensor). And check **before**
`optimizer.step()`: a non-finite gradient writes `nan` into the weights, from
which every later loss, metric, and gradient is `nan` forever.

```python
from torch.nn.utils import clip_grad_norm_

loss.backward()
total_norm = clip_grad_norm_(model.parameters(), max_norm=1.0)
if not torch.isfinite(total_norm):
    break                              # weights still clean; bail out
optimizer.step()
```

A non-finite `total_norm` also catches a poisoned *gradient* while the loss still
looks fine — a `0 * inf` in an unused branch, or `log(0)` at a masked position.

!!! warning "Automatic mixed precision produces `inf` on purpose"
    `torch.amp.GradScaler` overflows, skips the step, and halves the scale as
    normal operation, so a skipped step is not divergence. Watch
    `scaler.get_scale()` instead — a scale collapsing by orders of magnitude over
    many steps *is*.

### Loss relative to its own best — the workhorse

Scale-free, loss-agnostic, and it fires within a few steps of the blow-up:

$$
\text{diverged} \iff \ell_t > \kappa \cdot \min_{s \le t} \ell_s,
\qquad \kappa \in [3, 10]
$$

Comparing against $\min_s \ell_s$ rather than $\ell_0$ is the point — it catches
"fell nicely, then exploded", which the $\ell_0$ test misses once the loss has
dropped an order of magnitude. It is the stopping rule of the
[Learning Rate Range Test](../concepts/lr-range-test.md), with $\kappa = 4$.

```python
best = math.inf
for step, batch in enumerate(loader):
    loss = train_step(batch)
    best = min(best, loss)
    if loss > 4 * best:
        break
```

Smooth a noisy per-batch loss first, with the same bias correction Adam applies
to its moment estimates (without it the first few values are pulled towards zero
— see [Gradient Descent](../concepts/gradient-descent.md)):

$$
\bar\ell_t = \beta\,\bar\ell_{t-1} + (1-\beta)\,\ell_t,
\qquad \hat\ell_t = \frac{\bar\ell_t}{1 - \beta^{t}},
\qquad \beta \approx 0.98
$$

### Gradient norm, update ratio, parameter norm

Divergence is geometric — $\lVert g_t \rVert$ multiplies by a constant per step —
and visible before the loss moves, because the loss is a scalar aggregate while
the gradient is what does the damage:

$$
\lVert g_t \rVert > \kappa \cdot \operatorname{EMA}_\beta\!\left(\lVert g \rVert\right)
$$

`clip_grad_norm_(..., max_norm=float("inf"))` makes that a pure measurement with
no clipping side effect. Sustained update-to-parameter ratio
$\rho = \eta \lVert g \rVert / \lVert \theta \rVert \ge 10^{-2}$ (healthy is
$\approx 10^{-3}$) is the mechanism observed directly: the update overwrites the
weight rather than adjusting it. Unbounded $\lVert \theta_t \rVert$ growth is the
slowest and least ambiguous signal — nothing but divergence makes weights grow
geometrically. Per-layer versions of all three, and how to read them together,
are in [Training Diagnostics](../concepts/training-diagnostics.md).

### Worse than the trivial baseline

For *scoring*, the operational definition is not "numerically exploded" but
"useless", and the two should share an exit:

$$
\ell_t > \ell_{\text{cap}} \quad \text{at some } t > t_{\text{warmup}}
$$

This is what `ThresholdPruner(upper=CAP, n_warmup_steps=...)` encodes, and it
closes the gap the other detectors leave: a configuration that never produces a
`nan`, never spikes a gradient, and simply trains to a loss above $\ln C$ is
exactly as worthless as one that exploded.

| Context | Detector |
|---|---|
| Any training loop, non-negotiable | non-finite check before `step()` |
| Hyperparameter-optimisation objective | ratio to best, plus a threshold pruner |
| Debugging *why* it diverges | gradient norm and update ratio, per layer |
| Mixed precision | `scaler.get_scale()` collapse, not raw `inf` |

## Related

- [Optuna](optuna.md) — define-by-run spaces, the suggest API, and the samplers
  pruning has to cooperate with
- [Optuna — Studies](optuna-studies.md) — the storage backend the pruner reads,
  and `catch=` in context
- [Training Diagnostics](../concepts/training-diagnostics.md) — the per-layer
  probes behind the divergence detectors
- [Learning Rate Range Test](../concepts/lr-range-test.md) — the
  $4\times$-best-loss stopping rule, used for the same reason
- [Model Validation](../concepts/model-validation.md) — why $\min_t$ over a curve
  and $\min_i$ over trials are both optimistic
- [Tuning a Trading Strategy](../concepts/strategy-tuning.md) — what the
  objective should return when the metric is a Sharpe ratio rather than a loss
