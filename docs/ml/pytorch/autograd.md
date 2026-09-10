---
tags:
  - performance
---

# Autograd

Autograd is reverse-mode automatic differentiation over a graph that PyTorch
records **as the forward pass runs**. There is no compilation step and no static
graph: every operation on a tensor with `requires_grad=True` appends a node, and
the graph is rebuilt from scratch on the next iteration. That's why an `if` or a
Python loop in `forward` just works.

```python
import torch

x = torch.tensor([2.0], requires_grad=True)
y = 3 * x ** 2

y.grad_fn                # <MulBackward0>
y.grad_fn.next_functions # (<PowBackward0>, ...) — the chain back to the leaf
y.backward()
x.grad                   # tensor([12.])
```

- **Leaves** are tensors you created (inputs, `nn.Parameter`); everything
  produced by an operation is a non-leaf carrying a `grad_fn`.
- Gradients land on **leaves only**. Non-leaves compute and discard theirs
  unless you ask: `h.retain_grad()`.
- The graph holds references to every intermediate needed for backward, so a
  forward pass under recording costs memory proportional to its depth.

## `.backward()`

```python
loss.backward()                  # loss must be a SCALAR
```

- On a non-scalar you must supply the vector to left-multiply the Jacobian by:
  `y.backward(torch.ones_like(y))`. Otherwise: *"grad can be implicitly created
  only for scalar outputs"*. This is why the loop reduces to a single number
  before calling it — `loss.mean()`, not the per-sample vector.
- It **frees the graph** as it walks. A second `backward()` on the same graph
  raises *"Trying to backward through the graph a second time"*; pass
  `retain_graph=True` if you genuinely need two passes (two losses over one
  forward, most commonly).
- `create_graph=True` makes the backward pass itself differentiable — needed for
  second-order gradients (penalties on the gradient, meta-learning). It leaks
  memory if used casually.
- The functional alternative returns gradients instead of writing them:

```python
g, = torch.autograd.grad(loss, [x])    # does NOT touch x.grad
```

!!! warning "The graph is freed, the tensors are not"
    `retain_graph=True` is not a fix for a bug — it's a statement that you will
    backward twice. Reaching for it to silence the error usually means the real
    problem is a tensor carried across iterations (see accumulation below).

## `.grad` accumulates

`.grad` is `None` until the first backward, and every subsequent `backward()`
**adds** to whatever is already there. Nothing ever clears it for you.

```python
for xb, yb in loader:
    optimizer.zero_grad()          # or model.zero_grad()
    loss = criterion(model(xb), yb)
    loss.backward()                # += into every p.grad
    optimizer.step()
```

- Forgetting `zero_grad()` doesn't error — it trains on the running sum of every
  batch so far, and the model quietly diverges.
- Modern `zero_grad()` defaults to `set_to_none=True`: it drops `.grad` back to
  `None` rather than writing zeros. Cheaper, and it skips the update for
  untouched parameters. The visible difference is that `p.grad` may be `None`
  rather than a zero tensor when you inspect it.
- Order matters only in that `zero_grad()` must not sit between `backward()` and
  `step()`. Before the forward or right after `step()` are both fine.

The accumulation is a feature when it's deliberate — a large effective batch on
a small GPU:

```python
for i, (xb, yb) in enumerate(loader):
    loss = criterion(model(xb), yb) / accum_steps   # scale, or the LR is wrong
    loss.backward()
    if (i + 1) % accum_steps == 0:
        optimizer.step()
        optimizer.zero_grad()
```

## Switching recording off

| Tool | Scope | Use for |
|---|---|---|
| `torch.no_grad()` | a block | validation, manual parameter updates |
| `torch.inference_mode()` | a block | pure inference — faster, outputs can never re-enter autograd |
| `.detach()` | one tensor | logging, metrics, cutting a recurrent history |
| `requires_grad_(False)` | a parameter | freezing layers |

```python
model.eval()
with torch.no_grad():
    val_loss = sum(criterion(model(xb), yb) for xb, yb in val_loader)
```

- `model.eval()` and `no_grad()` are **orthogonal**. `eval()` switches dropout
  and batch-norm into inference behaviour; `no_grad()` stops graph recording.
  Validation needs both.
- `detach()` returns a tensor **sharing storage** with the original but with no
  `grad_fn` — the numbers are live, the history is cut. `detach().clone()` when
  you also want an independent buffer.
- `inference_mode` is `no_grad` plus disabled version counting. Anything created
  inside it is permanently unusable in autograd, so don't use it around code
  whose outputs feed training.

!!! note "Mental model"
    None of these change the numbers. They change whether PyTorch writes down
    *how* the numbers were produced. Recording keeps every intermediate alive,
    which is why `no_grad` at validation time can double the usable batch size.

## `.item()` and the accidental graph leak

`.item()` pulls a Python number out of a one-element tensor; `.tolist()` and
`.detach().cpu().numpy()` do the same for larger ones.

```python
running += loss.item()        # a float
```

!!! danger "`running += loss` leaks every graph you've built"
    A bare `loss` is still a node. Summing tensors across a loop keeps every
    iteration's graph — and every activation in it — alive until the variable is
    reassigned. Memory climbs until the process dies, often hundreds of steps in
    and far from the line at fault. Always `.item()` or `.detach()` anything you
    accumulate for logging.

- `.item()` on a GPU tensor forces a **device synchronisation**: it waits for
  every queued kernel to finish. Once per step for the loss is nothing; inside
  an inner loop it serialises the pipeline.
- `.numpy()` on a tensor that requires grad raises — hence the full
  `x.detach().cpu().numpy()` incantation ([Tensors](tensors.md#dtype-and-device)).

## Errors and what they mean

| Message | Cause |
|---|---|
| *element 0 of tensors does not require grad* | backward on a tensor with no graph — an input never had `requires_grad`, or the forward ran under `no_grad` |
| *grad can be implicitly created only for scalar outputs* | `backward()` on a non-scalar; reduce first |
| *Trying to backward through the graph a second time* | graph already freed — a tensor was reused across iterations, or you meant `retain_graph=True` |
| *a leaf Variable that requires grad is being used in an in-place operation* | mutating a parameter outside `no_grad` |
| *one of the variables needed for gradient computation has been modified by an inplace operation* | a saved activation was mutated ([view vs copy](tensors.md#view-vs-copy)) |
| `.grad` is `None` after backward | the tensor is a non-leaf (use `retain_grad()`), or it was detached somewhere upstream |

`torch.autograd.set_detect_anomaly(True)` traces a backward failure to the
*forward* line that created the offending operation. It's slow — enable it only
while hunting. `nan` gradients are the other classic: it reports the first
backward op to produce one.

## Related

- [The Training Loop](training-loop.md) — where `zero_grad`/`backward`/`step`
  sit, and what else has to be right around them
- [Tensors](tensors.md) — `requires_grad`, and the view/copy rules that turn
  into gradient errors
- [Reproducibility and Seeding](../concepts/reproducibility.md) — the other
  hidden global state in a training run
