---
tags:
  - design-patterns
---

# Building an LSTM

`nn.LSTM` — the Long Short-Term Memory (LSTM) layer — is a **feature extractor, not a
model**. It maps a sequence of feature vectors to a sequence of hidden states and stops
there: no output layer, no activation, no notion of your target. The model is that
extractor plus a head, and nearly every modelling decision lives at the seam.

```python
import torch
from torch import nn


class LSTMForecaster(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2, dropout=0.2, output_size=1):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Linear(hidden_size, output_size)

    def forward(self, x):                     # (batch, seq_len, input_size)
        output, _ = self.lstm(x)              # (batch, seq_len, hidden_size)
        return self.head(output[:, -1, :])    # (batch, output_size)
```

Run a fake batch the moment it's written — `model(torch.randn(8, 30, 3)).shape` — before a
dataset or loss exists. The [shapes note](lstm-shapes.md) covers why `nn.LSTM` won't catch a
transposed input for you.

## Constructor arguments

```python
nn.LSTM(input_size, hidden_size, num_layers=1, bias=True,
        batch_first=False, dropout=0.0, bidirectional=False, proj_size=0)
```

- **`input_size`** — the **feature** count per timestep, never the lookback. Univariate
  prices: 1. Price, volume, moving average: 3.
- **`hidden_size`** — the width of both $h_t$ and $c_t$; the capacity dial. It enters the
  parameter count quadratically, so doubling it roughly quadruples the layer. Start at
  32–64 on a few thousand windows and grow only when the small model can't fit.
- **`num_layers`** — layer 1's hidden-state sequence becomes layer 2's *input* sequence, so
  layer 2 sees `hidden_size` features, not `input_size`. Two is a common sweet spot; past
  three the returns go negative without residual connections, which `nn.LSTM` doesn't offer.
- **`bias`** — leave it `True`. The gates need an offset to sit anywhere but half-open at
  initialisation.
- **`proj_size=k`** — a learned projection after each step, so $h_t$ comes out at width `k`
  while $c_t$ keeps `hidden_size`. Cuts parameters; ignore until that's the binding
  constraint.

### `dropout`

Three things about this argument surprise people:

- It applies **only between layers** — on each layer's output except the last. With
  `num_layers=1` it does nothing and PyTorch emits a warning that's easy to lose in a log.
  The `dropout if num_layers > 1 else 0.0` guard above lets `num_layers` be a
  hyperparameter without that warning firing on every trial.
- It **never touches the final output**. Dropout before the head must be an explicit
  `nn.Dropout` in your module.
- It is **not variational dropout**. Recurrent dropout should reuse one mask across
  timesteps; `nn.LSTM` resamples per step, so the noise partly averages out. True
  variational dropout means writing the time loop with `nn.LSTMCell` and losing the fused
  kernel — usually not worth it. Reach for weight decay and a smaller `hidden_size`.

### `bidirectional`

Doubles the parameters, makes `output` `2 * hidden_size` wide, and puts
`2 * num_layers` in the first axis of `h_n`/`c_n`. Excellent for classification over a
complete sequence; the head must then concatenate the top layer's two final states, since
`output[:, -1, :]` has a backward half that has seen only the last token:

```python
summary = torch.cat([h_n[-2], h_n[-1]], dim=1)      # (batch, 2 * hidden_size)
```

!!! danger "Bidirectional is look-ahead leakage on a forecast"
    The backward pass at time $t$ has already consumed $t+1 \ldots T$. On windows cut from
    a time series with a next-step target, that is
    [look-ahead leakage](../concepts/data-leakage.md) wearing an architecture's clothing —
    a beautiful validation curve that evaporates in production.

## The parameters

Per layer, per direction, `nn.LSTM` creates four tensors:

| Name | Shape | Holds |
|---|---|---|
| `weight_ih_l0` | `(4 * hidden_size, input_size)` | input → all four gates |
| `weight_hh_l0` | `(4 * hidden_size, hidden_size)` | previous hidden → all four gates |
| `bias_ih_l0` | `(4 * hidden_size,)` | bias on the input term |
| `bias_hh_l0` | `(4 * hidden_size,)` | bias on the hidden term |

The factor of 4 is the four gate computations **fused into one matmul** — that fusion is
most of why `nn.LSTM` is fast and a hand-written cell loop isn't. The gate order along that
stacked axis is **i, f, g, o** (input, forget, candidate, output), which you need for
surgical initialisation.

Two bias vectors is a cuDNN interface artifact: mathematically $b_{ih} + b_{hh}$ is one
bias. It means weight decay hits the bias twice, and that a forget-gate bias of 1.0 is
reached by setting one vector's forget slice, not both.

Parameter count per layer per direction, with $n$ that layer's input width:

$$4h(n + h) + 8h$$

```python
sum(p.numel() for p in model.parameters() if p.requires_grad)   # 51,009 for the model above
```

!!! tip "Compute the ratio before you train"
    51k parameters against 4000 training windows is 12 parameters per example — already
    firmly in overfitting territory. That one line is the most useful number available
    before a run starts.

## Initialisation

The default is $\mathcal{U}(-k, k)$ with $k = 1/\sqrt{\text{hidden\_size}}$, uniform across
all four gates. It trains, but two overrides are near-standard practice:

- **Forget-gate bias to 1.0.** At init every gate sits near 0.5, so the cell state halves
  each step — after 20 steps it's $10^{-6}$ and the memory is gone before learning begins.
  A bias of 1.0 puts the gate at ≈0.73, decaying slowly.
