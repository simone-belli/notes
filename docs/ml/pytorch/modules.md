---
tags:
  - design-patterns
---

# Modules

A model is a subclass of `nn.Module`. Strip away the convenience and the base
class is three things: a **registry** of the tensors and child modules it owns,
a **callable** that runs your `forward`, and a set of **tree operations**
(`.to()`, `.parameters()`, `.state_dict()`, `.train()`) that recurse over the
children. Everything the [training loop](training-loop.md) does to a model is
one of those recursive walks.

```python
import torch
from torch import nn

class Net(nn.Module):
    def __init__(self, in_dim, out_dim):
        super().__init__()                    # MUST come first
        self.fc = nn.Linear(in_dim, out_dim)

    def forward(self, x):
        return self.fc(x)
```

The registry is the whole trick: `nn.Module.__setattr__` is overridden, so
assigning an `nn.Module` or `nn.Parameter` to an attribute files it in
`self._modules` or `self._parameters`. Nothing else is registered.

!!! danger "`super().__init__()` before anything else"
    Without it you get *"cannot assign module before Module.\_\_init\_\_()
    call"* — the registries don't exist yet.

## Three kinds of state

| Kind | Declared as | In `parameters()` | In `state_dict()` | Moved by `.to()` |
|---|---|---|---|---|
| Parameter | `nn.Parameter(t)` | yes | yes | yes |
| Buffer | `self.register_buffer("m", t)` | **no** | yes | yes |
| Plain attribute | `self.t = torch.zeros(3)` | no | **no** | **no** |

```python
self.scale = nn.Parameter(torch.ones(d))               # learned
self.register_buffer("mask", torch.tril(torch.ones(n, n)))   # state, not learned
self.eps = 1e-5                                        # config
```

- `nn.Parameter` is a Tensor subclass whose job is to be recognised by the
  registry; it defaults to `requires_grad=True`.
- Buffers are model-owned tensors that aren't learned — batch-norm running
  statistics, a causal mask, a positional table. Registering them is what makes
  them move device and get saved.
- A plain tensor attribute stays on the CPU forever, and the first GPU forward
  raises *"Expected all tensors to be on the same device"* from inside your own
  module.

## The registration trap

Only attributes assigned **directly** on the module are registered — a plain
Python container is opaque:

```python
self.layers = [nn.Linear(8, 8) for _ in range(3)]     # INVISIBLE
```

Those layers are absent from `parameters()`, so the optimizer never updates
them, `.to(device)` never moves them, and `state_dict()` never saves them. The
model trains; those layers just never learn, with no error at any point.

```python
self.layers  = nn.ModuleList([nn.Linear(8, 8) for _ in range(3)])
self.heads   = nn.ModuleDict({"cls": nn.Linear(8, 2), "reg": nn.Linear(8, 1)})
self.weights = nn.ParameterList([nn.Parameter(torch.randn(4)) for _ in range(2)])
```

`ModuleList` is a list that registers — it has no `forward`, so you still write
`for layer in self.layers: x = layer(x)` yourself.

!!! tip "The diagnostic"
    `sum(p.numel() for p in model.parameters())` right after construction. A
    count smaller than expected means something is hiding in a plain list.

## Composition

`nn.Sequential` is a Module *with* a `forward` that chains children, each taking
one input and returning one output:

```python
mlp = nn.Sequential(
    nn.Linear(784, 256), nn.ReLU(),
    nn.Dropout(0.1),
    nn.Linear(256, 10),
)
```

It's useless the moment the data flow isn't a line. A residual connection needs
`x` to survive the block, so it must be a custom Module:

```python
class ResidualBlock(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.body = nn.Sequential(nn.Linear(d, d), nn.ReLU(), nn.Linear(d, d))
        self.norm = nn.LayerNorm(d)

    def forward(self, x):
        return self.norm(x + self.body(x))     # the skip is the point
```

**`Sequential` for runs of layers; a custom Module wherever the graph branches,
merges, or reuses a child.** Nesting is normal — a model is a Module containing
Sequentials containing Modules.

## Layers: module or functional

Most operations exist twice — `torch.nn` classes and `torch.nn.functional`
functions.

- **State or configuration that must travel with the model → the Module.**
  Anything with weights (`Linear`, `Conv2d`, `Embedding`), buffers
  (`BatchNorm2d`), or train/eval-dependent behaviour (`Dropout`).
- **Pure function of its input → either.** `F.relu(x)` in `forward` keeps
  `__init__` short; `nn.ReLU()` shows up in `print(model)` and can live in a
  `Sequential`.

!!! warning "`F.dropout` defaults to `training=True`"
    It keeps dropping at eval time unless you pass `training=self.training`.
    `nn.Dropout` reads the flag for you — use the module.

