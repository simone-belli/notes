# The Training Loop

PyTorch ships no `.fit()`. The loop is yours to write, and it is always the same
five statements — the rest is bookkeeping.

```python
for xb, yb in loader:
    optimizer.zero_grad()        # 1. clear last step's gradients
    preds = model(xb)            # 2. forward — builds the graph
    loss = criterion(preds, yb)  # 3. reduce to one scalar
    loss.backward()              # 4. fill p.grad for every parameter
    optimizer.step()             # 5. update parameters in place
```

Each line owns exactly one thing, and each is separately forgettable:

| Line | Mutates | If you omit it |
|---|---|---|
| `zero_grad()` | `p.grad` → `None` | gradients keep [accumulating](autograd.md#grad-accumulates); the model diverges, no error |
| `model(xb)` | nothing | — |
| `criterion(...)` | nothing | — |
| `backward()` | `p.grad` (`+=`) | `step()` reuses stale gradients or sees `None` |
| `step()` | `p.data` | nothing learns; the loss is flat |

!!! warning "Call the module, don't call `forward`"
    `model(xb)` runs `__call__`, which fires registered hooks and *then*
    `forward`. `model.forward(xb)` skips the hooks — it works until something
    (a profiler, a feature extractor, `nn.Module` internals) depends on them.

## The three objects

```python
import torch
from torch import nn

model     = MyModel().to(DEVICE)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
```

- `model.parameters()` is a **generator of live references**. The optimizer
  holds those same tensors, which is how `step()` can update the model without
  ever being handed it. Construct the optimizer *after* moving the model to its
  device, and re-create it if you replace a layer.
- The criterion is just a function object; it holds no state (except a
  `weight=` you passed it) and takes part in no updates.
- `optimizer.step()` reads `p.grad` and writes `p` under `no_grad`. It has no
  idea where the gradients came from — anything that filled `.grad` works.

## Loss functions

```python
nn.MSELoss()               # regression;  preds and target both float, SAME shape
nn.CrossEntropyLoss()      # multi-class; preds are RAW LOGITS (N, C), target int64 (N,)
nn.BCEWithLogitsLoss()     # binary;      raw logits, float target of the same shape
```

!!! danger "Don't put a softmax in front of `CrossEntropyLoss`"
    It applies `log_softmax` internally. Feeding it probabilities trains a
    flatter, wrong objective — and it will not complain. Same for
    `BCEWithLogitsLoss` and a trailing sigmoid. The `WithLogits` variants also
    fold the two ops into one numerically stable kernel, so they are strictly
    better than `nn.Sigmoid()` + `nn.BCELoss()`.

- Every criterion defaults to `reduction='mean'` — a scalar, which is what
  `backward()` requires. `reduction='none'` returns per-sample losses for
  weighting or inspection; you must reduce before backward.
- The commonest shape bug: `MSELoss` between `(N,)` preds and `(N, 1)` targets
  [broadcasts](tensors.md#what-transfers-from-numpy) to `(N, N)` and trains on
  nonsense. `preds.squeeze(-1)` or `yb.unsqueeze(-1)` — deliberately.
- `CrossEntropyLoss` wants **class indices**, not one-hot, and they must be
  `int64`.

## The full skeleton

```python
for epoch in range(n_epochs):
    model.train()                                   # dropout/batch-norm ON
    running = 0.0
    for xb, yb in train_loader:
        xb, yb = xb.to(DEVICE), yb.to(DEVICE)
        optimizer.zero_grad()
        loss = criterion(model(xb), yb)
        loss.backward()
        optimizer.step()
        running += loss.item() * xb.size(0)         # .item(), and weight by batch size
    train_loss = running / len(train_loader.dataset)

    model.eval()                                    # dropout/batch-norm OFF
    with torch.no_grad():                           # no graph recorded
        val_loss = sum(criterion(model(xb.to(DEVICE)), yb.to(DEVICE)).item()
                       * xb.size(0) for xb, yb in val_loader) / len(val_loader.dataset)

    scheduler.step()                                # per EPOCH, after the optimizer
```

- `model.train()` / `model.eval()` toggle dropout and batch-norm only; they have
  nothing to do with gradients. Validation needs `eval()` **and** `no_grad()` —
  the first for correct behaviour, the second for memory.
- Weight the running loss by `xb.size(0)`: the last batch is usually smaller, so
  a plain mean of batch means is subtly wrong.
- `.item()` is not optional here — accumulating the tensor keeps every graph
  alive ([the leak](autograd.md#item-and-the-accidental-graph-leak)).
- A learning-rate scheduler steps **once per epoch** and **after**
  `optimizer.step()`. Stepping it per batch silently decays the rate an
  epoch-length times too fast.

## Between backward and step

The gap between lines 4 and 5 is where gradients are still raw and inspectable —
the only place these belong:

```python
loss.backward()
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
optimizer.step()
```

- Clipping before `backward()` clips nothing; after `step()` it's too late.
- Gradient norms logged here are the first diagnostic when a loss goes to `nan`:
  a norm exploding one step earlier localises the problem.

## Sanity checks before a long run

- **Overfit a single batch.** Loop 200 steps on one batch of ~8 samples; the
  loss must reach ~0. If it can't, the bug is in the model, loss, or label
  alignment — no amount of data will fix it.
- **Check the initial loss.** Random `C`-class classification starts near
  `ln(C)` (≈2.30 for 10 classes). A very different value means the head, the
  labels, or the reduction is wrong.
- **Watch that the parameters move.** `p.grad.norm()` of exactly `0.0`, or an
  unchanged parameter after `step()`, means the graph is severed — usually a
  `.detach()`, a `no_grad` block, or a `requires_grad=False` too far up.

## Silent failure checklist

| Symptom | Usual cause |
|---|---|
| Loss flat from step 1 | no `optimizer.step()`, or `lr` far too small |
| Loss diverges / `nan` | missing `zero_grad()`, `lr` too high, softmax before `CrossEntropyLoss` |
| Train loss good, val loss wild | forgot `model.eval()` |
| Validation runs out of memory | forgot `torch.no_grad()` |
| Memory climbs across epochs | accumulating a loss tensor without `.item()` |
| `Expected all tensors to be on the same device` | a batch not moved, or the optimizer built before `.to(DEVICE)` |

## Related

- [Autograd](autograd.md) — what `backward()` builds and frees, and why
  `zero_grad()` exists
- [Tensors](tensors.md) — dtype and device rules the loop assumes
- [Reproducibility and Seeding](../concepts/reproducibility.md) — making two
  runs of this loop comparable
