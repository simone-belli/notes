# Long Short-Term Memory

A **Long Short-Term Memory (LSTM)** network is a recurrent architecture that keeps a
memory vector updated by *addition* rather than repeated matrix multiplication, with
learned gates deciding what gets written, erased, and read. The additive path is the whole
point: it is what lets a learning signal travel back hundreds of timesteps.

## The problem: vanishing gradients

A plain **recurrent neural network (RNN)** carries one hidden state and applies the same
weights at every step:

$$
h_t = \tanh(W_x x_t + W_h h_{t-1} + b)
$$

Training unrolls this into one layer per timestep — **backpropagation through time
(BPTT)** — so the gradient reaching step $t$ from a loss at step $T$ contains a product of
$T-t$ Jacobians, each $\operatorname{diag}(\tanh') W_h^{\top}$. Products of many matrices
behave like powers of a scalar:

- Largest singular value of $W_h$ below 1 → **vanishing gradients**. No signal survives the
  trip back, so the network can only learn short-range structure.
- Above 1 → **exploding gradients**. One batch produces an enormous update and the loss
  goes to NaN.

Exploding is fixable by rescaling (**gradient clipping**). Vanishing is not — the
information is gone, not merely small. That asymmetry is why the architecture had to
change rather than the optimiser.

!!! note "It's a structural conflict, not bad tuning"
    Bengio et al. (1994) showed that for a recurrent map to hold information robustly its
    dynamics must be contractive — and contractive dynamics are exactly what makes the
    gradient vanish. Robust memory and long-range credit assignment fight each other *in
    that architecture*.

## The cell: two states, three gates

An LSTM carries **two** vectors between steps:

- $c_t$ — the **cell state**, long-term memory, touched only by elementwise multiply and add.
- $h_t$ — the **hidden state**, the working output that leaves the cell each step.

All four sub-networks read the same concatenation $[h_{t-1}, x_t]$ with their own weights:

$$
\begin{aligned}
f_t &= \sigma(W_f [h_{t-1}, x_t] + b_f) && \text{forget — what to keep} \\
i_t &= \sigma(W_i [h_{t-1}, x_t] + b_i) && \text{input — how much to write} \\
\tilde{c}_t &= \tanh(W_c [h_{t-1}, x_t] + b_c) && \text{candidate — what to write} \\
o_t &= \sigma(W_o [h_{t-1}, x_t] + b_o) && \text{output — what to expose}
\end{aligned}
$$

$$
c_t = f_t \odot c_{t-1} + i_t \odot \tilde{c}_t
\qquad
h_t = o_t \odot \tanh(c_t)
$$

with $\odot$ elementwise multiplication. Read the $c_t$ line as a sentence: **keep** the
fraction $f_t$ of what you remembered, and **add** the fraction $i_t$ of what you just
computed.

Two properties that prose descriptions tend to hide:

- Gates are **vectors**, not scalars — a 256-unit LSTM makes 256 independent forget
  decisions per step. The cell state is a bank of separately-managed registers, one slot
  able to hold a fact for 500 steps while its neighbour resets every step.
- Gates are **soft** — $f_t = 0.93$ means "multiply by 0.93", an actual leaky decay, not a
  decision. Softness is what keeps the cell differentiable and trainable end to end.

!!! tip "Sigmoid gates, tanh content"
    Sigmoid outputs $(0,1)$ — a multiplicative mask, a soft learned switch. Tanh outputs
    $(-1,1)$ — zero-centred so a write can push a slot up or down, bounded so repeated
    writes can't diverge. The pairing of $i_t$ with $\tilde{c}_t$ separates *whether* to
    write from *what* to write.

## Why the gradient survives

Along the memory path, $\partial c_t / \partial c_{t-1} \approx \operatorname{diag}(f_t)$,
so over many steps the gradient is scaled by $\prod_k f_k$ — a product of **learned
per-dimension scalars**, not of a fixed shared matrix:

- No repeated multiplication by $W_h$, so no geometric $\lambda^{T-t}$ term.
- If a slot needs to persist, the network can learn $f_k \approx 1$ there and the product
  stays near 1 for arbitrarily many steps. The gradient highway is *opened by learning*.
- It cannot explode along this path, since every $f_k \in (0,1)$.

Structurally this is the same trick as a residual connection — an identity path the
gradient can take around the nonlinearity — applied across time instead of depth.

!!! warning "Mitigated, not abolished"
    A learned $f \approx 0.9$ still decays as $0.9^n$: half gone in 7 steps, negligible by
    100. LSTMs make long-range learning possible, not automatic. In practice they handle
    hundreds of steps reliably and struggle past a few thousand.

A cheap, standard fix at initialisation: set the forget-gate bias $b_f$ to $+1$ rather
than $0$, so the cell starts out remembering ($\sigma(1) \approx 0.73$) instead of halving
its memory every step.

## Variants

- **Gated recurrent unit (GRU)** — drops the separate cell state, merges forget and input
  into one update gate ($z$ and $1-z$), adds a reset gate. Two gates, one state, ~25%
  fewer parameters. Performance is usually close; pick empirically.
- **Bidirectional** — one LSTM forwards, one backwards, hidden states concatenated. Great
  for tagging and classification; **impossible for forecasting**, because the backward pass
  reads the future. A silent source of [look-ahead leakage](data-leakage.md) in time-series
  work.
- **Stacked** — feed layer 1's $h_t$ as layer 2's input. Two or three layers is typical.
- **Peephole connections** — gates also see $c_{t-1}$ directly. Rarely used now.

Large ablations (Greff et al., 2017; Jozefowicz et al., 2015) found no variant beats the
plain forget-gated LSTM consistently; the forget gate and the output activation are the
components that matter.

## Practical notes

- **Truncated BPTT** — chop long sequences into chunks of 50–200 steps, backpropagate
  within a chunk, carry the state forward but *detached* from the graph.
- **Clip gradients** by global norm (typically 1.0–5.0); gates can still explode even if
  the memory path can't.
- **Scale inputs.** Saturated sigmoids have near-zero derivative, so large unscaled inputs
  pin gates at 0 or 1 and stall learning.
- **Pad and mask** variable-length sequences so padding doesn't reach the loss or corrupt
  the final state.
- **Dropout** must use the same mask at every timestep ("variational"), not a fresh one
  per step.
- **Timesteps can't be parallelised** — step $t$ needs $h_{t-1}$. Only the batch dimension
  parallelises, which is the throughput ceiling transformers escape.

## When to still reach for one

Self-attention made the path between any two positions $O(1)$ instead of $O(T)$ and
parallelises across the sequence, which is why transformers took over from 2017. LSTMs
still fit when the dataset is small (recurrence's order-and-locality bias is real
inductive help), when inference must stream at constant memory per step (the state is a
fixed-size vector, unlike a growing key-value cache), or when compute is tight. The ideas
also carry: gating and additive state updates recur throughout modern architectures.

## Mental model

The cell state is a whiteboard carried through the sequence. The **forget gate** erases
parts of it, the **candidate** drafts what could be written while the **input gate**
decides how much of that draft lands, and the **output gate** picks which parts you read
aloud right now. The board is never rewritten wholesale — only erased and added to — and
that is what keeps both the memory and the learning signal alive.

## Related

- [Building an LSTM](../pytorch/lstm-model.md) — turning `nn.LSTM` into a model: arguments, initialisation, head, clipping
- [LSTM Shapes](../pytorch/lstm-shapes.md) — `nn.LSTM` in practice, and the shape conventions that fail silently
- [Gradient Descent](gradient-descent.md) — what clipping and the update rule are doing
- [Autograd](../pytorch/autograd.md) — the graph BPTT unrolls and why detaching matters
- [Data Leakage](data-leakage.md) — the look-ahead trap a bidirectional LSTM walks into
