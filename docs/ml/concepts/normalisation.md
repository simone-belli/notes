# Normalisation Layers

Three unrelated mechanisms are called *normalisation*, and only the second is a
layer:

- **Feature scaling** — standardising the network's *inputs* once, as
  preprocessing. Outside the model, and must be fit on training data only or it
  leaks (see [Data Leakage](data-leakage.md) and
  [Fold-Safe Transformers](../scikit-learn/fold-safe-transformers.md)).
- **Normalisation layers** — a module *inside* the network that rescales
  activations on every forward pass, using statistics of the tensor in front of
  it. This page.
- **Gradient normalisation** — bounding the gradient's norm before the step
  (`clip_grad_norm_`); see [Training Diagnostics](training-diagnostics.md).

## The operation

Every variant is the same two steps. First standardise over some set of axes:

$$
\hat{x} = \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}}
$$

with $\epsilon \approx 10^{-5}$ only to survive a constant feature. Then
re-scale with two learned vectors, one scale $\gamma$ and one shift $\beta$, one
element per normalised feature:

$$
y = \gamma \hat{x} + \beta
$$

```python
from torch import nn

layer = nn.LayerNorm(256)          # gamma and beta, 256 each
layer.weight, layer.bias           # gamma, beta
```

Step 2 is what makes the layer harmless. Standardising alone would forbid a
layer from emitting a large or offset output — a real loss of expressiveness.
With $\gamma$ and $\beta$ the layer can reproduce any mean and scale, including
recovering the identity:

$$
\gamma = \sqrt{\sigma^2 + \epsilon}, \quad \beta = \mu
\;\Longrightarrow\; y = x
$$

!!! note "A reparameterisation, not a restriction"
    Normalisation does not change which functions the network can represent. It
    changes how the optimiser travels through them — the whole benefit is in the
    conditioning, not the hypothesis space.

## Which axes — the only real difference

Write activations as $x_{n,c,i}$ — example $n$ of $N$, channel or feature $c$ of
$C$, spatial-or-time position $i$ of $I$. Every variant is the formula above with
the sum taken over different indices ($\sigma^2$ follows the same indices as
$\mu$):

$$
\begin{aligned}
\text{BatchNorm} &: &\mu_{c} &= \frac{1}{NI}\sum_{n}\sum_{i} x_{n,c,i} \\
\text{InstanceNorm} &: &\mu_{n,c} &= \frac{1}{I}\sum_{i} x_{n,c,i} \\
\text{GroupNorm} &: &\mu_{n,g} &= \frac{1}{|g|\,I}\sum_{c \in g}\sum_{i} x_{n,c,i} \\
\text{LayerNorm} &: &\mu_{n,i} &= \frac{1}{C}\sum_{c} x_{n,c,i}
\end{aligned}
$$

**Only BatchNorm's mean has lost the index $n$.** That is the whole story: its
statistics are shared across examples, so one example's output depends on its
batch-mates. Every other variant is a per-example function — which is why
transformers use LayerNorm, and why GroupNorm exists for small-batch regimes
(≤ 8, where batch statistics are too noisy).

| Variant | Reduces over | Depends on other examples? |
|---|---|---|
| `nn.BatchNorm1d/2d` | `N` (and `H, W`) | **yes** |
| `nn.LayerNorm` | trailing feature axes | no |
| `nn.InstanceNorm2d` | `H, W`, per example per channel | no |
| `nn.GroupNorm` | channel groups, per example | no |
| `nn.RMSNorm` | feature axis, **no mean subtraction** | no |

The two non-batch extremes are transposes of each other — LayerNorm reduces over
channels at fixed position, InstanceNorm over positions at fixed channel — and
GroupNorm interpolates: `nn.GroupNorm(1, C)` reduces over all of `C, H, W` per
example, `nn.GroupNorm(C, C)` is InstanceNorm. `nn.LayerNorm` reduces over
whatever trailing axes `normalized_shape` names, so `nn.LayerNorm(D)` on
`(N, T, D)` gives the $\mu_{n,i}$ above while `nn.LayerNorm((C, H, W))` gives
$\mu_n$.

Root Mean Square normalisation (`nn.RMSNorm`) drops the mean subtraction and the
shift entirely:

$$
y = \gamma \odot \frac{x}{\sqrt{\dfrac{1}{C}\sum_{c} x_c^2 + \epsilon}}
$$

One reduction instead of two, no $\beta$, about as good in practice, and the
default in recent large language models.

## Why it helps

The original *internal covariate shift* explanation (Ioffe & Szegedy, 2015) did
not survive testing — Santurkar et al. (2018) injected deliberate distribution
shift after a BatchNorm layer and training was unaffected. What holds up:

- **Loss-surface smoothing.** Normalisation lowers the Lipschitz constant of the
  loss and its gradient, so a larger step stays in the stable region — see
  [Gradient Descent](gradient-descent.md).
- **Weight-scale invariance.** Multiply the preceding layer's weights by $c$ and
  both $\mu$ and $\sigma$ scale by $c$, so the ratio — and therefore the output —
  is unchanged, while the gradient shrinks:

    $$
    \mathrm{Norm}\big((cW)x\big) = \mathrm{Norm}(Wx),
    \qquad
    \nabla_{cW}\,\mathcal{L} = \frac{1}{c}\,\nabla_{W}\,\mathcal{L}
    $$

    A layer whose weights have grown automatically takes smaller steps, so the
    effective rate self-adjusts per layer — which is the quantity the
    update-to-parameter ratio measures.
- **Less reliance on initialisation.** Kaiming/Xavier init exists to keep
  activation variance roughly constant with depth; a norm layer enforces it at
  every step instead of hoping it holds.
