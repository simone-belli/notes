---
tags:
  - testing
---

# Training Diagnostics

A loss curve is one scalar per epoch — a projection of a system with millions of
degrees of freedom onto a single line. Many different internal states produce the
same flat curve, so the curve alone cannot tell you *which* pathology you have.
The quantities that can are per-layer (which part is sick) and per-step (is it
drifting or oscillating).

The reference is Andrej Karpathy's [A Recipe for Training Neural
Networks](https://karpathy.github.io/2019/04/25/recipe/) (2019).

## Why the discipline is needed

Two claims drive the whole recipe:

- **Neural nets are a leaky abstraction.** "Backprop + SGD does not magically
  make your network work." Stochastic Gradient Descent (SGD) and batch
  normalisation are numerical methods with preconditions; violate them and they
  underperform rather than raise.
- **Training fails silently.** Flipped labels, an off-by-one in an
  autoregressive model, clipping the *loss* instead of the *gradients*,
  mismatched normalisation statistics between splits — every one of these still
  trains, and the loss still falls. You just land a few points worse with
  nothing to tell you.

!!! warning "The asymmetry"
    In normal software, no error is weak evidence of correctness. In training it
    is almost none. A run that completes with a plausible curve tells you little.

## The six stages

Strict ordering — never advance while the previous stage is unverified, so that
the number of untested assumptions stays small enough to localise a failure.

1. **Become one with the data.** No code. Scan thousands of examples for
   duplicates, corruption, label noise, imbalance.
2. **Skeleton + dumb baselines.** Full pipeline end-to-end with a model too
   simple to be wrong. You are testing plumbing, not modelling.
3. **Overfit.** Drive *training* loss down hard; ignore validation. Proves the
   architecture can represent the task.
4. **Regularise.** Trade training accuracy for validation accuracy.
5. **Tune.** Hyperparameter search.
6. **Squeeze.** Ensembles, and train longer than feels necessary.

Stage-3 rules worth keeping: copy the simplest architecture from a related paper
("don't be a hero"), Adam at `3e-4` is the forgiving default, add one feature at
a time, and **do not trust learning-rate decay defaults** — a schedule tuned to
another dataset's epoch count can drive the rate to ~0 early. See
[Learning Rate Schedulers](../pytorch/lr-schedulers.md).

Stage-4 order of reliability: more data ≫ augmentation > pretraining > smaller
input dimensionality > smaller model > dropout / weight decay / early stopping.

## The stage-2 checks

- **Verify the loss at init.** Softmax over `C` classes starts at `-log(1/C)` =
  `ln(C)`. A different value means the head, reduction, or labels are wrong —
  known before you waste a run.
- **Init the final-layer bias.** Regressing a mean-50 target? Set the output bias
  to 50. At a 1:10 class ratio, set the logit bias to predict 0.1. Otherwise the
  first steps just learn the bias, producing a hockey stick that looks like
  learning.
- **Input-independent baseline.** Zero the inputs and train; performance *must*
  degrade. If it doesn't, the model isn't using the input — see
  [Data Leakage](data-leakage.md).
- **Overfit one batch.** Two to eight examples, loss to ~0. A model that can't
  memorise two examples has a bug that more data will never fix.
- **Visualise immediately before `model(x)`.** Decode the actual tensor going in
  — "the only source of truth" for preprocessing and augmentation bugs.
- **Use backprop to chart dependencies.** Set the loss to the sum of example
  *i*'s outputs, backprop to the input, and assert the gradient is non-zero
  **only** on example *i*. Catches batch-dimension mixing and backwards-in-time
  leaks; nothing else finds these.
- **Fix the seed** so two runs are comparable — see
  [Reproducibility and Seeding](reproducibility.md).

## Quantities to log every step

### Gradient norm, per layer

Raw gradients exist only between `backward()` and `step()`:

```python
import torch

# after loss.backward(), before optimizer.step()
for name, p in model.named_parameters():
    if p.grad is not None:
        print(name, p.grad.norm().item())
```

Monotone decay from output back to input is a vanishing gradient; a spike in one
layer localises an explosion.

### What `clip_grad_norm_` returns

It returns the total norm **before** clipping — free instrumentation that most
code discards:

```python
from torch.nn.utils import clip_grad_norm_

loss.backward()
total_norm = clip_grad_norm_(model.parameters(), max_norm=1.0)  # pre-clip value
optimizer.step()
```

- `total_norm` far below `max_norm` → clipping is inert; it is not protecting you.
- `total_norm` above `max_norm` on most steps → you are clipping constantly, so
  the threshold rather than the optimiser is setting your effective step size.
- `max_norm=float("inf")` clips nothing and makes the call a pure measurement.

### Update-to-parameter ratio

Gradient norm and learning rate are meaningless alone; what matters is the step
size relative to the weights it moves.

```python
ratio = (lr * p.grad.norm() / p.norm()).item()   # target ~1e-3
```

Above ~`1e-2` the step overwrites the weight; below ~`1e-4` the layer is frozen.
Being scale-free, it compares across layers and models where a raw norm can't.

### Activation statistics

A forward hook reads any module's output without editing the model (mechanics
and handle lifetime in [Modules](../pytorch/modules.md#forward-hooks)):

```python
def stats_hook(module, inputs, output):
    print(module.__class__.__name__, output.mean().item(), output.std().item())

handle = model.layer3.register_forward_hook(stats_hook)
# ... forward passes ...
handle.remove()
```

- **Std shrinking layer by layer** — signal dying forward; gradient will vanish
  backward.
- **Std growing layer by layer** — activations inflating; usually ends in `nan`.
- **Saturation** — for `tanh`, std near 1.0 with the mean pinned at ±1 means the
  units sit in the flat region. For a Rectified Linear Unit (ReLU), track the
  **dead fraction** (activations at exactly 0); a layer 95%+ dead has stopped
  contributing.

!!! tip "Instrument a debug run, not the production loop"
    Hooks fire on every forward pass and `.item()` forces a device
    synchronisation. Read the numbers on a short run, then `remove()` the handles.

## Cheat sheet

Every probe on this page, with the reading that clears it and the reading that
doesn't. "Bad" values are orders of magnitude, not thresholds — compare layers
against each other before comparing against the number.

| Quantity | Healthy | Unhealthy | What the bad reading implies |
|---|---|---|---|
| Loss at init (softmax, `C` classes) | ≈ `ln(C)` | anything else | Head, reduction, or labels are wrong — fix before spending a run |
| Loss trajectory | falls steadily, mild noise | rises on many steps | Learning rate above the stable region — a dynamics failure |
| Loss trajectory | falls steadily, mild noise | smooth and pinned just under `ln(C)` | No signal reaching the loss — features, pipeline, or leak-free-by-accident inputs |
| Gradient norm, per layer | same order of magnitude across layers | monotone decay from output back to input | Vanishing gradient — depth, activation choice, or init; early layers aren't training |
| Gradient norm, per layer | same order of magnitude across layers | spike confined to one layer | Localised explosion — that layer's init or normalisation, or an outlier batch |
| Gradient norm, step to step | steady, slowly decaying | large and erratic | Learning rate too high; loudest in the *variance*, not the mean |
| `total_norm` from `clip_grad_norm_` | near `max_norm`, occasionally clipped | far below `max_norm` every step | Clipping is inert — it is not protecting you from anything |
| `total_norm` from `clip_grad_norm_` | near `max_norm`, occasionally clipped | above `max_norm` on most steps | The threshold, not the optimiser, sets your effective step size |
| Update:param ratio | ~`1e-3` | ≥ `1e-2` | The step overwrites the weight — learning rate too high for that layer |
| Update:param ratio | ~`1e-3` | ≤ `1e-4` | Layer effectively frozen — rate too low, or gradient isn't reaching it |
| Activation std, per layer | roughly constant with depth | shrinking layer by layer | Signal dying forward; the gradient will vanish backward |
| Activation std, per layer | roughly constant with depth | growing layer by layer | Activations inflating — usually ends in `nan` |
| `tanh` saturation | mean well inside ±1 | mean pinned at ±1, std ≈ 1 | Units sit in the flat region; local gradient ≈ 0 |
| ReLU dead fraction | modest and stable | 95%+ of activations exactly 0 | Layer has stopped contributing — often the residue of an earlier rate spike |
| Zeroed-input baseline | performance degrades badly | performance barely changes | The model isn't using the input — see [Data Leakage](data-leakage.md) |
| Overfit 2–8 examples | loss → ~0 | plateaus well above 0 | Bug in model, loss, or label alignment — capacity is not the problem |
| Per-example gradient isolation | non-zero only on example *i* | non-zero on other examples | Batch-dimension mixing or a backwards-in-time leak |

!!! warning "Read the pair, not the cell"
    No single row is diagnostic. A small gradient norm is healthy next to a
    ~`1e-3` update ratio and damning next to a `1e-5` one — the norm is scaled by
    the weights it moves, so only the ratio is comparable across layers.

## Differential diagnosis

Two runs, both with a flat-looking loss curve:

| Quantity | Learning rate too high | No signal in the data |
|---|---|---|
| Loss trajectory | non-monotonic — rises on many steps | smooth, pinned just under `ln(C)` |
| Gradient norm | large and **erratic** step to step | small, decaying to a steady floor |
| Update:param ratio | `1e-2` and up | `1e-4` and below |
| Activation std | inflating or saturated | stable and healthy |

!!! note "The mental model"
    A high learning rate is a **dynamics** failure — loud in the *variance* of
    every per-step quantity. No signal is an **information** failure — eerily
    quiet, because the optimiser is behaving perfectly and gradients are small
    only because there is nothing left to learn.

The decisive test when traces are ambiguous is to **overfit one batch with a
known-sane optimiser** (Adam at `3e-4`), which removes the learning rate from the
hypothesis space:

- **Memorises the batch** → optimiser and architecture are fine; the features
  don't predict the target. A model *can* memorise random labels — memorisation
  proves capacity, not signal.
- **Fails on a handful of examples** → the bug is in the model, loss, or label
  alignment. Return to stage 2.

## Related

- [Gradient Descent](gradient-descent.md) — why the learning rate has a stable
  region at all
- [Model Validation](model-validation.md) — what stages 4–5 tune against
- [The Training Loop](../pytorch/training-loop.md) — where these probes attach
