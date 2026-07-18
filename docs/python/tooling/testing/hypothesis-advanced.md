---
tags:
  - testing
quiz: detail
---

# Hypothesis — Advanced Strategies

Techniques beyond the [core `@given`/strategies pattern](hypothesis.md): shaping strategies to match domain constraints instead of discarding invalid draws, generating structured and dependent data, and reproducing a specific failure deterministically.

## Constrain, don't filter

`assume(condition)` and `.filter(predicate)` both generate a candidate and discard it if false — same cost, different timing. Every discarded example still counts against the example budget; too high a discard rate raises `FailedHealthCheck` (`HealthCheck.filter_too_much`) instead of silently retrying forever.

```python
# Wastes ~50% of draws
@given(st.integers(), st.integers())
def test_range(low, high):
    assume(low <= high)
    ...

# Can't generate an invalid pair
@st.composite
def ordered_pair(draw):
    low = draw(st.integers())
    high = draw(st.integers(min_value=low))
    return low, high
```

Filtering is fine for cheap, rarely-triggered exclusions (`.filter(lambda x: x != 0)`); it becomes a problem when two draws are tightly coupled, which is exactly when `st.composite` pays off.

## Bounding `st.floats`

`st.floats()` with no arguments generates the full IEEE 754 space — NaN, ±infinity, subnormals included — because a float-typed parameter accepts them just as validly as `3.14`. `allow_nan=False`, `allow_infinity=False`, and a bounded `min_value`/`max_value` are **domain statements**, not workarounds: each says "this quantity cannot be NaN / infinite / out of range" in this specific system. Make that claim consciously — checking it actually holds — rather than adding it just to silence a failing assertion like `x == x`. If NaN handling is part of the contract, test it separately instead of folding it into the same strategy as everything else.

## Generating valid Pydantic models with `st.builds`

`st.builds(cls, **kwargs)` calls `cls(**kwargs)` with each keyword drawn from its strategy — works for any callable, including a [Pydantic](../../libraries/pydantic/pydantic.md) `BaseModel`:

```python
trades = st.builds(
    Trade,
    symbol=st.text(min_size=1, max_size=10),
    price=st.decimals(min_value="0.01", max_value="100000", places=2),
    qty=st.integers(min_value=1, max_value=10_000),
    side=st.sampled_from(['BUY', 'SELL']),
)
```

Modern Hypothesis registers hooks for installed Pydantic models, so `st.builds(Trade)` alone can infer strategies from field types — handy for smoke-testing, less useful when you need to steer specific fields toward boundary values.

!!! note "Hypothesis and Pydantic disagree about 'valid'"
    `st.text()` describes what the *type system* allows; `Field(..., min_length=1)` describes what the *domain* allows. `st.text()` happily generates `""`, which then raises `ValidationError` — a strategy that doesn't mirror the `Field` constraints wastes most of its draws on rejected instances. Similarly, `st.decimals()` can generate `Decimal("NaN")` by default (same philosophy as `st.floats()` above), which fails a `Field(..., gt=0)` check every time. The fix is the same as above: tighten the strategy to mirror the constraint, not filter after the fact.

## Composite strategies with shared, dependent structure

`@st.composite` draws values sequentially, using earlier draws to parameterize later ones — the tool for structure that independent strategies can't express, like a portfolio where every trade shares a small symbol pool and timestamps stay ordered:

```python
@st.composite
def portfolios(draw, min_trades=1, max_trades=20):
    symbols = draw(st.lists(
        st.text(alphabet=st.characters(whitelist_categories=["Lu"]), min_size=1, max_size=4),
        min_size=1, max_size=5, unique=True,
    ))
    n = draw(st.integers(min_value=min_trades, max_value=max_trades))

    timestamps = [draw(st.datetimes())]
    for _ in range(n - 1):
        offset = draw(st.integers(min_value=1, max_value=3600))
        timestamps.append(timestamps[-1] + timedelta(seconds=offset))

    trades = draw(st.lists(
        st.builds(Trade, symbol=st.sampled_from(symbols), ...),  # shared pool, not per-trade
        min_size=n, max_size=n,
    ))
    return list(zip(timestamps, trades))
```

Ordering timestamps by appending `previous + offset` guarantees the invariant by construction — no post-hoc sort that would mask a real ordering bug in the code under test. Composite strategies also shrink coherently: because later draws depend on earlier ones, shrinking preserves the relationships (fewer trades, smaller offsets) instead of producing an incoherent partial state.

## Reproducing a failure with the example blob

`@settings(print_blob=True)` prints an encoded reproduction blob alongside a falsifying example:

```
Falsifying example: test_range(pair=(3, 1))
You can add @reproduce_failure('6.100.0', b'AXicY2BAAAAAOgAB') as a decorator
on this test to reproduce this failure.
```

Pasting `@reproduce_failure(...)` onto the test replays that exact generated value deterministically, bypassing the random search — useful when a failure came from a complex composite value (a whole generated portfolio) that's tedious to reconstruct from the printed repr, or when a fresh `@given` run wouldn't hit the same case again. It's version-pinned to the Hypothesis release that produced it, so treat it as a short-term local reproduction aid — once you've isolated the concrete failing value, promote it to a permanent `@example(...)` and delete the decorator.
