# dtypes

Pandas wraps [NumPy dtypes](../numpy/dtypes.md) for numeric columns, then adds extension types that fix NumPy's practical gaps: no nullable integers, slow strings, and no categorical type.

## Inspecting

```python
df.dtypes                    # Series: column → dtype
df.dtypes.value_counts()     # how many columns of each type
df.memory_usage(deep=True)   # actual bytes; deep=True measures object columns correctly
```

## The string problem: `object` dtype

Without explicit configuration, pandas stores string columns as NumPy `object` arrays — each cell is a Python `str` on the heap. No contiguous memory, no vectorisation, large memory footprint.

```python
df['name'].dtype    # dtype('O')  ← object

# Fix: use StringDtype (pandas 1.0+)
df['name'] = df['name'].astype('string')
df['name'].dtype    # StringDtype()
```

`StringDtype` is backed by a more efficient Arrow or NumPy structure and propagates `pd.NA` for missing values (not `np.nan`).

## Nullable integer types

Plain NumPy `int64` cannot hold `NaN`. Any integer column with a missing value silently becomes `float64` in old pandas. The nullable extension integers fix this — capital I:

```python
pd.array([1, 2, None], dtype='Int64')   # Int64 — nullable, missing = pd.NA
pd.array([1, 2, None], dtype='int64')   # float64 — lowercase = NumPy, None→NaN
```

Capital-I types: `Int8`, `Int16`, `Int32`, `Int64`, `UInt8`, …, `BooleanDtype`.

## `pd.NA` vs `np.nan` vs `None`

| Value | Type | Used in |
|-------|------|---------|
| `None` | Python object | `object` columns, Python containers |
| `np.nan` | float64 | NumPy, float columns, old pandas |
| `pd.NA` | NAType | Nullable extension types (Int64, StringDtype, BooleanDtype) |

They don't compare equal and behave differently in boolean contexts. Don't mix them across columns.

## `CategoricalDtype`

For low-cardinality string or integer columns (country, status, grade): stores integer codes + a small lookup table instead of full strings per row.

```python
df['status'] = df['status'].astype('category')

# Ordered categorical — enables comparisons
from pandas import CategoricalDtype
size_type = CategoricalDtype(['S', 'M', 'L', 'XL'], ordered=True)
df['size'] = df['size'].astype(size_type)
df[df['size'] > 'M']   # works because ordered=True
```

Benefits: lower memory, faster `groupby` and `value_counts` (operate on integer codes).

## Dtype fix-up pattern (after loading)

```python
# Downcast numerics
df['price'] = df['price'].astype('float32')   # if float64 precision not needed
df['count'] = df['count'].astype('int32')

# Fix string columns
for col in df.select_dtypes('object').columns:
    df[col] = df[col].astype('string')

# Fix low-cardinality columns
for col in ['country', 'status', 'tier']:
    df[col] = df[col].astype('category')
```

## Interop with NumPy

NumPy-backed columns (standard int/float/bool) share memory; `.to_numpy()` returns a view:

```python
arr = df['price'].to_numpy()   # no copy for NumPy-backed columns
```

Extension type columns (Int64, StringDtype, Categorical) are **not** backed by plain NumPy arrays. `.to_numpy()` allocates a new array, often `dtype=object`. Be explicit:

```python
df['count'].to_numpy(dtype=float, na_value=np.nan)   # converts pd.NA → np.nan
```

## Gotchas

- `object` dtype silently defeats all pandas/NumPy performance — always check after loading CSV or joining.
- `float32` has only ~7 significant digits; if you're accumulating sums or doing statistical calculations, stick with `float64`.
- Mixing `pd.NA` and `np.nan` in the same column produces inconsistent `.isna()` behaviour in some older pandas versions.