- **Mild regularisation (BatchNorm only)**, from the noise in batch-dependent
  statistics. It disappears at eval time, and is one reason BatchNorm stacked
  with Dropout often underperforms either alone.

## BatchNorm's two modes

A BatchNorm layer holds four tensors: the parameters $\gamma, \beta$ and two
**buffers**, `running_mean` and `running_var` — state that travels in the
`state_dict` but gets no gradient (see [Modules](../pytorch/modules.md)).

- **`train()`** — normalises with the *current batch's* $\mu_B, \sigma_B^2$, and
  updates the buffers $\hat\mu, \hat\sigma^2$ as an exponential moving average
  with rate $m$ (`momentum=0.1` by default):

    $$
    \hat\mu \leftarrow (1-m)\,\hat\mu + m\,\mu_B,
    \qquad
    \hat\sigma^2 \leftarrow (1-m)\,\hat\sigma^2 + m\,\sigma_B^2
    $$

- **`eval()`** — ignores the batch and substitutes the buffers, so inference is
  deterministic and independent of batch composition:

    $$
    y = \gamma\,\frac{x - \hat\mu}{\sqrt{\hat\sigma^2 + \epsilon}} + \beta
    $$

Every failure mode follows from that asymmetry, and all of them are silent:

| Symptom | Cause |
|---|---|
| Validation metrics shift with batch composition | `model.eval()` never called — batch statistics used at validation |
| `BatchNorm1d` raises on the last batch | a batch of size 1 has no variance; `drop_last=True` on the train loader |
| Fine-tuned model performs worse than expected | buffers still hold the source domain's statistics; `requires_grad_(False)` does **not** freeze them — only `eval()` stops them updating |
| Checkpoint is worse after reload | only `parameters()` was saved, so the buffers reset to mean 0 / var 1 |

!!! warning "Buffers are not parameters"
    `model.parameters()` excludes `running_mean` and `running_var`. Save
    `state_dict()`, not `parameters()`, or the layer normalises with freshly
    initialised statistics at eval time.

## Where the layer goes

**Drop the preceding bias.** A `Linear` bias adds a constant that the very next
mean subtraction removes, and $\beta$ plays its role anyway:

$$
\mathrm{Norm}(Wx + b) = \mathrm{Norm}(Wx)
$$

```python
from torch import nn

block = nn.Sequential(
    nn.Linear(256, 256, bias=False),   # bias would be cancelled
    nn.BatchNorm1d(256),
    nn.ReLU(),
)
```

This does not apply to `nn.RMSNorm`, which subtracts no mean. Note also that
norm-layer parameters and biases are conventionally excluded from weight decay
via a separate parameter group (see [Optimisers](../pytorch/optimisers.md)) —
decaying $\gamma$ toward 0 just shrinks the layer's output scale.

**Pre-norm versus post-norm** is the placement choice that matters in a residual
block:

$$
\underbrace{x_{\ell+1} = \mathrm{Norm}\big(x_\ell + F_\ell(x_\ell)\big)}_{\text{post-norm}}
\qquad
\underbrace{x_{\ell+1} = x_\ell + F_\ell\big(\mathrm{Norm}(x_\ell)\big)}_{\text{pre-norm}}
$$

Post-norm puts a norm layer *on* the skip path; pre-norm leaves it untouched, so
the gradient from layer $L$ back to layer $\ell$ is a product in which every
factor contains the identity:

$$
\frac{\partial x_L}{\partial x_\ell}
= \prod_{k=\ell}^{L-1}\left(I + \frac{\partial F_k}{\partial x_k}\right)
$$

No product of small branch Jacobians can kill it. Post-norm instead folds the
norm layer's Jacobian into each factor, attenuating the signal at every block,
which is why the original transformer needed learning-rate warmup to train at
all. Pre-norm trains deep stacks without warmup; the cost is that activations
grow along the residual stream, so a final norm before the output head is
required.

## Renormalising a sick layer

"Renormalise at this layer" is the prescription for one specific reading: the
per-layer activation standard deviation is stable through the network and then
**inflates at one layer**, which compounds downstream into `nan`. In order of
preference:

- **Insert a norm layer there** if the block has none — the scale is forced back
  to 1 regardless of what the weights do.
- **Check an existing one is in the forward path.** A module assigned in
  `__init__` but never called in `forward` still appears in `print(model)` and
  does nothing.
- **Check its mode** — a stray `.eval()` left on during training normalises with
  stale buffers and cannot track the inflation.
- **Rescale that layer's init**, e.g. zero-initialising the last layer of each
  residual branch so blocks start near-identity.

!!! tip "Local problem, local fix"
    Inflation confined to one layer is a scale problem *at that layer*. Cutting
    the global learning rate also works, but pays for it by slowing every healthy
    layer — prefer the local fix and keep the rate.

Long Short-Term Memory (LSTM) layers are the awkward case: `nn.LSTM` has no
internal normalisation and no flag to add one, because the gate arithmetic lives
in a fused kernel. Normalising the inputs and the LSTM's output is what is
available from outside — see [Building an LSTM](../pytorch/lstm-model.md).

## Related

- [Training Diagnostics](training-diagnostics.md) — the activation-statistics
  probe that tells you a norm layer is needed
- [Gradient Descent](gradient-descent.md) — the conditioning argument for why
  smoothing buys a larger learning rate
- [Modules](../pytorch/modules.md) — parameters vs buffers, and `state_dict`
- [Data Loading](../pytorch/data-loading.md) — `drop_last` and the batch-of-one
  error
