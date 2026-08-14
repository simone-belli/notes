---
tags:
  - performance
quiz: core
---

# Indexing and Slicing

An array is three things: a flat **data buffer**, a **shape**, and a **strides**
tuple giving the byte step along each axis. Element `a[i, j]` lives at
`offset + i*s0 + j*s1` — that formula is the whole indexing engine.

```python
a = np.arange(12).reshape(3, 4)
a.strides     # (32, 8) — 8 bytes per int64, so a 4-element row is 32 bytes
```

**A basic slice copies nothing.** It builds a new (shape, strides, offset)
triple over the same buffer. That single fact explains both why slicing a 1 GB
array is instant and why writing through a slice mutates the original.

## Basic slicing

`start:stop:step` per axis, comma-separated; an axis you don't mention is taken
in full.

```python
a = np.arange(10)
a[2:5]        # [2 3 4]      stop exclusive
a[::2]        # [0 2 4 6 8]  step
a[::-1]       # reversed — still a view
a[-3:]        # last three

A = np.arange(12).reshape(3, 4)
A[1]          # row 1 — same as A[1, :]
A[:, 2]       # column 2
A[0:2, 1:3]   # sub-block
```

- Bounds defaults are **direction-aware**: with a negative step, omitted `start`
  means the last element. `a[5::-1]` keeps element 0; `a[5:0:-1]` drops it.
- Slices **clamp**, integers **raise**: `a[5:99]` on a length-3 array returns an
  empty array, while `a[5]` is an `IndexError`.

!!! warning "Integers drop an axis, slices keep it"
    `A[:, 2]` has shape `(3,)`; `A[:, 2:3]` has shape `(3, 1)`. An integer
    *consumes* an axis, a slice *narrows* one. This is the root of most shape
    bugs — use `2:3` (or `np.newaxis`) when a later step needs the axis to still
    exist for [broadcasting](broadcasting.md).

### `...` and `np.newaxis`

```python
T = np.random.rand(4, 5, 6, 7)
T[..., 0]     # (4, 5, 6) — last axis indexed, the rest in full
T[0, ...]     # (5, 6, 7)

a[:, np.newaxis].shape   # (3,) → (3, 1); newaxis is literally None
```

`...` expands to as many full slices as needed and may appear once. It's what
makes code rank-agnostic: `T[..., -1]` works whatever `T.ndim` is.

## Advanced (fancy) indexing

The moment an index is an **array** of integers or booleans, NumPy must gather
elements into a freshly allocated array.

```python
a[[0, 2, 4]]        # pick in any order; repeats allowed
a[a > 0]            # boolean mask → always 1-D, length = count of True
a[(a > 0) & (a < 5)]
A[A.sum(axis=1) > 10]     # mask one axis to select whole rows
```

Multiple integer index arrays are **broadcast against each other and paired
element-wise** — they do *not* form a cross-product:

```python
A[[0, 1, 2], [3, 2, 1]]   # the points (0,3), (1,2), (2,1)

rows, cols = np.array([0, 2]), np.array([1, 3])
A[np.ix_(rows, cols)]     # (2, 2) sub-GRID — np.ix_ does the broadcasting
```

!!! warning "`and`/`or`/`not` don't work on arrays"
    They call `bool()` and raise *"truth value of an array … is ambiguous"*. Use
    `&`, `|`, `~` — and parenthesise: `&` binds tighter than `>`, so
    `a > 0 & a < 5` parses as nonsense.

Mixing a slice *between* two advanced indices moves the gathered axis to the
front of the result — a genuine wart. Index in two steps, or use
`np.take_along_axis(A, idx, axis=)`, which never reorders.

## Views vs copies

| Indexing | Returns | Writes reach the original |
|---|---|---|
| Basic slice — `a[1:5]`, `a[::2]`, `a[..., 0]` | **view** | **yes** |
| Integer array — `a[[0, 2]]` | copy | no |
| Boolean mask — `a[a > 0]` | copy | no |

```python
v = a[2:5];   v[0] = 999      # a is modified
f = a[[2,3]]; f[0] = 999      # a is not

np.shares_memory(a, v)        # True — the reliable check
v.flags['OWNDATA']            # False for a view
```

- Call `.copy()` when you mean a copy; slicing out scratch data and mutating it
  silently corrupts the parent.
- A view keeps the **whole** parent buffer alive via `.base` — 10 elements
  sliced from a 1 GB array retain 1 GB until you `.copy()`.

Assignment *through* a mask still works — `a[a < 0] = 0` calls `__setitem__`,
which scatters into the original buffer, while the read `a[a < 0]` must
materialise a copy. Only **chained** indexing breaks: `a[mask][0] = 5` writes to
a temporary and is lost. That mechanism is exactly pandas'
[`SettingWithCopyWarning`](../pandas/indexing.md).

!!! note "`a[[0, 0]] += 1` increments once, not twice"
    Augmented assignment on fancy indices is unbuffered — read, add, write back
    in one pass — so duplicate indices overwrite instead of accumulating. Use
    `np.add.at(a, [0, 0], 1)` or `np.bincount` when indices repeat.

## Contiguity

Slicing is free, but the result may be strided, and strided memory defeats cache
prefetching.

```python
A[0, :].flags['C_CONTIGUOUS']   # True  — rows are contiguous runs
A[:, 0].flags['C_CONTIGUOUS']   # False — columns step by the row width
```

- Prefer working along the **last** axis in C (row-major) order.
- `.reshape()` is a free view on contiguous data and a copy otherwise;
  `.flatten()` always copies, `.ravel()` only when it must.
- `A.T` is a pure stride swap — free, and non-contiguous by construction.
- `np.ascontiguousarray(x)` forces the copy before heavy work on a strided view.

## Patterns

```python
a[1:] - a[:-1]                        # adjacent differences
A[np.arange(3), idx]                  # one element per row, column given by idx
A[np.triu_indices(3, k=1)]            # upper triangle — unique pairs
np.where(a > 0, a, 0)                 # element-wise ternary
np.where(a > 0)                       # the indices where true
```

Sliding windows, purely by manufacturing strides:

```python
from numpy.lib.stride_tricks import sliding_window_view

w = sliding_window_view(np.arange(10), 4)   # (7, 4) VIEW — no data copied
w.mean(axis=1)                              # rolling mean, no Python loop
```

It's read-only by design: overlapping windows share buffer elements, so writes
would be ambiguous.

## Related

- [Broadcasting](broadcasting.md) — how shapes align once you've sliced them
- [dtypes](dtypes.md) — the itemsize that strides are counted in
- [Pandas — Indexing, Views and Copies](../pandas/indexing.md) — the same
  view/copy problem one layer up