| Layer | Shape in → out | Notes |
|---|---|---|
| `nn.Linear(in, out)` | `(*, in)` → `(*, out)` | acts on the **last** axis; leading axes pass through |
| `nn.Embedding(n, d)` | `(*)` int64 → `(*, d)` | a lookup table, not a matmul |
| `nn.Conv2d(cin, cout, k)` | `(N, cin, H, W)` → `(N, cout, H', W')` | channels-first |
| `nn.LayerNorm(d)` | unchanged | last axis, per sample |
| `nn.BatchNorm1d(d)` | unchanged | across the batch — train/eval differ |
| `nn.Dropout(p)` | unchanged | scales by `1/(1-p)` at train, identity at eval |
| `nn.Flatten()` | `(N, ...)` → `(N, -1)` | keeps the batch axis |

`Linear` acting on the last axis is why it works unchanged on
`(batch, features)` or `(batch, seq, features)` — you rarely need to reshape.

## forward

Ordinary Python: loops, conditionals, and calling one submodule twice are all
fine, because the graph is recorded per call.

```python
def forward(self, x):                 # (N, C, H, W)
    x = self.stem(x)
    x = x.flatten(1)                  # (N, C*H*W) — keep the batch axis
    return self.head(x)               # LOGITS
```

- **Annotate shapes in comments** at each transition — most model bugs are shape
  bugs, and the comment is what makes a mismatch visible while reading.
- **Batch axis first and untouched**: `flatten(1)`, `view(x.size(0), -1)`,
  `squeeze(1)` — never a bare `flatten()` or `squeeze()`.
- **No device logic in `forward`.** Derive instead:
  `torch.arange(n, device=x.device)`, `torch.zeros_like(x)`.
