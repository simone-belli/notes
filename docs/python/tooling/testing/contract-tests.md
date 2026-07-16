---
tags:
  - testing
  - design-patterns
---

# Testing — Contract Tests

When you have two or more concrete classes that share an interface ([`Protocol`](../../language/objects/typing/structural-typing.md)), run the same test suite against all of them with a **parametrized [fixture](fixtures.md)** — no test duplication, no `isinstance`.

## The fixture

```python
import pytest
from pathlib import Path

@pytest.fixture(params=["memory", "jsonl"])
def store(request, tmp_path) -> TradeStore:
    if request.param == "memory":
        return InMemoryTradeStore()
    if request.param == "jsonl":
        return JsonlTradeStore(tmp_path / "trades.jsonl")
```

`params` tells pytest to run every dependent test once per value. Test names get the param appended automatically: `test_empty[memory]`, `test_empty[jsonl]`.

## Tests talk only to the Protocol

```python
def test_empty_store(store: TradeStore):
    assert store.get_all() == []

def test_added_trade_is_retrievable(store: TradeStore):
    t = Trade(symbol="AAPL", qty=10, price=182.5)
    store.add(t)
    assert store.get_all() == [t]
```

No branching, no `request.param` access, no `isinstance` — the tests are completely agnostic.

## If a test needs to know which implementation it has, the abstraction is leaking

```python
# BAD — test reaches into the implementation
def test_persistence(store, request):
    if request.param == "jsonl":    # breaks the contract abstraction
        ...
```

Fix: ask whether the behaviour is part of the **contract** or specific to one implementation.

- **Contract behaviour** (required by the Protocol) → fix the test to work on all impls.
- **Implementation-specific behaviour** → write a standalone test against the concrete class directly:

```python
# GOOD — tests JsonlTradeStore explicitly, not through the shared fixture
def test_jsonl_creates_file_on_first_add(tmp_path):
    store = JsonlTradeStore(tmp_path / "trades.jsonl")
    store.add(Trade(symbol="AAPL", qty=10, price=182.5))
    assert (tmp_path / "trades.jsonl").exists()
```

!!! tip "Diagnostic question"
    When you reach for `request.param` or `isinstance` inside a parametrized test, ask: *is this behaviour required by the interface, or specific to one implementation?* The answer tells you whether to fix the test or extract a standalone one.

## Adding a third implementation

Add one string to `params` and one branch to the fixture. All existing tests gain a third run for free.

## Related notes

- [`testing-patterns.md`](testing-patterns.md) — dependency seams, `tmp_path`, capturing stdout
- [`repository-di.md`](../../language/objects/repository-di.md) — the Protocol + fake pattern these tests exercise
- [`pytest.md`](pytest.md) — command quick-reference
