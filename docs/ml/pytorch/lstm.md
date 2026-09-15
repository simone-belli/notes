# LSTM Shapes

Most PyTorch layers reject a wrong shape immediately. `nn.LSTM` — the Long Short-Term
Memory (LSTM) layer — cannot: its input is three
axes of numbers with no way to tell which axis is which, so handing it
`(batch, seq, features)` when it expects `(seq, batch, features)` **runs, returns a
plausible shape, and trains**. The model is nonsense — it unrolled across your batch — but
nothing raises.

```python
import torch
import torch.nn as nn
```

!!! danger "Legal is not correct"
    For `nn.LSTM`, a shape that runs without error is not evidence of a shape that is
    right. Assert shapes; don't infer them from the absence of an exception.

## `batch_first`

The default is `batch_first=False`, expecting `(seq_len, batch, input_size)` — the odd one
out against `DataLoader`, `nn.Linear`, and everything else. Always pass it explicitly:

```python
lstm = nn.LSTM(input_size=3, hidden_size=8, num_layers=2, batch_first=True)
output, (h_n, c_n) = lstm(torch.randn(4, 10, 3))   # (batch=4, seq=10, features=3)
assert output.shape == (4, 10, 8)
assert h_n.shape == (2, 4, 8)
```

The same input through a `batch_first=False` layer returns `output` of shape `(4, 10, 8)` —
**identical to the correct case** — and `h_n` of `(2, 10, 8)`, where the batch has silently
become 10. Only `h_n` betrays it.

!!! warning "Batch size == lookback has no tell"
    Batch 32 with a 32-step lookback makes every tensor the same shape under both
    conventions. Nothing distinguishes the transposed run but the numbers. Set
    `batch_first=True` as policy, not as a per-case check.

!!! note "`batch_first` does not touch the state"
    It reorders `input` and `output` only. `h_n` and `c_n` are **always**
    `(num_layers * num_directions, batch, hidden_size)` — batch in the middle — under both
    settings. Even in a batch-first model the state tensors are not batch-first.

## `output` vs `h_n`

| Tensor | Shape (`batch_first=True`) | Contains |
|---|---|---|
| `output` | `(batch, seq_len, hidden * directions)` | every **timestep**, top layer only |
| `h_n` | `(layers * directions, batch, hidden)` | final **timestep**, every layer |
| `c_n` | `(layers * directions, batch, hidden)` | final cell state, every layer |

They are orthogonal slices of the same block of states and overlap in exactly one place:

```python
assert torch.equal(output[:, -1, :], h_n[-1])    # bit-identical
```

- `h_n[0]` is the **first** layer's final state, not the last — a plausible
  `(batch, hidden)` tensor that trains fine and just performs worse. Use `h_n[-1]`.
- `output` never contains lower layers; a stacked `nn.LSTM` won't give you those.
- `c_n` is the raw cell state before the output gate, related to `h_n` by
  $h = o \odot \tanh(c)$. Its only real use is feeding back as initial state — passing it
  to a `Linear` is a bug.

## Which one for a prediction

One prediction per sequence — forecasting, classification — wants the whole-sequence
summary:

```python
head = nn.Linear(8, 1)
y = head(output[:, -1, :])    # (batch, 1)
y = head(h_n[-1])             # same tensor
```

Prefer `output[:, -1, :]` under `batch_first=True` so the axis order matches the rest of
your code; prefer `h_n[-1]` under `batch_first=False`, where `output[-1]` is the correct
spelling.

One prediction per timestep just uses all of `output` — `Linear` broadcasts over leading
axes:

```python
y_all = head(output)          # (batch, seq_len, 1)
```

!!! tip "The two `-1`s mean different things"
    In `output[:, -1, :]` the `-1` indexes **time**; in `h_n[-1]` it indexes **layer**.
    They coincide only because each tensor already collapsed the other axis. `output[-1]`
    under `batch_first=True` gives the last *sample*, shape `(seq_len, hidden)` — which
    still flows into a `Linear` without error.

**Bidirectional changes the answer.** `output` is `2 * hidden` wide and `output[:, -1, :]`
is wrong as a summary: its second half is the backward pass having seen only the final
token. Take the states explicitly:

```python
summary = torch.cat([h_n[-2], h_n[-1]], dim=1)   # fwd, bwd of the top layer
```

## `(h_0, c_0)`

