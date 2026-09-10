---
tags:
  - performance
---

# Tensors

A `torch.Tensor` is a NumPy array plus two things: it knows **where its bytes
live** (`dtype`/`device`) and **how it was computed** (autograd metadata). Every
line of a training loop is an operation on one, so five questions should be
answerable about any tensor without running the code: *what shape, what dtype,
what device, is it in the graph, does it share memory with something else?*

| Field | NumPy analogue |
|---|---|
| storage, `shape`, `stride()` | data buffer, `.shape`, `.strides` (bytes vs **elements**) |
| `dtype`, `device` | dtype only |
| `requires_grad`, `grad_fn`, `grad` | none |

```python
import torch

x = torch.arange(12).reshape(3, 4)
x.shape, x.stride(), x.dtype, x.device   # ([3,4]), (4,1), int64, cpu
```

## Creation

```python
torch.tensor([1, 2, 3])                  # infers dtype, ALWAYS copies
torch.zeros(3, 4); torch.ones(3, 4); torch.empty(3, 4); torch.full((3,4), 7.0)
torch.arange(0, 10, 2)                   # end-exclusive
torch.linspace(0, 1, steps=5)            # end-INCLUSIVE
torch.rand(3, 4); torch.randn(3, 4); torch.randint(0, 10, (3, 4))

torch.zeros_like(x); torch.randn_like(x) # same shape, dtype, device
x.new_zeros(2, 5)                        # same dtype/device, new shape

torch.from_numpy(a)                      # SHARES memory with the array (CPU only)
torch.as_tensor(a)                       # shares if it can, copies if it must
```

`torch.manual_seed(0)` seeds PyTorch's generator only — it has no effect on
NumPy's or Python's ([seeding](../concepts/reproducibility.md)).

!!! warning "Never use `torch.Tensor(...)` with a capital T"
    `torch.Tensor(5)` returns an **uninitialised float32 tensor of length 5**,
    not the scalar 5. It's a legacy constructor; always use lowercase
    `torch.tensor`.

## What transfers from NumPy

- **Indexing** works the same: `x[0]`, `x[:, 2]`, `x[..., -1]`, `x[x > 5]`,
  paired fancy indices. Use `None` where you'd write `np.newaxis`.
  ([NumPy — Indexing and Slicing](../../data/numpy/indexing.md))
- **Negative strides are not supported.** `x[::-1]` raises; use
  `torch.flip(x, dims=[0])`, which copies.
- **Broadcasting** rules are identical — align right, size-1 stretches.
  ([NumPy — Broadcasting](../../data/numpy/broadcasting.md))
- **Reductions** are the same operations with `axis=` renamed `dim=`:
  `x.sum(dim=0)`, `x.mean(dim=1, keepdim=True)`, `x.std()`, `x.argmax(dim=1)`.

Three reduction details that differ:

- `x.max(dim=1)` returns a named tuple `(values, indices)`; `x.amax(dim=1)`
  returns values only. `x.max()` with no `dim` returns a scalar.
- `mean` on an integer tensor raises — cast with `x.float().mean()`.
- `keepdim=True` is the normalisation idiom: `x - x.mean(dim=1, keepdim=True)`
  broadcasts, without it you get a shape error or a wrong broadcast.

!!! warning "The silent shape bug"
    `pred` of shape `(32,)` minus `target` of shape `(32, 1)` broadcasts to
    `(32, 32)`. The loss still computes and still backprops — on the wrong
    thing. `unsqueeze`/`squeeze` discipline is what prevents it.

## Reshape vocabulary

```python
x.view(6, 4)          # view — requires compatible strides, else raises
x.reshape(6, 4)       # view if it can, silent copy if it can't
x.view(-1, 4)         # -1 infers one dimension
x.flatten(0, 1)       # merge dims 0 and 1
x.unflatten(0, (2, 3))  # the inverse — split one dim into two
x.permute(2, 0, 1)    # view — arbitrary axis reorder
x.transpose(0, 1)     # view — swap exactly two axes
x.unsqueeze(0)        # add a size-1 axis;  x.squeeze(0) removes one
torch.cat([a, b], dim=0)     # join along an EXISTING axis
torch.stack([a, b], dim=0)   # join along a NEW axis; shapes must match
```

