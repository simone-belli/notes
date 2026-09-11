# Gradient Descent

Training minimises an empirical risk with no closed form, so you go downhill iteratively. Every
optimiser in this family is the same line with a different vector after the minus sign:

$$
\theta_t = \theta_{t-1} - \alpha \cdot (\text{something built from } g_1,\dots,g_t)
$$

where $\theta \in \mathbb{R}^d$ are the parameters, $\alpha$ the **learning rate**, and $g_t$ the
gradient of the loss at step $t$.

## The base algorithm

$$
\theta_t = \theta_{t-1} - \alpha \nabla_\theta \mathcal{L}(\theta_{t-1})
$$

A first-order Taylor expansion gives
$\mathcal{L}(\theta_t) \approx \mathcal{L}(\theta_{t-1}) - \alpha\|\nabla\mathcal{L}\|^2$ — the
loss decreases, *provided the linear approximation holds over a step of size $\alpha$*. That
proviso is the whole theory of learning-rate selection. With gradient-Lipschitz constant $L$
(curvature bounded by $L$), descent is guaranteed for

$$
0 < \alpha < \frac{2}{L}
$$

and $\alpha = 1/L$ is optimal for a quadratic. Above $2/L$ the iteration **diverges** — the
loss-goes-to-`nan` failure mode.

### Conditioning is why it's slow

For a quadratic with Hessian eigenvalues $\lambda_1 \ge \dots \ge \lambda_d$, error along
direction $i$ contracts by $(1-\alpha\lambda_i)$ per step. Reaching accuracy $\epsilon$ costs
$O(\kappa\log(1/\epsilon))$ steps, where

$$
\kappa = \frac{\lambda_1}{\lambda_d}
$$

is the **condition number**. $L = \lambda_1$, so the usable rate is set by the *sharpest*
direction while progress is set by the *flattest*.

!!! note "The narrow-valley picture"
    On an ill-conditioned quadratic the gradient points nearly perpendicular to the valley
    floor, so descent ping-pongs across the valley making tiny progress along it. Every
    refinement below — momentum, per-coordinate scaling — is an attack on $\kappa$.

## Stochastic gradient descent

Full-batch costs $O(n)$ per step. Use a mini-batch $B_t$ of size $m$ instead:

$$
g_t = \frac{1}{m}\sum_{i \in B_t} \nabla_\theta \ell_i(\theta_{t-1}),
\qquad
\theta_t = \theta_{t-1} - \alpha g_t
$$

The essential property is **unbiasedness**: $\mathbb{E}[g_t] = \nabla\mathcal{L}$. Each step is
wrong; they're right on average. Gradient variance falls as $\sigma^2/m$, so the noise scale
falls only as $1/\sqrt{m}$ — doubling the batch buys less than you'd hope.

The noise is not purely a cost:

- **Compute.** You get $n/m$ times as many steps for the same work, and early on a 32-sample
  estimate points nearly the same way as the full gradient.
- **Saddle points.** High-dimensional loss surfaces are dominated by saddles rather than local
  minima; exact descent can stall on one, noise kicks you off.
- **Implicit regularisation.** The noise is anisotropic — larger in sharp directions — biasing
  iterates toward flat minima, which empirically generalise better.

### Why the rate must decay

!!! warning "Constant $\alpha$ does not converge"
    SGD with a fixed rate reaches a *stationary distribution*, not a point — a ball around the
    minimum of radius $\mathbb{E}\|\theta-\theta^\star\|^2 \sim \alpha\sigma^2/2\mu$ for a
    $\mu$-strongly-convex objective. Noise injects energy, the gradient pulls back, and they
    balance at a radius **proportional to $\alpha$**. To settle, $\alpha$ must shrink. This is
    the justification for every [learning-rate schedule](../pytorch/lr-schedulers.md).

The classical Robbins–Monro conditions make it precise:

$$
\sum_{t=1}^\infty \alpha_t = \infty
\qquad\text{and}\qquad
\sum_{t=1}^\infty \alpha_t^2 < \infty
$$

— the first so you can still travel arbitrarily far, the second so accumulated noise stays
finite. $\alpha_t = \alpha_0/t$ satisfies both; in practice $\alpha_0/\sqrt{t}$, cosine, and step
decay are the usable compromises.

