# Module Inspection

Assigning a submodule registers it under its attribute name, so a model is a
tree in which every node has a **dotted path** — `head.0.weight`. That single
naming scheme is shared by `named_modules()`, `named_parameters()`,
`state_dict()` and `get_submodule()`, which is what lets discovery feed straight
into action. Reading a layer's *output* needs one more tool — a **forward
hook**, which fires on every pass without editing
[`forward`](modules.md#forward).

```python
import torch
from torch import nn
```

## Finding submodules

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

## Parameters

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

## Related

- [Modules](modules.md) — the registry that gives every node its dotted path in
  the first place
- [Training Diagnostics](../concepts/training-diagnostics.md) — the per-layer
  statistics worth reading out through a forward hook
- [Autograd](autograd.md) — why storing a raw hook output pins the graph
- [Optimisers](optimisers.md) — what a filtered `parameters()` generator feeds
