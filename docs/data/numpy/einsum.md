---
tags:
  - performance
---

# einsum

`np.einsum` evaluates a tensor expression written in **Einstein summation notation**: label every axis of every operand with a letter, list the letters the output keeps, and NumPy multiplies along matching letters and sums over the rest. One notation replaces `dot`, `@`, `outer`, `trace`, `transpose`, and `sum(axis=...)`, with the axis bookkeeping written out in the call.

## Reading the string

```python
import numpy as np

C = np.einsum("ij,jk->ik", A, B)   # same as A @ B
```

The string is the formula with $\sum$ and the multiplication removed:

$$
C_{ik} = \sum_j A_{ij}\, B_{jk}
$$

- One letter per axis — the count must equal the operand's `ndim`.
- The **same letter** across operands pairs those axes; they must be equal length (or 1, which [broadcasts](broadcasting.md)).
- A letter repeated **within** one operand (`"ii"`) takes the diagonal.
- Output letters are kept, **in the order written** — that order is a transpose.
- Letters **missing from the output are summed over**.

!!! note "Mental model: letters are loop indices"
    Every letter is a nested `for` loop. The body multiplies one element from each operand; letters after `->` index where the product is added, and the others are summed out.

## Common patterns

| operation | formula | string |
|---|---|---|
| transpose | $B_{ji} = A_{ij}$ | `"ij->ji"` |
| column sums | $s_j = \sum_i A_{ij}$ | `"ij->j"` |
| trace | $\sum_i A_{ii}$ | `"ii->"` |
| diagonal | $d_i = A_{ii}$ | `"ii->i"` |
| inner product | $\sum_i u_i v_i$ | `"i,i->"` |
| outer product | $M_{ij} = u_i v_j$ | `"i,j->ij"` |
| matrix–vector | $y_i = \sum_j A_{ij} v_j$ | `"ij,j->i"` |
| batched matmul | $C_{bik} = \sum_j A_{bij} B_{bjk}$ | `"bij,bjk->bik"` |
| row-wise dot | $r_i = \sum_j A_{ij} B_{ij}$ | `"ij,ij->i"` |
| quadratic form | $\sum_{ij} x_i A_{ij} x_j$ | `"i,ij,j->"` |

`...` stands for any number of broadcast leading axes, so `"...ij,...jk->...ik"` is `@` for arbitrary batch shapes.

```python
# batched bilinear form, no intermediate (B, N) temporaries
y = np.einsum("bi,ij,bj->b", x, W, z, optimize=True)
```

## Performance and `optimize`

- With **two operands**, einsum runs one C loop and avoids the full `A * B` temporary — good for things like row-wise dot products.
- With **three or more**, the default `optimize=False` loops over *all* letters at once: `"ij,jk,kl->il"` costs $O(n^4)$ instead of the $O(n^3)$ of `(A @ B) @ C`.
- `optimize=True` (`"greedy"`) or `"optimal"` plans a pairwise contraction order and hands steps to BLAS (Basic Linear Algebra Subprograms) where it can.
- `np.einsum_path(...)` prints the plan and estimated savings; pass the returned path as `optimize=path` to skip re-planning in a hot loop.
- For a plain matrix multiply, `@` is as fast or faster — reach for einsum when the axis bookkeeping is the hard part.

!!! tip "Always pass `optimize=True` with 3+ operands"
    The unoptimised path is correct but can be orders of magnitude slower on large arrays.

## Gotchas

!!! warning "Implicit mode sorts the output letters"
    Without `->`, the output is every letter appearing once, **alphabetically**. `np.einsum("ij,jk", A, B)` is matmul, but `np.einsum("ba", A)` is a transpose. Always write the arrow.

- **No integer upcast** — einsum accumulates in the input dtype, so an `int8` sum overflows where `np.sum` would not ([dtypes](dtypes.md)). Cast first or pass `dtype=`.
- **Some results are views** — `"ij->ji"` and `"ii->i"` can return a view of the input (the diagonal one read-only), like basic [indexing](indexing.md).
- **Case-sensitive labels** — `i` and `I` are different axes.
- **Portable syntax** — the same strings work in `torch.einsum` and `jax.numpy.einsum`.
