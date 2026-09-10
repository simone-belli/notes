# Learning Rate Schedulers

A scheduler owns exactly one job: **rewrite
`optimizer.param_groups[i]["lr"]` over time**. It never touches parameters or
gradients. Delete it and training still runs — at a constant learning rate.

```python
import torch
from torch.optim.lr_scheduler import CosineAnnealingLR

optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
scheduler = CosineAnnealingLR(optimizer, T_max=n_epochs)

for epoch in range(n_epochs):
    train_one_epoch()
    scheduler.step()          # only effect: a new float in the optimizer
```

## Why decay the rate

- **Early** — large steps cross the flat, badly-scaled regions fast, and the
  step noise keeps the optimizer out of sharp minima.
- **Late** — stochastic gradient descent (SGD) doesn't converge to a point; it
  orbits the minimum in a ball whose radius scales with the learning rate. To
  settle, the radius must shrink.
- **Warmup** is the mirror image: Adam's second-moment estimate is meaningless
  for the first few hundred steps, so full-size updates then can wreck a model
  permanently. Ramp up from ~0, then decay.

!!! note "A scheduler is not what Adam does"
    Adam rescales each coordinate by its own gradient history — *relative*
    scaling across parameters. The `lr` you pass is still a global multiplier,
    and nothing in Adam shrinks it. Warmup + Adam + cosine is standard because
    the two mechanisms are orthogonal.

## Mechanics

Constructing a scheduler already mutates the optimizer: it copies each group's
`lr` into `initial_lr` (the **base** the schedule is relative to), then steps
once to write the step-0 value. Each `step()` increments `last_epoch`, computes
one float per parameter group from `base_lrs`, and writes them in.

- `last_epoch` is a misnomer — it counts `step()` calls, nothing more. The
  class has no idea what an epoch is.
- With several [parameter groups](modules.md), the schedule scales each group's
  own base, so discriminative learning rates keep their ratio for free.
- Read the current value with `scheduler.get_last_lr()` (a list) — not
  `get_lr()`, which is the internal hook and warns.

```python
optimizer.step()      # uses the CURRENT lr
scheduler.step()      # sets the lr for the NEXT optimizer.step()
```

!!! warning "Per-epoch or per-batch is not the scheduler's decision"
    `StepLR`, `MultiStepLR`, `CosineAnnealingLR`, `ReduceLROnPlateau` are
    defined in epochs; `OneCycleLR` and every warmup schedule are defined in
    batches. Step an epoch scheduler inside the batch loop and a cosine meant
    to bottom out at epoch 50 bottoms out during epoch 1 — the rest of the run
    trains at ~0. No error, no warning. Log the learning rate every epoch.

## The schedules

```python
from torch.optim.lr_scheduler import (
    StepLR, MultiStepLR, CosineAnnealingLR, OneCycleLR,
    LinearLR, LambdaLR, SequentialLR, ReduceLROnPlateau,
)

StepLR(optimizer, step_size=30, gamma=0.1)              # ×0.1 every 30 epochs
MultiStepLR(optimizer, milestones=[60, 85], gamma=0.1)  # ×0.1 at 60 and 85
CosineAnnealingLR(optimizer, T_max=n_epochs)            # half-cosine to eta_min
OneCycleLR(optimizer, max_lr=1e-2, total_steps=n_epochs * len(loader))
LinearLR(optimizer, start_factor=0.01, total_iters=500) # warmup ramp
```

| Schedule | Shape | Use when |
|---|---|---|
| `MultiStepLR` | staircase | reproducing older vision recipes; legible curves |
| `ExponentialLR` | `lr *= gamma` each step | short runs only — `gamma` and length interact badly |
| `CosineAnnealingLR` | smooth half-cosine | the modern default, given a known budget |
| `OneCycleLR` | up 30%, then cosine to ~0 | fixed budget, want fewest epochs; step **per batch** |
| `LambdaLR` | any function of step count | anything the library lacks |
| `ReduceLROnPlateau` | reactive | budget unknown, or with early stopping |

- `CosineAnnealingLR`'s `T_max` **must** be the total run length in whatever
  unit you step. Too short and the cosine turns around and climbs back up; too
  long and you never reach the bottom.
- `OneCycleLR` starts at `max_lr / div_factor` (default 25), not `max_lr`, and
  cycles momentum inversely. `total_steps` must be exact — overshoot raises.
- `LambdaLR`'s function returns a **multiplier** on the base rate. The original
  Transformer schedule is one line:
  `lambda s: min((s+1)**-0.5, (s+1) * 4000**-1.5)`.

### Composing warmup with decay

`SequentialLR` runs schedulers one after another, switching at milestones —
this is the ubiquitous "linear warmup then cosine decay", stepped per batch:

```python
warmup = LinearLR(optimizer, start_factor=0.01, total_iters=500)
decay  = CosineAnnealingLR(optimizer, T_max=total_steps - 500)
scheduler = SequentialLR(optimizer, [warmup, decay], milestones=[500])
```

`ChainedScheduler` instead applies them all simultaneously, multiplying their
effects — rarely what you want.

### ReduceLROnPlateau

The only reactive one, and the only one whose `step()` takes an argument:

```python
scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.1, patience=10)

val_loss = validate(model)
scheduler.step(val_loss)     # after validation, with the METRIC
```

- Get `mode` right: `"min"` for loss, `"max"` for accuracy. `mode="min"` on
  accuracy decays the rate every time the model improves.
- It needs no total run length, which is why it pairs with early stopping — but
  it only reacts *after* a plateau has already been wasted.

## Checkpointing

The scheduler carries state (`last_epoch`, `base_lrs`, and the best-metric
counters for `ReduceLROnPlateau`). Omit it from the checkpoint and a resumed
run silently restarts the schedule from the top.

```python
torch.save({"model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict()}, path)
```

On resume, construct the scheduler against **fresh** base rates and then
`load_state_dict` it. Building it after loading the optimizer state captures
the mid-run rate as `initial_lr`, leaving the schedule defined against the
wrong base.

## Silent failure checklist

| Symptom | Usual cause |
|---|---|
| Learning rate ~0 after one epoch | epoch scheduler stepped per batch |
| Learning rate climbs back up late in the run | `T_max` shorter than the run |
| `OneCycleLR` raises after N steps | `total_steps` too small, or stepped per epoch |
| First update full-size despite warmup | `scheduler.step()` before `optimizer.step()` |
| Rate decays whenever the model improves | `ReduceLROnPlateau(mode="min")` on accuracy |
| Resumed run worse than a continuous one | scheduler state not checkpointed |
| Rate never changes | scheduler built on a different optimizer instance |

!!! tip "Second-order gains"
    A good schedule is worth roughly a point of accuracy or a 2× cut in epochs.
    Getting the *base* learning rate right is worth far more — no schedule
    rescues a base rate two orders of magnitude off.

## Related

- [The Training Loop](training-loop.md) — where `scheduler.step()` sits among
  the five statements
- [Modules](modules.md) — `model.parameters()` and the parameter groups a
  schedule scales
- [Optuna](../experiments/optuna.md) — searching over the base learning rate
  the schedule is relative to
