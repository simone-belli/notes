---
tags:
  - testing
quiz: detail
---

# Hypothesis

Property-based testing: instead of hand-picking inputs, you declare *invariants* that must hold for all valid inputs, and Hypothesis generates hundreds of random cases to falsify them. When a failure is found, it **shrinks** the input to the smallest counterexample.

Install: `pip install hypothesis` (integrates with [pytest](pytest.md) natively, no plugin needed).

## Core pattern

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers(), min_size=1))
def test_reverse_is_involution(xs):
    assert list(reversed(list(reversed(xs)))) == xs
```

`@given` injects generated values; the test runs ~100 times (default).

## Strategies

Strategies (`st.*`) are recipes for generating data:

```python
st.integers(min_value=0, max_value=100)
st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)
st.text()
st.lists(st.integers(), min_size=1, max_size=50)
st.one_of(st.integers(), st.none())
```

Compose freely: `st.lists(st.floats(...), min_size=1)`.

## Multiple parameters

`@given` accepts one strategy per test argument — positional or keyword — and draws each independently every example:

```python
@given(st.integers(), st.integers())
def test_add_commutative(a, b):
    assert a + b == b + a

@given(a=st.integers(min_value=0), b=st.floats(allow_nan=False))
def test_mixed_kwargs(a, b):
    ...
```

When parameters must be *related* (e.g. `low <= high`), don't generate them independently and filter — Hypothesis may discard most examples before finding a valid one. Use `st.composite` to draw dependently instead:

```python
from hypothesis import strategies as st

@st.composite
def low_high(draw):
    low = draw(st.integers(min_value=0, max_value=100))
    high = draw(st.integers(min_value=low, max_value=100))
    return low, high

@given(low_high())
def test_range(pair):
    low, high = pair
    assert low <= high
```

!!! tip "Filtering vs composite"
    `st.tuples(a, b).filter(lambda p: p[0] <= p[1])` works but wastes examples on rejected draws; `st.composite` builds only valid combinations and shrinks them together.

## Property patterns

| Pattern | Example assertion |
|---|---|
| Invariant | `result <= 0` always |
| Round-trip | `decode(encode(x)) == x` |
| Commutativity | `f(a, b) == f(b, a)` |
| Idempotence | `f(f(x)) == f(x)` |
| Boundary | `f([x]) == base_case` |

## `max_drawdown` example

Maximum Drawdown (MDD) = largest peak-to-trough decline in a cumulative return series.

```python
def max_drawdown(returns: list[float]) -> float:
    cumulative = peak = 1.0
    max_dd = 0.0
    for r in returns:
        cumulative *= (1 + r)
        peak = max(peak, cumulative)
        max_dd = min(max_dd, (cumulative - peak) / peak)
    return max_dd
```

Three properties that always hold:

```python
from hypothesis import given, strategies as st

_returns = st.lists(
    st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
    min_size=1,
)

@given(_returns)
def test_nonpositive(returns):        # Property 1: sign contract
    assert max_drawdown(returns) <= 0

@given(st.lists(
    st.floats(min_value=0, max_value=0.5, allow_nan=False, allow_infinity=False),
    min_size=1,
))
def test_nonneg_returns(returns):     # Property 2: no decline → no drawdown
    assert max_drawdown(returns) == 0.0

@given(st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False))
def test_single_element(r):           # Property 3: base case
    assert max_drawdown([r]) == 0.0
```

!!! note "Why bound the floats?"
    `min_value=-0.5, max_value=0.5` keeps cumulative return away from 0 and ∞, preventing `nan` from IEEE 754 edge cases masking actual bugs. Test NaN behaviour separately if needed.

!!! tip "Shrinking"
    If Property 1 fails on `[0.1, -0.2, 0.3]`, Hypothesis shrinks it to `[-0.1]` — the minimal list that still triggers the bug. Fix the implementation to handle that case and the shrunk example becomes the regression anchor.

## Settings

```python
from hypothesis import settings, HealthCheck

@settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
@given(_returns)
def test_nonpositive(returns):
    assert max_drawdown(returns) <= 0
```

- `max_examples` (default 100): number of passing cases to generate.
- `deadline`: fail if one example exceeds N ms (default 200ms).
- `.hypothesis/` directory: Hypothesis stores failures across runs and replays them first on the next run.

## Pin explicit cases alongside properties

```python
from hypothesis import example

@given(_returns)
@example([-0.5])   # always runs, acts as a regression test
def test_nonpositive(returns):
    assert max_drawdown(returns) <= 0
```

## Hypothesis vs parametrize

| Scenario | Use |
|---|---|
| Known edge cases | `@pytest.mark.parametrize` |
| Mathematical invariants | `@given` |
| Round-trip / commutativity | `@given` |
| Side-effect-heavy integration | plain pytest fixtures |