The [pandas reshaping](../../data/pandas/transforming/reshaping.md) vocabulary
maps across, with one landmine:

| Conceptual move | pandas | PyTorch |
|---|---|---|
| Split one axis into two | `unstack` | `view(B, T, C)` / `reshape` |
| Merge two axes into one | `stack` | `flatten(0, 1)` |
| Reorder axes | `swaplevel`, `.T` | `permute`, `transpose` |
| Concatenate along an axis | `pd.concat` | `torch.cat` |

!!! danger "`torch.stack` is not pandas `stack`"
    pandas `stack` folds a column level into the index (longer, narrower);
    `torch.stack` **adds a new axis**. Keep the two words in separate drawers.

`view` never copies and raises on a permuted tensor; `reshape` is "`view` if
possible, else `.contiguous().view(...)`" and always succeeds. Use `view` when
you believe it's free and want to be told if you're wrong.

```python
x.permute(0, 2, 1).view(2, 12)                # RuntimeError
x.permute(0, 2, 1).contiguous().view(2, 12)   # explicit copy
x.permute(0, 2, 1).reshape(2, 12)             # implicit copy
```

Bare `.squeeze()` removes *all* size-1 axes, so a batch of one silently changes
rank. Always name the axis: `.squeeze(1)`.

## dtype and device

Floating-point literals default to **float32**, not float64 as in NumPy — half
the memory, and what GPUs are built for. The consequence is that data arriving
from NumPy is float64 and won't join in:

```python
w = torch.randn(3, 4)                        # float32
x = torch.from_numpy(np.random.rand(4))      # float64
x @ w.T   # RuntimeError: expected scalar type Double but found Float
```

Fix at the boundary: `torch.as_tensor(a, dtype=torch.float32)`.

- `.float()`, `.long()`, `.bool()` are shorthands for `.to(torch.float32)` etc.
  ([NumPy — dtypes](../../data/numpy/dtypes.md) covers the promotion rules,
  which are the same.)
- Classification targets must be `long`; `nn.CrossEntropyLoss` rejects float
  and int32 labels.
- Only float and complex tensors can carry gradients.

All tensors in an operation must share a device, or you get *"Expected all
tensors to be on the same device"*. `.to()` is a no-op returning `self` when
dtype and device already match, so calling it defensively is free.

!!! danger "`tensor.to(device)` returns; `model.to(device)` mutates"
    `nn.Module.to()` moves parameters in place, so `model.to(device)` works on
    its own line. `Tensor.to()` returns a **new** tensor — a bare
    `x.to(device)` does nothing. It must be `x = x.to(device)`.

Getting values back to Python needs all three steps: `x.detach().cpu().numpy()`
— leave the graph, leave the GPU, share the buffer. For a scalar, `loss.item()`.

## requires_grad

This is the attribute that makes a tensor a graph node rather than an array.

```python
x = torch.tensor([2.0], requires_grad=True)
y = x ** 2 + 3

y.grad_fn        # <AddBackward0> — y records how it was made
x.is_leaf        # True (created by the user);  y.is_leaf is False
y.backward()
x.grad           # tensor([4.])
```

- Any op on a tensor requiring grad produces an output that requires grad and
  carries a `grad_fn`. That chain of `grad_fn`s **is** the graph, built forward
  by ordinary Python execution.
- `.backward()` **accumulates** into `.grad` on leaves — hence
  `optimizer.zero_grad()`.
- Non-leaf tensors don't keep `.grad` unless you call `y.retain_grad()`.
- `x.requires_grad_(True)` flips the flag in place; setting it `False` over
  `model.parameters()` is how a backbone gets frozen.

!!! note "Mental model"
    `requires_grad` is a *recording switch*, not a property of the numbers. The
    floats are identical either way; what changes is whether PyTorch keeps every
    intermediate alive to replay backwards. That memory cost is why `no_grad` at
    validation time can double the usable batch size.

[Autograd](autograd.md) covers the rest: what `.backward()` frees, why `.grad`
accumulates, and `no_grad` vs `detach` vs `inference_mode`.

## View vs copy

Half of this is the NumPy rule — a view shares storage, writes through it reach
the parent. What's new is that **autograd is watching**, so an in-place write
can corrupt a gradient rather than just a number.

