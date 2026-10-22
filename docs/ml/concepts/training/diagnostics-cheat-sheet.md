---
tags:
  - testing
---

# Training Diagnostics — Cheat Sheet

Every probe from [Training Diagnostics](training-diagnostics.md), grouped by the
quantity you are reading rather than by the stage you are in. Each section gives
the healthy value first, then a table of abnormal readings and what each one
implies.

!!! warning "Orders of magnitude, not thresholds"
    No number here is a limit to assert on. Compare layers against each other
    first and against the figure second — a reading that is alarming in one
    network is routine in another ten times deeper.

## Triage

The symptom you notice first is the loss curve; it only tells you which probe to
open next.

```text
Loss curve looks wrong
│
├─ already wrong at step 0 (≠ ln(C))
│    └──► head, reduction, or label bug — not a training problem yet
│
├─ rises or spikes on many steps
│    └─ gradient norm, step to step
│         └─ large and erratic ──► learning rate too high
│
├─ flat, pinned just under ln(C)
│    └─ update:param ratio + activation std
│         ├─ ratio ≥ 1e-2, std inflating ──► learning rate too high
│         └─ ratio ~1e-3, std healthy ────► no signal in the data
│
├─ falls, then plateaus well above 0
│    └─ overfit 2–8 examples
│         ├─ reaches ~0 ──► capacity is fine; the gap is stage 4's problem
│         └─ plateaus ───► bug in model, loss, or label alignment
│
└─ goes to nan
     └─ activation std with depth
          └─ growing layer by layer ──► activations inflating
```

Once a per-layer sweep shows one layer out of line with its neighbours, the
question changes from *what* is wrong to *where*:

```text
Reading is localised to one layer
│
├─ gradient norm ≫ neighbours ──► its init or normalisation, or an
│                                 outlier batch
├─ gradient norm ≪ neighbours, and the layer is early
│    └──► vanishing chain upstream — read activation std above it
├─ update:param ratio ≤ 1e-4 here only ──► frozen: dead ReLU or
│                                          saturated tanh
└─ activation std ≫ neighbours ──► inflation starts here; clip or
                                   renormalise at this layer
```

## Loss

**Healthy:** starts at ≈ `ln(C)` for a softmax over `C` classes, then falls
steadily with mild noise.

| Reading | What it implies |
|---|---|
| Value at init ≠ `ln(C)` | Head, reduction, or labels are wrong — known before you waste a run |
| Rises on many steps | Learning rate above the stable region — a dynamics failure |
| Smooth and pinned just under `ln(C)` | No signal reaching the loss — features, pipeline, or leak-free-by-accident inputs |

## Gradient norm

**Healthy:** same order of magnitude across layers; steady and slowly decaying
step to step.

| Reading | What it implies |
|---|---|
| Monotone decay from output back to input | Vanishing gradient — depth, activation choice, or init; early layers aren't training |
| Spike confined to one layer | Localised explosion — that layer's init or normalisation, or an outlier batch |
| Large and erratic step to step | Learning rate too high; loudest in the *variance*, not the mean |

## `total_norm` from `clip_grad_norm_`

```python
from torch.nn.utils import clip_grad_norm_

total_norm = clip_grad_norm_(model.parameters(), max_norm=1.0)  # pre-clip value
```

**Healthy:** near `max_norm`, occasionally clipped.

| Reading | What it implies |
|---|---|
| Far below `max_norm` every step | Clipping is inert — it is not protecting you from anything |
| Above `max_norm` on most steps | The threshold, not the optimiser, sets your effective step size |

## Update:param ratio

**Healthy:** ~`1e-3`, at every layer.

| Reading | What it implies |
|---|---|
| ≥ `1e-2` | The step overwrites the weight — learning rate too high for that layer |
| ≤ `1e-4` | Layer effectively frozen — rate too low, or gradient isn't reaching it |

## Activation statistics

**Healthy:** std roughly constant with depth, `tanh` mean well inside ±1,
Rectified Linear Unit (ReLU) dead fraction modest and stable.

| Reading | What it implies |
|---|---|
| Std shrinking layer by layer | Signal dying forward; the gradient will vanish backward |
| Std growing layer by layer | Activations inflating — usually ends in `nan` |
| `tanh` mean pinned at ±1, std ≈ 1 | Units sit in the flat region; local gradient ≈ 0 |
| 95%+ of ReLU activations exactly 0 | Layer has stopped contributing — often the residue of an earlier rate spike |

## One-shot structural tests

These pass or fail rather than trend, so run them once at
[stage 2](training-diagnostics.md#the-stage-2-checks) instead of logging them
every step.

| Test | Pass | Fail means |
|---|---|---|
| Zero the inputs and train | Performance degrades badly | The model isn't using the input — see [Data Leakage](../validation/data-leakage.md) |
| Overfit 2–8 examples | Loss → ~0 | Bug in model, loss, or label alignment — capacity is not the problem |
| Per-example gradient isolation | Non-zero only on example *i* | Batch-dimension mixing or a backwards-in-time leak |

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

- [Training Diagnostics](training-diagnostics.md) — where each of these probes
  comes from, how to instrument it, and the six-stage recipe around it
- [Gradient Descent](gradient-descent.md) — why the learning rate has a stable
  region at all
- [Learning Rate Range Test](lr-range-test.md) — locating the edges of that
  region in one run
- [Module Inspection](../../pytorch/module-inspection.md#forward-hooks) — the hook
  mechanics behind the activation readings
- [Optuna — Diverged Trials](../../experiments/optuna-divergence.md#measuring-divergence)
  — turning these readings into an automatic stop inside a hyperparameter search
