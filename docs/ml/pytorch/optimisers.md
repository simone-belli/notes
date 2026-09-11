---
tags:
  - performance
---

# Optimisers

An optimiser is **a list of tensor references, a dict of hyperparameters, and a lazily-built
dict of per-parameter state**. `step()` walks that list, reads `p.grad`, and writes `p` in
place. It has never heard of your model, your loss, or the autograd graph.

```python
import torch

optimizer = torch.optim.SGD(model.parameters(), lr=0.1, momentum=0.9)
```

| Attribute | What it is |
|---|---|
| `optimizer.param_groups` | list of **dicts**; each has `"params"` plus every hyperparameter |
| `optimizer.state` | dict keyed by the **`Parameter` object itself** → its private state |
| `optimizer.defaults` | the hyperparameters as constructed |

`model.parameters()` is a generator of **live references**, and the optimiser stored those exact
objects — `all(a is b for a, b in zip(optimizer.param_groups[0]["params"], model.parameters()))`
is `True`. There is no copy and no back-pointer to the model. That single fact explains
everything below.

!!! note "`state` is empty until the first `step()`"
    `len(optimizer.state)` is `0` right after construction. Momentum buffers and Adam's moment
    estimates are allocated on first use, on whatever device and dtype the parameter has *at
    that moment*.

## What `step()` walks

```python
@torch.no_grad()
def step(self):
    for group in self.param_groups:          # 1. each group
        for p in group["params"]:            # 2. each parameter in it
            if p.grad is None:               # 3. skip untouched params
                continue
            state = self.state[p]            # 4. lazily initialised, first time only
            update(p, p.grad, state, group)  # 5. read grad, write p in place
```

Five consequences, and they cover most optimiser bugs:

- **Traversal is over `param_groups`, not the model.** Anything not in the list is invisible;
  anything in it is updated whether or not it's still attached to the model.
- **Hyperparameters are re-read from `group` every step** — exactly the hook a
  [scheduler](lr-schedulers.md) uses when it writes `group["lr"]`.
- **`p.grad is None` is skipped silently.** Frozen parameters in the optimiser raise nothing
  and cost nothing — so "the optimiser accepted it" proves nothing about what trains.
- **The update is in-place under `no_grad`**; parameters stay leaves with `requires_grad=True`.
- **`step()` never clears `.grad`** — that's [`zero_grad()`](autograd.md#grad-accumulates),
  separate because gradient accumulation exists.

`step(closure)` takes an optional callable that re-evaluates the loss. Only `LBFGS` and friends
need it.

## SGD

```python
torch.optim.SGD(params, lr, momentum=0, weight_decay=0, nesterov=False)
```

With `momentum=0`, SGD is genuinely stateless — `optimizer.state` stays `{}`. The recurrence (the
maths is in [Gradient Descent](../concepts/gradient-descent.md)):

```
g   ← grad + weight_decay · p        # L2 folded into the gradient
buf ← g  (first step)  |  momentum · buf + g  (thereafter)
p   ← p − lr · buf
```

- `lr` is **outside** the buffer — `buf` accumulates raw gradients. The textbook formulation
  folds `lr` in, so the two behave differently when a scheduler changes `lr` mid-run.
- No bias correction: `buf` starts at `g`, so the first steps are systematically smaller than
  steady-state ones.
- Momentum is a low-pass filter on the gradient. At `0.9` the effective step is roughly `10×`
  the raw gradient once the direction is consistent, which is why the usable `lr` for momentum
  SGD sits about an order of magnitude below plain SGD's.
- `nesterov=True` evaluates the gradient at the look-ahead point; needs `momentum > 0` and
  `dampening == 0`.

## Adam

```python
torch.optim.Adam(params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8)
```

Two exponential moving averages per parameter — the gradient's mean and its square — with one
divided by the root of the other:

```
m ← β₁·m + (1−β₁)·g                  # first moment: direction
v ← β₂·v + (1−β₂)·g²                 # second moment: scale
m̂ ← m / (1 − β₁ᵗ)    v̂ ← v / (1 − β₂ᵗ)     # bias correction, t = step count
p ← p − lr · m̂ / (√v̂ + ε)
```

!!! tip "The division makes the step size ≈ `lr` regardless of gradient magnitude"
    If a coordinate's gradients are consistently tiny, `√v̂` is tiny too and the ratio is ~1.
    Adam is nearly scale-invariant per coordinate, which is why one `lr` works across
    architectures and why anything with embeddings or attention uses it.

Bias correction exists because `m` and `v` start at zero; with `β₂=0.999`, `v` needs ~1000 steps
to forget that. It repairs the *expectation* but not the *variance* — early `v̂` is estimated
from few samples and is noisy, which is the real reason Adam wants [learning-rate
warmup](lr-schedulers.md).

!!! warning "Adam costs 3× the parameter memory"
    Measured on `nn.Linear(1000, 1000)`: 1,001,000 parameter elements against 2,002,000 elements
    of state — exactly two extra full-size tensors per parameter. With gradients too, training
    holds ~4× the weight memory versus ~2× for plain SGD.

## Adam vs AdamW

The difference is only *where* the decay term enters:

- **Adam** adds `weight_decay · p` to the gradient, so it then goes through the `/√v̂`
  normalisation like everything else.
- **AdamW** leaves the gradient alone and scales the parameter by `(1 − lr · weight_decay)`.

One step with `lr=0.1`, `weight_decay=0.5`, and the gradient set to exactly zero, on
`p = [1.0, 2.0, 4.0]`:

```
Adam   → [0.900, 1.900, 3.900]      # every coordinate moves by the same 0.1
AdamW  → [0.950, 1.900, 3.800]      # every coordinate scales by 0.95
```