- **Return raw logits** — the losses apply their own
  [softmax or sigmoid](training-loop.md#loss-functions).
- **Take shapes as `__init__` arguments**, so the model can be smoke-tested on a
  tiny configuration.

`mat1 and mat2 shapes cannot be multiplied (32x784 and 256x10)` is almost always
a `Linear` whose `in_features` doesn't match the previous layer's output — read
the second number of the first shape against the first of the second.

## Inspecting

Assigning a submodule registers it under its attribute name, so a model is a
tree in which every node has a **dotted path** — `head.0.weight`. That single
naming scheme is shared by `named_modules()`, `named_parameters()`,
`state_dict()` and `get_submodule()`, which is what lets discovery feed straight
into action.

### Finding submodules

Take a model with two named parts, `self.lstm` and `self.head`:

```python
print(model)                      # the repr: the whole tree, indented — start here

model.lstm                        # attribute access
model.head[0]                     # Sequential indexes
model.get_submodule("head.0")     # by dotted path, when the path is data

for name, child in model.named_children():    # one level deep
    print(name, type(child).__name__)         # lstm LSTM / head Sequential

for name, m in model.named_modules():         # recursive, depth-first
    print(repr(name), type(m).__name__)       # '' Net / 'lstm' LSTM / 'head.0' Linear
```

- `named_modules()` **includes the root itself** under the empty name `''`, and
  yields containers alongside real layers — filter both out when acting on
  leaves. `children()`/`modules()` are the unnamed equivalents.
- Select by type rather than by depth:

```python
for name, m in model.named_modules():
    if isinstance(m, nn.LSTM):
        print(name)               # 'lstm'
```

- `get_submodule(path)` raises `AttributeError` on a bad path — better than a
  `getattr` chain when the name comes from a config. Siblings are
  `get_parameter("head.0.weight")` and `get_buffer(...)`.
- Inside containers the key is the index or dict key — `layers.0`,
  `heads.price` — and `model.heads["price"]` works on a `ModuleDict`.

### Parameters

```python
for name, p in model.named_parameters():
    print(name, tuple(p.shape), p.requires_grad)     # 'stem.0.weight' (256, 784) True
sum(p.numel() for p in model.parameters() if p.requires_grad)
```

- `named_parameters()` keys are those same dotted paths — the keys in
  `state_dict()`, which is what makes partial loading and per-layer learning
  rates possible.
- `torchinfo.summary(model, input_size=(1, 784))` adds per-layer output shapes.
- `module.register_forward_hook(fn)` extracts intermediates without editing
  `forward` — see [Forward hooks](#forward-hooks) below.

!!! warning "Renaming an attribute breaks old checkpoints"
    Rename `self.head` to `self.classifier` and every `head.*` key in a saved
    `state_dict` stops matching. `load_state_dict(..., strict=True)` reports it;
    `strict=False` silently leaves those layers randomly initialised.

Freezing is per-parameter, and worth filtering out of the
[optimizer](optimisers.md) so Adam doesn't carry state for tensors that never
move:

```python
for p in model.backbone.parameters():
    p.requires_grad_(False)
optimizer = torch.optim.AdamW(
    (p for p in model.parameters() if p.requires_grad), lr=1e-3)
```

## Forward hooks

A hook is a [callback](../../python/language/functional/callbacks.md) attached
to a module, so PyTorch runs it on every forward pass — reading a layer's input
or output **without editing `forward`**, which matters when the layer lives
inside a pretrained model you don't own.

```python
def fn(module, args, output):
    print(module.__class__.__name__, output.shape, output.std().item())

handle = model[0].register_forward_hook(fn)
model(x)            # fn fires here
handle.remove()
```

- `args` is a **tuple** of positional inputs; `args[0]` is the usual tensor.
- `output` is whatever `forward` returned — for `nn.LSTM` that's the
  `(output, (h_n, c_n))` tuple, so don't assume a bare tensor.
- `register_forward_pre_hook(fn)` takes `fn(module, args)` and fires *before*
  `forward`; `register_full_backward_hook(fn)` takes
  `fn(module, grad_input, grad_output)` and fires during `backward()`. The older
  `register_backward_hook` is deprecated.

!!! warning "Returning a value rewrites the forward pass"
    A forward hook that returns non-`None` **replaces the module's output** (a
    pre-hook replaces its input). For observation, return nothing. A stray
    `return output` works by accident; `return output.detach()` silently severs
    the graph downstream.

Hooks only run via `__call__`. `model.forward(x)` skips them entirely — the
usual reason a hook "doesn't fire".

### The handle, and when to remove it

`register_forward_hook` returns a `RemovableHandle`. The module keeps its hooks
in an `OrderedDict` keyed by an integer id; the handle holds that id, and
`handle.remove()` deletes the entry, so the hook stops firing and the module's
reference to your function is dropped.

Removal is the only way to undo a registration — hooks are not in `state_dict()`
and survive `eval()` and `.to(device)`. The rule is that **a hook should live as
long as the measurement, not as long as the model**:

- **It fires forever otherwise** — including in validation and production
  inference, not just the debug run you wrote it for.
- **Registering in a loop stacks hooks.** Ten epochs of
  `layer.register_forward_hook(fn)` means ten calls per forward pass; nothing
  deduplicates.
- **Storing outputs leaks memory.** `acts.append(output)` pins the whole
  [autograd](autograd.md) graph for every batch recorded. Append
  `output.detach().cpu()`, or a scalar like `output.std().item()`.

Because `remove()` must run even if the forward pass raises, tie it to a
[context manager](../../python/language/runtime/context-managers.md):

```python
from contextlib import contextmanager

@contextmanager
def capture(module, fn):
    handle = module.register_forward_hook(fn)
    try:
        yield
    finally:
        handle.remove()

with capture(model[0], fn):
    model(x)
```

For several layers, keep the handles in a list and remove them together:

```python
handles = [m.register_forward_hook(fn)
           for m in model.modules() if isinstance(m, nn.ReLU)]
for h in handles:
    h.remove()
```

## Initialisation

Built-in layers initialise themselves sensibly (Kaiming-uniform for `Linear` and
`Conv2d`), so usually there is nothing to do. To override, `apply` walks the
tree:

```python
def init_weights(m):
    if isinstance(m, nn.Linear):
        nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
        nn.init.zeros_(m.bias)

model.apply(init_weights)
```

`nn.init` functions are in-place and run under `no_grad`. A `nn.Parameter` you
create yourself gets *no* initialisation beyond the tensor you passed in.

## Saving

Save the `state_dict` — an `OrderedDict` of dotted names to tensors, parameters
*and* buffers — not the model object.

```python
torch.save(model.state_dict(), "model.pt")

model = Net(784, 10)                                          # architecture first
model.load_state_dict(torch.load("model.pt", map_location=DEVICE))
model.eval()
```

- `torch.save(model, ...)` pickles the class reference and breaks when you
  rename or move the file that defines it.
- `load_state_dict(..., strict=False)` returns `(missing_keys, unexpected_keys)`
  instead of raising — how a pretrained backbone loads into a model with a new
  head.
- A resumable checkpoint also needs `optimizer.state_dict()` (Adam's moments)
  and the epoch number, not just the weights.

## Smoke test

```python
model = MLP(784, 256, 10).to(DEVICE)
model(torch.randn(4, 784, device=DEVICE)).shape     # (4, 10)
```

Run one fake batch the moment the model is written. Every shape bug surfaces in
a millisecond, before a data loader, a loss, or an optimizer is involved.

## Checklist

1. `super().__init__()` first.
2. Submodules assigned as attributes, or wrapped in `ModuleList`/`ModuleDict`.
3. Non-learned tensors via `register_buffer`.
4. Shapes as `__init__` arguments; shape comments in `forward`.
5. Batch axis first and untouched.
6. Raw logits out.
7. No device logic in `forward`.
8. One fake batch through it before anything else.
9. Parameter count checked against expectation.
10. Save the `state_dict`.

## Related

- [The Training Loop](training-loop.md) — what consumes `parameters()` and
  toggles `train()`/`eval()`
- [Autograd](autograd.md) — why `requires_grad` on a parameter is what makes it
  trainable
- [Tensors](tensors.md) — `.to()` on a module mutates, on a tensor it returns
- [Training Diagnostics](../concepts/training-diagnostics.md) — the per-layer
  statistics worth reading out through a forward hook