The second argument is a **tuple**, both parts shaped like `h_n` — never batch-first.
Omitting it initialises zeros, and explicit zeros are bit-identical to the default, so
write them only if you're carrying state.

These errors are loud, unlike the transposition — the layer knows `num_layers` and
`hidden_size` from its own construction, so it can check the state; it knows nothing about
your intended batch or sequence length, so it cannot check the input.

```
Expected hidden[0] size (2, 4, 8), got [4, 2, 8]
For batched 3-D input, hx and cx should also be 3-D but got (2-D, 2-D) tensors
```

Carrying state across chunks — truncated backpropagation through time — is the real use.
`None` is a valid state, so the first iteration needs no special case:

```python
state = None
for chunk in chunks:                            # each (batch, chunk_len, features)
    out, state = lstm(chunk, state)
    state = tuple(s.detach() for s in state)    # cut the history
```

Chunked-with-carry is numerically identical to one long forward pass; the split changes
gradients, not activations. Forgetting [`detach()`](autograd.md) is the classic
growing-memory bug. Only carry state when the next chunk genuinely follows the previous one
in time for every row.

## Sequence length vs lookback

**Lookback** is a modelling choice living in your dataset code; **`seq_len`** is a tensor
axis. They're the same number in a sliding-window setup, which is why they blur — but two
things follow from their being different kinds of thing.

`nn.LSTM` bakes in `input_size` and `hidden_size` at construction, **not** `seq_len`. The
same module accepts `(32, 30, F)` and then `(32, 200, F)`; the recurrence just unrolls
further. So a wrong lookback never raises, and train/inference can silently disagree on
length.

Windowing a series of $N$ points with lookback $L$ gives $N - L + 1$ windows, and
$N - L$ once a next-step target costs you one more. Off-by-one here shifts every label —
either a dead model or, in the wrong direction, [look-ahead
leakage](../concepts/data-leakage.md) with a suspiciously good score.

```python
series = torch.arange(100.0).unsqueeze(1)    # (100, 1)
lookback = 30
windows = series.unfold(0, lookback, 1)      # (71, 1, 30) -- window axis LAST
X = windows.permute(0, 2, 1)                 # (71, 30, 1) = (batch, seq, feature)
X, y = X[:-1], series[lookback:]             # (70, 30, 1), (70, 1)
```

!!! warning "The univariate trap"
    With one feature the feature axis is size 1 and easy to drop — and a rank-2 input does
    not reliably raise, because modern PyTorch reads it as an **unbatched** sequence
    `(seq_len, input_size)`, returning `output` of `(seq_len, hidden)` with no batch axis.
    When it does raise, the message is `input.size(-1) must be equal to input_size`, which
    points at the feature axis rather than the missing batch axis. Keep the explicit
    `unsqueeze(-1)`, and `unsqueeze(0)` a single sample at inference.

## Padding and other shape shifters

Padding breaks `output[:, -1, :]`: for a short row the last position is the state after
consuming padding zeros. `pack_padded_sequence` fixes it — `h_n` then holds each sequence's
**true** final state, and this is the one case where `h_n[-1]` and `output[:, -1, :]`
disagree. `pad_packed_sequence` unpacks, zeroing past each length. `lengths` must be on the
CPU even when the data is on GPU.

- **`proj_size=k`** makes `output` and `h_n` width `k` while `c_n` keeps `hidden_size` — so
  the two state tensors stop matching.
- **`nn.LSTMCell`** has no sequence or layer axis at all: states are `(batch, hidden)` and
  you write the time loop yourself.

## Checklist

1. `batch_first=True` passed explicitly.
2. `input_size` is the **feature** count, never the lookback.
3. Input is rank 3, feature axis explicit even when it's 1.
4. `output.shape == (batch, seq_len, hidden * directions)`.
5. `h_n.shape == (layers * directions, batch, hidden)` — batch in the **middle**.
6. The head consumes `output[:, -1, :]` or `h_n[-1]` — not `h_n[0]`, not `c_n`.
7. Window count is $N - L + 1$, or $N - L$ with a next-step target.
8. Carried state is detached and the chunks are genuinely consecutive.

## Related

- [Building an LSTM](lstm-model.md) — the model class around the layer: arguments, initialisation, head, clipping
- [Long Short-Term Memory](../concepts/lstm.md) — what the cell state and gates actually do
- [Modules](modules.md) — where the `assert`s go in `forward`
- [Data Loading](data-loading.md) — building the windows, and why `random_split` is wrong here
