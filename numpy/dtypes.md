# dtypes

A dtype is the contract that makes NumPy arrays fast: every element occupies exactly the same number of bytes, laid out contiguously in memory, with no per-element Python overhead. The CPU can stride through the block predictably and operate on multiple elements per clock cycle.

## Common dtypes

| Family | Types | Default |
|--------|-------|---------|
| Signed int | `int8` `int16` `int32` `int64` | `int64` |
| Unsigned int | `uint8` `uint16` `uint32` `uint64` | — |
| Float | `float16` `float32` `float64` | `float64` |
| Complex | `complex64` `complex128` | — |
| Bool | `bool` | — |
| Object | `object` | fallback for mixed/string |

## Specifying and inspecting

```python
a = np.array([1, 2, 3], dtype=np.float32)
a.dtype            # dtype('float32')
a.dtype.itemsize   # 4 bytes
a.nbytes           # 12 bytes total

np.zeros((100, 100), dtype=np.uint8)
np.array([1, 2, 3], dtype='f4')   # shorthand: 'f4'=float32, 'i2'=int16, 'u4'=uint32
```

## Type inference from literals

```python
np.array([1, 2, 3])        # int64
np.array([1.0, 2.0])       # float64
np.array([1, 2, 3.0])      # float64  (mixed → upcast)
np.array([True, False])    # bool
np.array([1, 'a'])         # object  (heterogeneous → fallback, loses all speed)
```

## Casting

```python
a = np.array([1.7, 2.9])
a.astype(np.int32)                      # [1, 2] — truncates, no rounding
a.astype('float32')                     # halves memory
a.astype(np.int32, casting='safe')      # raises TypeError — float→int not safe
```

`casting` options: `'safe'`, `'same_kind'`, `'unsafe'` (default, no check).

## Precision limits

```python
np.finfo(np.float32)   # ~7 decimal digits, max ~3.4e38
np.finfo(np.float64)   # ~15 decimal digits, max ~1.8e308
np.iinfo(np.int8)      # min=-128, max=127
```

## Gotchas

**Silent integer overflow** — no error, wraps around:
```python
np.int8(127) + np.int8(1)   # -128
```

**No NaN in integer arrays** — NaN is a float concept:
```python
np.array([1, 2, np.nan])   # silently becomes float64
```

**`np.int_` is platform-dependent** — maps to C `long` (64-bit on Linux/macOS, 32-bit on some Windows). Use explicit `np.int32` / `np.int64` for reproducibility.

**`object` dtype is a trap** — stores Python object pointers; all vectorisation is lost. Avoid unless data is genuinely heterogeneous.

## Memory layout and [broadcasting](broadcasting.md)

The fixed-width contiguous layout is what makes [broadcasting](broadcasting.md) zero-copy: a stride of 0 simulates repetition without allocating a new array.
