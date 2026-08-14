---
tags:
  - performance
quiz: core
---

# Broadcasting

NumPy applies element-wise operations to arrays of different shapes by *virtually stretching* smaller arrays to match — no data is copied, no Python loop is written.

## The three rules (right-to-left comparison)

1. **Pad left with 1s** — if arrays differ in rank, prepend 1s to the shorter shape.
2. **Stretch size-1 dims** — a dimension of size 1 expands to match the other array's size in that dim.
3. **Error on mismatch** — two dimensions that are neither equal nor 1 raise `ValueError`.

Output shape = element-wise max of the aligned shapes.

## Shape traces

```
# scalar + 1-D
(3,) + ()  →  pad  →  (3,) + (1,)  →  stretch  →  (3,) + (3,)  =  (3,)

# 2-D matrix − column vector
(2, 3) - (2, 1)  →  stretch col  →  (2, 3) - (2, 3)  =  (2, 3)

# outer product via row × column
(1, 3) * (3, 1)  →  stretch both  →  (3, 3) * (3, 3)  =  (3, 3)

# 3-D general case
(4, 1, 3) + (5, 3)  →  pad  →  (4, 1, 3) + (1, 5, 3)  →  (4, 5, 3)
```

## Common patterns

```python
# subtract column mean from every row
A - A.mean(axis=1, keepdims=True)     # (M, N) - (M, 1)  →  (M, N)

# normalise asset prices to start at 1  — prices shape (T, N)
prices / prices[0]                    # (T, N) / (N,)  →  (T, N)

# daily returns for all assets at once
returns = np.diff(prices, axis=0) / prices[:-1]   # (T-1, N)

# outer sum of two 1-D arrays
b[:, np.newaxis] + a                  # (M, 1) + (N,)  →  (M, N)
```

## `np.newaxis`

Insert a size-1 axis explicitly to control which dims align:

```python
a = np.array([1, 2, 3])   # (3,)
b = np.array([10, 20])    # (2,)
b[:, np.newaxis] + a      # (2, 1) + (1, 3)  →  (2, 3)  — outer sum
```

`np.newaxis` is an alias for `None`; both work identically. It's often the fix
when [indexing](indexing.md) dropped an axis you still needed.

## Why it's fast

Python loops box every number and dispatch through the interpreter on each iteration. NumPy sends the whole operation to a tight C loop over contiguous typed memory. Typical speedup: **100–500×** for arithmetic on arrays of ≥ 10 k elements. Broadcasting adds no memory overhead — a stride of 0 simulates repetition without allocation.

## Gotchas

!!! warning "keepdims is almost always required after a reduction"
    `A.mean(axis=1)` returns shape `(M,)` — this aligns on the **column** axis when broadcast back, not the row axis. Use `keepdims=True` to get `(M, 1)`, which broadcasts correctly along columns.

- `keepdims=True` is essential when reducing and then broadcasting back: `A.mean(axis=1)` gives shape `(M,)` which aligns on the wrong axis; `keepdims=True` gives `(M, 1)` which broadcasts correctly.
- Two arrays that *look* compatible may silently produce the wrong shape — always check `.shape` on intermediate results when debugging.