AdamW does what "weight decay" means — shrink proportionally. Adam's L2 term gets divided by
that coordinate's gradient history, coupling regularisation strength to gradient statistics.

**Use `AdamW` whenever `weight_decay > 0`.** At `weight_decay=0` the two are identical, so
there's no reason to reach for `Adam` at all. AdamW's effective regularisation scales with `lr`,
so retuning the rate retunes the decay.

## Choosing

| | SGD + momentum | AdamW |
|---|---|---|
| State per parameter | 1 tensor (0 without momentum) | 2 tensors |
| Sensitivity to `lr` | high — needs tuning and a schedule | low — `1e-3`/`3e-4` usually works |
| Convnets | best final accuracy, given a good schedule | slightly worse, far less tuning |
| Transformers, embeddings | poor | the only practical choice |
| Typical `lr` | `0.1`, momentum `0.9` | `1e-3`; `1e-4`–`3e-4` fine-tuning |

AdamW to get something working; SGD+momentum when chasing the last half-point on a vision
benchmark with budget to tune.

## Parameter groups

Pass dicts instead of a flat iterable — each becomes a group with its own hyperparameters, and
missing keys fall back to the constructor defaults:

```python
optimizer = torch.optim.AdamW([
    {"params": model.backbone.parameters(), "lr": 1e-5},
    {"params": model.head.parameters(),     "lr": 1e-3},
], weight_decay=0.01)                        # applies to both
```

This drives discriminative fine-tuning and the standard "no weight decay on biases and norm
parameters" recipe. `add_param_group({...})` appends later; unspecified keys inherit from
`defaults`, not from any existing group.

A parameter may appear in **at most one** group — duplicates raise `ValueError: some parameters
appear in more than one parameter group`, which usefully catches passing `model.parameters()`
alongside a submodule's.

## The reference relationship

The question is always: *is the optimiser still holding the same object?*

### `model.to(device)` does not break it

`nn.Module.to()` swaps `param.data` in place, keeping the [`Parameter`](modules.md) object
identical — so `param_groups` stays valid and picks up the new device. Building the optimiser
before the move and moving before the first step works fine, because state is allocated lazily.

What breaks is moving **after** state exists: momentum buffers and moment estimates are *not*
moved by `model.to()`, leaving them stale on the old device. Across devices that's a
mid-training device-mismatch error; across dtypes it silently keeps computing in the old
precision. Move first, then train.

### Rebinding a layer breaks it, invisibly

```python
optimizer = torch.optim.SGD(model.parameters(), lr=0.5)
model[1] = nn.Linear(3, 2)      # replaced after construction
optimizer.step()                # the new layer never moves
```

The optimiser still holds the *old* layer's tensors. Worse, the counts match — 4 parameters
either side, two of them different objects — so nothing looks wrong and the replaced layer stays
at its initialisation forever. Same for any parameter created after construction. **Re-create
the optimiser whenever the parameter set changes**, accepting that this discards the momentum
buffers.

!!! tip "The two-line check"
    ```python
    opt_params = {id(p) for g in optimizer.param_groups for p in g["params"]}
    missing = [n for n, p in model.named_parameters()
               if p.requires_grad and id(p) not in opt_params]
    ```
    `missing` should be empty. Run it once after building the optimiser — it catches rebinding,
    the [plain-list registration trap](modules.md#the-registration-trap), and forgotten
    submodules in one go.

## State and checkpointing

There's a representation switch: in memory `optimizer.state` is keyed by the `Parameter` object,
but `state_dict()` re-keys it by the parameter's **integer position**, and
`param_groups[i]["params"]` becomes a list of indices:

```python
>>> sd = optimizer.state_dict()
>>> sorted(sd.keys()),  list(sd["state"].keys()),  sd["param_groups"][0]["params"]
(['param_groups', 'state'], [0, 1], [0, 1])
```

Positional keying is what makes checkpoints portable — and it means **`load_state_dict` matches
by position, never by name**:

- A different parameter *count* raises `ValueError: loaded state dict contains a parameter group
  that doesn't match the size of optimizer's group`.
- The same count with **different shapes** loads **silently**. A `(3, 4)` momentum buffer will
  attach to a `(5, 4)` parameter without complaint and fail at the next step.

Checkpoint the optimiser alongside the model — resuming without it restarts Adam's moments from
zero and puts a visible loss spike exactly at the resume point:

```python
torch.save({"model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict()}, path)
```

On resume: build the model, load its weights, build the optimiser from the *restored* model's
parameters, then load the optimiser state.

## Silent failure checklist

| Symptom | Cause |
|---|---|
| One layer never trains, no error | layer rebound after the optimiser was built |
| Nothing trains, loss exactly flat | `step()` missing, or `parameters()` from the wrong model |
| Loss spikes exactly at resume | optimiser state not checkpointed |
| Device mismatch after several steps | `model.to()` called after state was allocated |
| Weight decay seems weak or oddly targeted | `Adam` instead of `AdamW` |
| Out of memory switching SGD → Adam | two extra full-size tensors per parameter |
| `some parameters appear in more than one parameter group` | `model.parameters()` passed alongside a submodule's |
| Resumed run diverges, no error | state dict of matching length but mismatched shapes |

## Related

- [Gradient Descent](../concepts/gradient-descent.md) — the library-agnostic derivations behind
  these update rules
- [The Training Loop](training-loop.md) — where `zero_grad()` and `step()` sit
- [Learning Rate Schedulers](lr-schedulers.md) — the object that rewrites `group["lr"]`
- [Autograd](autograd.md) — what fills the `.grad` that `step()` reads
- [Modules](modules.md) — where `parameters()` comes from
