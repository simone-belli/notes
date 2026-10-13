---
tags:
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

## What `step` should count

`step` is just a monotone integer resource counter — nothing ties it to epochs.
The two useful axes buy different things:

- **Epochs** — resource is *training time within one fit*. Pruning asks "will
  this curve get there?"
- **Folds** — resource is *evidence about generalisation*. One report per
  completed fold of a [cross-validation](../scikit-learn/cross-validation.md),
  and pruning asks "is this configuration's mean score going to beat the others?"

Score at the fold level when:

- **There are no epochs.** A `RandomForestRegressor`, a `Ridge`, a support
  vector machine, or any whole `Pipeline` fit has no intermediate curve to
  report. The only partial information that exists is $k$ of $K$ folds done.
- **Fold variance dominates training variance.** On financial series the
  dispersion of Sharpe ratio or information coefficient *across* folds dwarfs
  epoch-to-epoch movement within one. Pruning on epochs there prunes on noise
  while the real uncertainty sits on the axis you aren't measuring.
- **The fits are cheap and the folds are many.** Combinatorial purged
  cross-validation generates $\binom{N}{k}$ paths; that is where the budget
  goes, not inside any one fit.

```python
import numpy as np
import optuna
from sklearn.model_selection import TimeSeriesSplit

def objective(trial: optuna.Trial) -> float:
    model = build(trial)
    scores = []
    for k, (tr, va) in enumerate(TimeSeriesSplit(n_splits=10).split(X)):
        scores.append(fit_and_score(model, X, y, tr, va))
        trial.report(float(np.mean(scores)), k)   # step = fold, running mean
        if trial.should_prune():
            raise optuna.TrialPruned()
    return float(np.mean(scores))
```

- Report the **running mean**, not the individual fold score — the mean is the
  estimator of what you finally return, so it is on the same scale as other
  trials' reports at the same step.
- The running mean after $k$ folds has standard error
  $\operatorname{SE}_k = \sigma_{\text{fold}} / \sqrt{k}$, so early steps are
  genuinely noisy. With $K = 5$ you only get five decision points and cutting at
  $k = 1$ is cutting on one fold; set `n_warmup_steps` to roughly
  $\lfloor K/3 \rfloor$.

!!! warning "Fold $k$ must be the same data in every trial"
    Cross-trial comparison at step $k$ is only meaningful because the splitter is
    deterministic — folds are *not* exchangeable, and in a time-series split the
    early ones are a specific regime, not a random sample. Shuffle the fold order
    per trial and the pruner is comparing different quantities. See
    [Reproducibility and Seeding](../concepts/reproducibility.md).

`WilcoxonPruner` is built for this axis: report per-fold values and it runs a
paired signed-rank test against the best trial. Pairing is what exploits
fold-is-the-same-data, removing fold difficulty as a nuisance term, which makes
it strictly more powerful than comparing running means.

!!! tip "Don't try to nest both axes"
    `step` is one integer, so `(fold, epoch)` has no representation. Either
    flatten it as $k E + e$, or — cleaner — handle epochs with a plain
    early-stopping callback *inside* the fit and let Optuna prune on folds only.
    Early stopping is a within-fit concern and does not need the study.

## When the trial blew up instead

`should_prune()` decides the fate of a trial that is merely *losing*. A trial
whose loss went to not-a-number is a different case: `nan` is a `FAIL`, which
records no observation, leaves the point looking unexplored, and invites the
sampler straight back into the region that broke. The score such a trial should
return instead, and the detectors that catch the blow-up before `nan` does, are
in [Optuna — Diverged Trials](optuna-divergence.md).

## Related

- [Optuna — Diverged Trials](optuna-divergence.md) — the other exit: what to
  return when a trial breaks rather than loses, and how to spot it early
- [Optuna](optuna.md) — define-by-run spaces, the suggest API, and the samplers
  pruning has to cooperate with
- [Optuna — Studies](optuna-studies.md) — the storage backend the pruner reads,
  and `catch=` in context
- [Running Cross-Validation](../scikit-learn/cross-validation.md) — the per-fold
  scores the fold-level axis reports
- [Purged Cross-Validation](../concepts/purged-cross-validation.md) — the
  combinatorial path count that makes folds the expensive axis