Rates, for orientation: full-batch descent on a strongly convex problem is linear, $O(\rho^t)$;
SGD is $O(1/t)$ strongly convex and $O(1/\sqrt{t})$ convex. SGD is far slower *per step* — it
wins only because steps are $n/m$ times cheaper.

## Momentum

Replace the raw gradient with an exponentially weighted moving average:

$$
v_t = \beta v_{t-1} + g_t,
\qquad
\theta_t = \theta_{t-1} - \alpha v_t
$$

with $\beta$ typically $0.9$. Unrolled, $v_t = \sum_{k=0}^{t-1}\beta^k g_{t-k}$.

- **As a filter** — consistent gradient components accumulate toward $g/(1-\beta)$, a $10\times$
  amplification at $\beta=0.9$, while sign-flipping components cancel. In the valley picture the
  along-valley direction is amplified and the across-valley oscillation cancels.
- **As physics** — a ball with momentum rolling on the surface, $\beta$ playing
  $(1-\text{friction})$; it rolls through small bumps and flat regions instead of stopping.
- **The payoff** — with tuned $\alpha,\beta$, iteration complexity improves from $O(\kappa)$ to
  $O(\sqrt{\kappa})$. At $\kappa=10^4$ that is $100$ steps against $10^4$.
- **Effective window** is about $1/(1-\beta)$ steps, which is why raising $\beta$ usually forces
  lowering $\alpha$.

!!! warning "Two conventions"
    Some texts write $v_t = \beta v_{t-1} + (1-\beta)g_t$. That is the same recursion with
    $\alpha$ rescaled by $1/(1-\beta)$ — check which one a paper or library means before
    transferring a learning rate between them.

**Nesterov** evaluates the gradient at the look-ahead point
$\theta_{t-1} - \alpha\beta v_{t-1}$ instead of at $\theta_{t-1}$: if the momentum step is about
to overshoot, the gradient already points back. It attains the optimal $O(1/t^2)$ rate for smooth
convex problems; for deep nets the gain is real but modest.

## Adaptive methods

Momentum fixes the *direction*. It does nothing about one global $\alpha$ having to serve
coordinates whose gradients differ by orders of magnitude.

**AdaGrad** divides by the root of the accumulated squared gradient:

$$
G_t = \sum_{k=1}^{t} g_k \odot g_k,
\qquad
\theta_t = \theta_{t-1} - \frac{\alpha}{\sqrt{G_t}+\epsilon}\odot g_t
$$

Good for sparse features, but $G_t$ only grows, so the effective rate decays to zero and learning
stops. **RMSProp** fixes that by making it an exponentially weighted moving average,
$s_t = \beta_2 s_{t-1} + (1-\beta_2) g_t \odot g_t$, which can fall as well as rise.

### Adam

RMSProp + momentum + bias correction:

$$
\begin{aligned}
m_t &= \beta_1 m_{t-1} + (1-\beta_1)\, g_t && \text{first moment (mean)} \\
v_t &= \beta_2 v_{t-1} + (1-\beta_2)\, g_t \odot g_t && \text{second moment (uncentred variance)} \\
\hat{m}_t &= \frac{m_t}{1-\beta_1^{\,t}}, \qquad \hat{v}_t = \frac{v_t}{1-\beta_2^{\,t}} && \text{bias correction} \\
\theta_t &= \theta_{t-1} - \alpha\,\frac{\hat{m}_t}{\sqrt{\hat{v}_t}+\epsilon}
\end{aligned}
$$

Original defaults, essentially unchanged since: $\alpha = 10^{-3}$, $\beta_1 = 0.9$,
$\beta_2 = 0.999$, $\epsilon = 10^{-8}$.

**Bias correction** exists because $m_0 = v_0 = 0$, so $m_1 = 0.1\,g_1$ — a tenfold
underestimate. For roughly stationary gradients $\mathbb{E}[m_t] = (1-\beta_1^t)g$, so dividing
by $(1-\beta_1^t)$ is exactly unbiasing. It matters most when $t$ is small and vanishes as
$t\to\infty$. It's worse for $v$: at $\beta_2 = 0.999$ the factor is $10^{-3}$ at $t=1$, and $v$
needs ~$1/(1-\beta_2) = 1000$ steps to forget its zero start.