| Returns a view | Always copies |
|---|---|
| basic slicing, `view`, `unsqueeze`, `squeeze` | fancy/boolean indexing, `flip`, `repeat` |
| `permute`, `transpose`, `movedim`, `narrow` | `clone`, `torch.cat`, `torch.stack` |
| `expand`, `broadcast_to`, `detach`, `diagonal` | `.to(other_device)`, `.float()` (when it must) |

`reshape`, `flatten`, and `contiguous` are conditional — view when the strides
allow, copy otherwise. `expand` is a stride-0 view and allocates nothing;
`repeat` materialises. There is no `np.shares_memory`; compare
`x.untyped_storage().data_ptr()`, or check `v._base is x`.

Three failure modes:

**Ordinary aliasing.** `big[:100].mul_(0)` zeroes part of `big`. Use `.clone()`
when you mean a copy (`clone` copies data but stays in the graph;
`detach().clone()` gives a plain disconnected copy).

**In-place on a leaf that requires grad** raises *"a leaf Variable that requires
grad is being used in an in-place operation"*. This is why manual updates are
wrapped — and what `optimizer.step()` does internally:

```python
with torch.no_grad():
    w -= lr * w.grad
```

**Mutating a value the backward pass saved.** Every tensor has a hidden version
counter; autograd records the version of each tensor it stashes for backward.

```python
y = x.sigmoid()   # sigmoid's backward needs y itself
y.mul_(2)
y.sum().backward()
# RuntimeError: one of the variables needed for gradient computation has been
# modified by an inplace operation ... is at version 1; expected version 0
```

The nasty variant is a mutation through a view someone *else* still holds — a
slice kept in a list, a cached activation. The error surfaces at `.backward()`,
far from the line that caused it, naming an operation rather than a variable.

!!! tip "Debugging it"
    `torch.autograd.set_detect_anomaly(True)` makes backward report the
    *forward* line that created the offending op. It's slow — turn it on only
    while hunting. And never use `x.data`: it bypasses version counting
    entirely, producing wrong gradients instead of an error.

In-place isn't forbidden — it's how memory stays down (`nn.ReLU(inplace=True)`,
`x.add_(y)`). The rule is: mutate only tensors you created and still exclusively
own, and only outside the region autograd needs them.

## Device-agnostic from line one

```python
DEVICE = torch.device(
    "cuda" if torch.cuda.is_available()
    else "mps" if torch.backends.mps.is_available()   # Metal Performance Shaders
    else "cpu"
)
```

- **Create on the device**, don't create-then-move:
  `torch.zeros(n, d, device=DEVICE)`, not `torch.zeros(n, d).to(DEVICE)` —
  the latter allocates on the CPU, copies, then frees.
- **Inherit rather than name it** where a tensor already exists:
  `torch.arange(n, device=x.device)`, `torch.ones_like(x)`. Inside a module,
  `next(self.parameters()).device`.
- **Move at the boundaries only** — the model once, each batch as it arrives,
  and *reassign*: `xb, yb = xb.to(DEVICE), yb.to(DEVICE)`.
- **Never hardcode `.cuda()` or `"cuda:0"`.** That's the line that makes the
  code unrunnable on a laptop.
- `torch.load(path, map_location=DEVICE)` — a GPU checkpoint otherwise tries to
  restore onto a GPU that may not exist.
- `DataLoader(..., pin_memory=True)` with `.to(DEVICE, non_blocking=True)`
  overlaps the host→device copy with compute, and is harmless on CPU.

`torch.set_default_device(DEVICE)` makes every factory call allocate there. It's
convenient in a notebook but implicit; an explicit `device=` argument is better
in code someone else reads.

## Related

- [Autograd](autograd.md) — `.backward()`, gradient accumulation, and the
  switches that stop the graph being recorded
- [The Training Loop](training-loop.md) — the five statements all of this
  exists to support
- [NumPy — Indexing and Slicing](../../data/numpy/indexing.md) — strides, and
  the view/copy rules this layer inherits
- [NumPy — Broadcasting](../../data/numpy/broadcasting.md) — identical rules
- [Pandas — Reshaping](../../data/pandas/transforming/reshaping.md) — where the
  `stack`/`unstack` vocabulary comes from
- [Reproducibility and Seeding](../concepts/reproducibility.md) — why
  `torch.manual_seed` isn't enough on its own
