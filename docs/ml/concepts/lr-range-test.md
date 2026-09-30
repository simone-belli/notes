---
tags:
  - testing
---

# Learning Rate Range Test

One short run that *measures* the usable band of learning rates instead of
guessing it. Introduced in Leslie Smith's [Cyclical Learning Rates for Training
Neural Networks](https://arxiv.org/abs/1506.01186) (2015) as the way to pick the
two bounds a cyclical schedule needs — but the measurement stands alone, and is
the cheapest way to set a base rate for any schedule.

The premise: a network has a **band** of learning rates that train it, spanning
one to two orders of magnitude. Below the band nothing moves; above it the loss
diverges. A single linear ramp finds both edges in a few epochs, for the price
of one run.

## The procedure

1. Snapshot the model and optimiser state — the test ends in the divergent
   region and leaves the weights damaged.
2. Pick a ramp from a rate far too small to a rate far too large (Smith's
   Canadian Institute For Advanced Research 10-class dataset (CIFAR-10) example:
   $0 \to 0.02$ over 8 epochs).
3. Train, raising the rate **every iteration**, and record accuracy (Smith) or
   the batch training loss (the modern variant) against the rate.
4. Read the two edges off the curve; restore the snapshot.

The ramp itself is linear in Smith's formulation — over $N$ iterations:

$$
\eta_t = \eta_{\text{start}} + \frac{t}{N}\left(\eta_{\text{end}} - \eta_{\text{start}}\right)
$$

Implementations that sweep several orders of magnitude use a geometric ramp
instead, so each decade gets equal resolution on a log axis:

$$
\eta_t = \eta_{\text{start}} \left( \frac{\eta_{\text{end}}}{\eta_{\text{start}}} \right)^{t/N}
$$

```python
import copy
import torch
from torch.optim.lr_scheduler import LambdaLR

eta_start, eta_end, n_iter = 1e-7, 1.0, 500
state = copy.deepcopy(model.state_dict())                      # step 1

optimizer = torch.optim.SGD(model.parameters(), lr=eta_start)
gamma = (eta_end / eta_start) ** (1 / n_iter)
scheduler = LambdaLR(optimizer, lambda t: gamma**t)            # × the base rate

history, best = [], float("inf")
for t, (x, y) in enumerate(loader):
    loss = criterion(model(x), y)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    history.append((scheduler.get_last_lr()[0], loss.item()))
    best = min(best, loss.item())
    scheduler.step()                          # per BATCH, not per epoch
    if t == n_iter or loss.item() > 4 * best:                  # step 3
        break

model.load_state_dict(state)                                   # step 4
```

## Reading the curve

Smith's rule, stated on accuracy: note the rate where accuracy **starts to
increase**, and the rate where it **slows, becomes ragged, or falls**. Those two
are the bounds.

| Region | Accuracy curve | Loss curve | Meaning |
|---|---|---|---|
| Too low | flat | flat | Steps too small to make progress in the budget |
| Rising | climbing | falling steeply | The usable band — $\eta_{\min}$ sits at its start |
| Ragged | noisy, plateauing | flattening, noisy | At the edge of stability — $\eta_{\max}$ sits here |
| Divergent | collapses | shoots up | Past the edge; weights are being destroyed |

On CIFAR-10 Smith read $\eta_{\min} = 0.001$ and $\eta_{\max} = 0.006$ off such
a plot. When only one bound is wanted, the paper's rule of thumb sets the other
from it:

$$
\eta_{\min} \approx \frac{\eta_{\max}}{3} \;\text{ to }\; \frac{\eta_{\max}}{4}
$$

!!! warning "The minimum of the loss curve is not the answer"
    The loss keeps falling until the run is already unstable, so its lowest
    point sits *inside* the divergent region — training there diverges. Take a
    rate from where the curve is **steepest**, roughly an order of magnitude
    below the blow-up. Plot a smoothed loss (an exponential moving average over
    batches); the raw per-batch curve is too noisy to locate anything on.

!!! tip "One run, not a search"
    A grid search over learning rates costs one full run per candidate and
    reports a single number each. The range test costs one *partial* run and
    returns the whole curve — which is why it belongs in stage 3 of the
    [training-diagnostics](training-diagnostics.md#the-six-stages) recipe,
    before any hyperparameter search.

## What the bounds are for

Smith's actual proposal is that the rate should **cycle** between the two
bounds rather than decay monotonically. The triangular policy, with half-cycle
length (*step size*) $s$ iterations:

$$
\begin{aligned}
c &= \left\lfloor 1 + \frac{t}{2s} \right\rfloor \\
x &= \left| \frac{t}{s} - 2c + 1 \right| \\
\eta_t &= \eta_{\min} + (\eta_{\max} - \eta_{\min}) \max(0,\, 1 - x)
\end{aligned}
$$

- **`triangular2`** halves the amplitude each cycle, scaling it by $2^{-(c-1)}$.
- **`exp_range`** decays it continuously, by $\gamma^{t}$.
- $s$ should be **2–10 times the iterations in one epoch**; stop training at the
  end of a cycle, where the rate is back at $\eta_{\min}$.

```python
from torch.optim.lr_scheduler import CyclicLR

scheduler = CyclicLR(optimizer, base_lr=1e-3, max_lr=6e-3,
                     step_size_up=4 * len(loader), mode="triangular")
```

!!! note "Why raising the rate helps at all"
    Increasing the learning rate has a short-term negative and a long-term
    positive effect. The loss surface's obstacles are saddle-point plateaus
    rather than local minima, and a plateau has small gradients by definition —
    so a small rate crawls across it. A period of large steps traverses it
    quickly, and the accuracy lost on the way up is recovered on the way down.

## Caveats

- **It is batch-size and architecture specific.** The band moves with batch
  size, model width, [normalisation layers](normalisation.md), and optimiser.
  Re-run the test when any of those change; a rate borrowed across
  configurations is the thing the test exists to replace.
- **Adam narrows what you learn.** Adam's per-coordinate rescaling already
  absorbs a lot of scale, flattening the curve and making the edges less sharp
  than with Stochastic Gradient Descent (SGD). The test still works; the plateau
  is just wider.
- **Warmup and the ramp are not the same thing.** The ramp is discarded
  measurement; a [warmup schedule](../pytorch/lr-schedulers.md#composing-warmup-with-decay)
  is part of the real run.
- **Restore the weights.** The run ends past the edge of stability. Continuing
  from it — a mistake easily made when the test is a cell in a notebook — trains
  a model the test already wrecked.

## Related

- [Learning Rate Schedulers](../pytorch/lr-schedulers.md) — `CyclicLR`,
  `OneCycleLR`, and the object the test's output is fed to
- [Gradient Descent](gradient-descent.md#why-the-rate-must-decay) — why a
  stable region exists, and why the rate must come down to converge
- [Training Diagnostics](training-diagnostics.md) — the per-step quantities that
  distinguish a too-high rate from no signal
- [Optuna](../experiments/optuna.md) — the search the test replaces for this one
  hyperparameter