!!! tip "The step size is roughly $\alpha$, whatever the gradient magnitude"
    $\hat{m}_t/\sqrt{\hat{v}_t}$ is a mean estimate over a root-mean-square estimate of the same
    quantity — a signal-to-noise ratio. Consistent gradients give $\approx 1$; pure noise gives
    $\approx 0$. So Adam is nearly invariant to per-layer gradient rescaling, which is why one
    $\alpha$ transfers across architectures where SGD needs per-layer tuning.

!!! note "Adam is a diagonal preconditioner"
    Newton's method steps $-H^{-1}\nabla\mathcal{L}$ and removes the $\kappa$ dependence
    entirely, but forming $H^{-1}$ is $O(d^3)$. Adam's $1/\sqrt{\hat{v}}$ is a cheap diagonal
    stand-in: it rescales axes but cannot rotate them, so it only helps with conditioning that
    is already axis-aligned. Hence a large win on heterogeneous architectures, a modest one on a
    well-normalised convnet.

$\epsilon$ is not only numerical safety — it floors the denominator and so caps the step.
Raising it from $10^{-8}$ to $10^{-4}$ moves Adam measurably toward momentum SGD, a standard
knob for models that diverge early.

### $L^2$ regularisation is not weight decay

$L^2$ adds $\tfrac{\lambda}{2}\|\theta\|^2$ to the objective, putting $\lambda\theta$ into the
gradient. Weight decay multiplies the parameter by $(1-\alpha\lambda)$ each step. **For plain
SGD these are identical** — both give $\theta_t = (1-\alpha\lambda)\theta_{t-1} - \alpha g_t$.

For an adaptive method they are not: a gradient-borne $\lambda\theta$ gets divided by
$\sqrt{\hat{v}}$ like everything else, so coordinates with small gradient history are decayed
*more*, which is backwards. **AdamW** decouples it:

$$
\theta_t = \theta_{t-1} - \alpha\left(\frac{\hat{m}_t}{\sqrt{\hat{v}_t}+\epsilon} + \lambda\theta_{t-1}\right)
$$

This is why AdamW, not Adam, is the default for any regularised model.

### Known failure modes

- **Non-convergence.** Reddi et al. (2018) built a convex problem where Adam converges to the
  wrong point: because $v_t$ forgets, a rare large informative gradient is outweighed by frequent
  small ones. **AMSGrad** forces $\hat{v}_t = \max(\hat{v}_{t-1}, v_t)$; rarely used, since the
  pathology is rare and the fix costs adaptivity.
- **Early-training variance.** Bias correction fixes $\hat{v}_t$'s mean but not its variance, and
  early on it is estimated from very few samples. Full-size updates with a noisy denominator can
  damage a model permanently — this, not the bias, is why **warmup** is near-universal for
  transformers. **RAdam** rectifies it principledly.
- **Generalisation gap.** On well-tuned convnets, momentum SGD still finds slightly
  better-generalising minima. AdamW and a good schedule narrow it, but it's why vision benchmarks
  still report SGD.

## Comparison

| | SGD | SGD + momentum | Adam / AdamW |
|---|---|---|---|
| State per parameter | none | 1 ($v$) | 2 ($m$, $v$) |
| Attacks conditioning | no | yes — $O(\kappa)\to O(\sqrt\kappa)$ | yes, per-coordinate (diagonal) |
| Typical $\alpha$ | $10^{-1}$ | $10^{-1}$, $\beta=0.9$ | $10^{-3}$ |
| Sensitivity to $\alpha$ | high | high | low |
| Best on | convex, well-conditioned | convnets, with a schedule | transformers, embeddings, sparse |

## Related

- [Optimisers](../pytorch/optimisers.md) — these formulas as PyTorch implements them, and the
  object that holds the state
- [Learning Rate Schedulers](../pytorch/lr-schedulers.md) — the decaying $\alpha_t$ the
  convergence argument demands
- [The Training Loop](../pytorch/training-loop.md) — where the update sits among the five
  statements
