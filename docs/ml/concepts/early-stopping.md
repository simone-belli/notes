# Early Stopping

Stop a run once its validation metric has stopped improving, and keep the weights
from the epoch that was best. Those are two separate deliverables — a *stopping
time* and a *model selection* — and code that implements only the first ships
weights that are `patience` epochs worse than the best the run ever saw.

Record $v_1, v_2, \dots$ on a held-out validation split. With patience $p$, stop
at the first epoch $t$ satisfying the first condition and return the weights from
the second:

$$
t - \arg\min_{s \le t} v_s \ge p,
\qquad
t^\star = \arg\min_{s} v_s
$$

## Why it regularises

The optimisation path is a sequence of hypotheses of *increasing effective
capacity*: early epochs have only had time to fit the dominant, high-signal
directions, later ones have time to fit noise. Epoch count is a capacity dial,
and early stopping tunes it.

For a quadratic loss with Hessian eigenvalues $\lambda_i$, gradient descent at
rate $\eta$ from $\theta_0 = 0$ shrinks the component along eigenvector $i$ by a
factor that matches ridge regression's shrinkage with penalty $\alpha$:

$$
\begin{aligned}
\text{after } t \text{ steps:} \quad & 1 - (1 - \eta\lambda_i)^t \\[2pt]
\text{ridge:} \quad & \frac{\lambda_i}{\lambda_i + \alpha} \\[4pt]
\text{the two agree when} \quad & \alpha \approx \frac{1}{\eta t}
\end{aligned}
$$

- **Stopping at step $t$ is approximately $L^2$ regularisation** with
  $\alpha = 1/(\eta t)$ — both leave low-curvature directions unfit. Training
  longer means a weaker penalty.
- Outside the quadratic case the intuition survives as a budget on distance
  travelled from initialisation, since
  $\lVert \theta_t - \theta_0 \rVert \le \eta \sum_s \lVert g_s \rVert$ — a norm
  constraint by another name.
- It is the **cheapest regulariser available**: weight decay costs a full run per
  candidate $\alpha$, while early stopping reads its hyperparameter off the one
  run you were doing anyway.

## The knobs

- **Monitored quantity and direction** — validation loss (minimise) or a task
  metric (maximise). It has to be the validation split; see
  [Model Validation](model-validation.md).
- **Patience $p$** — epochs of no improvement tolerated. This is a noise filter,
  so scale it to how noisy the validation estimate is; $p = 1$ stops on a
  fluctuation.
- **`min_delta`** — the margin that counts as an improvement, so the run doesn't
  drift forever on $10^{-7}$ gains.
- **Minimum epochs** — don't let the first noisy epochs trigger a stop, which
  matters most with a warmup schedule whose early epochs are *meant* to be bad.
- **Evaluation interval** — per epoch by default; every $N$ steps when epochs are
  long.

## Keeping the best weights

`torch.nn.Module.state_dict()` returns **references** to the live parameter
tensors, so a snapshot has to be copied:

```python
import copy

PATIENCE, MIN_DELTA, MAX_EPOCHS = 10, 1e-4, 500
best, best_state, bad = float("inf"), None, 0

for epoch in range(MAX_EPOCHS):
    train_one_epoch(model, optimizer)
    val = validate(model)

    if val < best - MIN_DELTA:
        best, bad = val, 0
        best_state = copy.deepcopy(model.state_dict())
    else:
        bad += 1
        if bad >= PATIENCE:
            break

model.load_state_dict(best_state)       # the whole point
```

!!! warning "`best_state = model.state_dict()` saves nothing"
    Without the copy, the optimiser mutates those tensors in place on the next
    step and the "best" snapshot silently tracks the current weights. On a large
    model, copy to host memory (`v.detach().cpu().clone()`) or to disk rather than
    holding a second set of parameters on the device.

## With a learning-rate scheduler

`ReduceLROnPlateau` watches the same plateau and has its own `patience`. If the
early-stopping patience is not comfortably larger, the run stops *before* the
rate drop that would have produced a fresh improvement — see
[Learning Rate Schedulers](../pytorch/lr-schedulers.md#reducelronplateau). Budget
the scheduler's patience plus a few epochs, times the number of drops you want to
allow.

## Early stopping is not pruning

| | Early stopping | Pruning |
|---|---|---|
| Scope | one fit | across trials |
| Question | has *this* run stopped improving? | is *this config* losing to the others? |
| Criterion | absolute, self-referential | comparative, against a pool |
| Decides | the epoch count | whether to abandon the configuration |

The two compose — early-stop inside the fit, prune across trials — and because
Optuna's `step` is a single integer they *must* be kept on separate axes. See
[Optuna — Pruning](../experiments/optuna-pruning.md#what-step-should-count).

## With cross-validation

Every fold stops at its own epoch, and the final refit on all the data has no
validation split left to stop on. The usual resolution is to refit for the
**mean (or median) best epoch across folds** with no stopping rule — the
`best_iteration` pattern from gradient-boosting workflows.

!!! note "The stopping epoch is a fitted hyperparameter"
    $\min_s v_s$ over a noisy curve is optimistically biased — the same
    selection-bias-on-the-extremum effect as reporting a search's best value as
    an expected result. Validation loss at $t^\star$ is therefore not a
    generalisation estimate; an honest number needs a test split you never
    touched.

## When the premise fails

- **Double descent.** The U-shaped validation curve is not universal:
  heavily overparameterised models can get worse, then better again past the
  interpolation threshold, and a patient stop lands on the first, worse minimum.
- **Compute-bound training.** Single-pass, budget-limited runs are still
  improving when the budget runs out, so there is no plateau to detect.
- **Tiny validation sets.** With a few hundred examples the $\arg\min$ over a
  hundred epochs is substantially luck — you are selecting on the standard error
  of your own estimate.

!!! warning "Chronological order is not optional"
    Early stopping on a shuffled validation split of a time series is a
    look-ahead leak: the stopping decision uses information from after the
    training window. The validation block must sit later in time — see
    [Time-Series Validation](time-series-validation.md).

## Related

- [Model Validation](model-validation.md) — the split that early stopping
  consumes, and why selecting on it costs you an unbiased estimate
- [Training Diagnostics](training-diagnostics.md) — the stage-4 regularisers
  early stopping sits among, and the probes that say whether a plateau is real
- [Learning Rate Schedulers](../pytorch/lr-schedulers.md) — the other consumer of
  a validation plateau, and the patience it needs
- [Learning Rate Range Test](lr-range-test.md) — the stopping rule for a
  deliberately diverging run, by contrast
- [The Training Loop](../pytorch/training-loop.md) — where the validation pass
  and the snapshot attach
- [Optuna — Pruning](../experiments/optuna-pruning.md) — abandoning a whole
  configuration rather than a fit
- [Time-Series Validation](time-series-validation.md) — why the validation block
  has to be the later one