- **Orthogonal recurrent weights.** `weight_hh` is applied once per timestep, so its
  spectral radius decides whether the state grows or shrinks; orthogonal means all singular
  values are 1, preserving norm exactly.

```python
def init_lstm(lstm):
    h = lstm.hidden_size
    for name, param in lstm.named_parameters():
        if name.startswith("weight_ih"):
            nn.init.xavier_uniform_(param)
        elif name.startswith("weight_hh"):
            for k in range(4):                                   # one square block per gate
                nn.init.orthogonal_(param.data[k * h:(k + 1) * h])
        elif name.startswith("bias"):
            nn.init.zeros_(param)
            param.data[h:2 * h] = 1.0                            # slice 1 of i, f, g, o
```

`weight_hh` is `(4h, h)` — a *stack* of four square matrices — so orthogonalising the whole
tensor would not do what you mean. Call this once from `__init__`; `nn.init` functions are
in-place and run under `no_grad`.

## The head

Three patterns cover nearly everything:

```python
self.head(output[:, -1, :])    # sequence → one value (forecast, classify)
self.head(output)              # one output per timestep — Linear broadcasts, no loop
self.head(output.mean(dim=1))  # pooled summary; often better when the signal isn't at the end
```

- **No activation on the output.** `nn.CrossEntropyLoss` wants raw logits and applies
  log-softmax itself; a `Softmax` in front of it trains a badly-scaled model that still
  converges slowly enough to look plausible.
- **Never `c_n`** — that's the pre-output-gate cell state. And never `h_n[0]`, which is the
  *first* layer's final state. Both produce a `(batch, hidden)` tensor that trains fine and
  quietly underperforms.

A deeper head is the natural home for explicit dropout, since the layer's own `dropout`
never reaches the output — and dropout on a feed-forward path raises none of the
variational concerns above:

```python
self.head = nn.Sequential(
    nn.Dropout(0.2),
    nn.Linear(hidden_size, hidden_size // 2),
    nn.ReLU(),
    nn.Linear(hidden_size // 2, output_size),
)
```

## Training specifics

Most of the [training loop](training-loop.md) is unchanged. Three things are recurrent-specific:

- **Clip gradients.** The constant error carousel protects the cell-state path, not the
  gate weights; one outlier batch with Adam can destroy a converged model. The call goes
  between `backward()` and `step()`, with `max_norm` of 1.0–5.0 the usual range:

    ```python
    from torch.nn.utils import clip_grad_norm_

    loss.backward()
    clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer.step()
    ```

- **Scale the inputs.** The gates are sigmoids, and a saturated sigmoid passes no gradient.
  Unscaled features pin gates at 0 or 1 and the model stalls without erroring. Compute the
  statistics on the training split only — fitting a scaler on the whole series before
  splitting is the classic preprocessing leak.
- **Truncate backpropagation through time** on long sequences: chunks of 50–200 steps,
  state carried forward but `detach()`ed. Forgetting the detach grows the graph across the
  whole epoch until the process runs out of memory.

There is **no [layer normalisation](../concepts/normalisation.md)** in `nn.LSTM`, and no
flag to add one — it needs
`nn.LSTMCell` and a hand-written time loop. Wanting it is usually a signal to check whether
a transformer fits the problem instead.

!!! warning "Beat the persistence baseline first"
    If predictions look like the true series shifted right one step, the model has learned
    "predict the last value" and nothing else. On financial series this is the default
    outcome and it plots beautifully. Compare mean squared error against the naive forecast
    before believing any result.

## GPU gotchas

- **`flatten_parameters()`** — cuDNN wants an RNN's weights in one contiguous block;
  `DataParallel` and some `.to()` patterns break that, giving *"RNN module weights are not
  part of single contiguous chunk of memory"*. Call `self.lstm.flatten_parameters()` at the
  top of `forward` if you see it; it's a no-op otherwise.
- **`.to(DEVICE)` before building the optimiser.** Moving afterwards rebinds the parameter
  attributes to new tensors while the optimiser still holds the old CPU ones — `step()`
  updates tensors the forward pass never reads, and the loss just sits flat.
- **cuDNN's LSTM backward is nondeterministic.** Bit-exact
  [reproducibility](../concepts/reproducibility.md) needs
  `torch.use_deterministic_algorithms(True)` plus `CUBLAS_WORKSPACE_CONFIG=:4096:8`, at a
  cost in speed.

## Checklist

1. `batch_first=True`, passed explicitly.
2. `input_size` is the feature count, never the lookback.
3. `dropout` guarded by `num_layers > 1`; explicit `nn.Dropout` if you want it before the head.
4. `bidirectional=False` for anything causal.
5. Head reads `output[:, -1, :]` or `h_n[-1]` — never `h_n[0]`, never `c_n`.
6. Raw output from the head; no softmax, no activation.
7. Forget-gate bias at 1.0 when sequences are long.
8. Inputs scaled with training-split statistics only.
9. `torch.nn.utils.clip_grad_norm_` between `backward()` and `step()`.
10. `.to(DEVICE)` before constructing the optimiser.
11. Parameter count compared against the training-set size.
12. One batch overfitted to near-zero loss before any long run.

## Related

- [LSTM Shapes](lstm-shapes.md) — the axis conventions that fail silently, and which state tensor the head wants
- [Long Short-Term Memory](../concepts/lstm.md) — what the gates and cell state do, and why the gradient survives
- [Modules](modules.md) — the `nn.Module` registry this model class relies on,
  and [how to walk to](module-inspection.md#finding-submodules) the `lstm` and `head`
  subtrees by name
- [Optimisers](optimisers.md) — why the optimiser must be built after `.to()`
