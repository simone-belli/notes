---
tags:
  - testing
---

# Testing — Mocking network calls

Worked example of testing functions that make HTTP calls. The goal: test what your code does **with** the response, not whether the network is up. Never hit a real endpoint in a unit test. Core mocking concepts (`MagicMock`, `patch`, `autospec`, `side_effect`) are covered in [mocking.md](mocking.md).

## Patch at the function boundary

Mock the **outermost function that crosses a boundary you don't own**:

- Testing `fetch_price` itself (response parsing)? Mock [`httpx.get`](../../libraries/httpx.md).
- Testing code that *calls* `fetch_price` (orchestration)? Mock `fetch_price`.

## `monkeypatch` — simpler, pytest-native

```python
# mymodule.py
import httpx

def fetch_price(symbol: str) -> float:
    resp = httpx.get(f"https://api.example.com/price/{symbol}")
    resp.raise_for_status()
    return resp.json()["price"]
```

```python
def test_fetch_price(monkeypatch):
    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"price": 42.0}

    monkeypatch.setattr(mymodule.httpx, "get", lambda url: FakeResp())

    assert mymodule.fetch_price("BTC") == 42.0
```

`monkeypatch.setattr` restores the original automatically after the test.

## `unittest.mock.patch` — when you need call inspection

```python
from unittest.mock import patch, MagicMock

def test_fetch_price():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"price": 42.0}

    with patch("mymodule.httpx.get", return_value=mock_resp):
        assert mymodule.fetch_price("BTC") == 42.0
```

## Happy path

```python
def test_portfolio_value_happy(monkeypatch):
    prices = {"BTC": 30000.0, "ETH": 2000.0}
    monkeypatch.setattr("portfolio.fetch_price", lambda s: prices[s])
    assert portfolio_value(["BTC", "ETH"]) == 32000.0
```

## Partial-failure path — some symbols raise, others succeed

```python
def test_portfolio_partial_failure():
    def flaky(symbol):
        if symbol == "DOGE":
            raise httpx.HTTPStatusError("404", request=None, response=None)
        return {"BTC": 30000.0, "ETH": 2000.0}[symbol]

    with patch("portfolio.fetch_price", side_effect=flaky):
        result = portfolio_value(["BTC", "ETH", "DOGE"])

    assert result["BTC"] == 30000.0
    assert result["DOGE"] is None   # error was caught and mapped to None
```

`side_effect` also accepts a **list** — each call pops the next item; an exception class is raised, a value is returned:

```python
with patch("mymodule.httpx.get", side_effect=[httpx.TimeoutException(""), mock_resp]):
    assert fetch_price_with_retry("BTC") == 42.0   # retried after timeout
```

## Patch where it's used, not where it's defined

!!! warning "Patch where the name is *used*, not where it's *defined*"
    `from httpx import get` binds `get` in `mymodule`'s namespace. Patching `httpx.get` replaces the original, but `mymodule.get` still points to the old function. The rule: patch the dotted path of the name as it appears in the module under test, e.g. `"mymodule.get"`. If it uses `import httpx`, patch `"mymodule.httpx.get"`.

```python
# mymodule.py uses:  from httpx import get
with patch("httpx.get", ...):      # WRONG — has no effect in mymodule
with patch("mymodule.get", ...):   # RIGHT
```

If the module uses `import httpx` and calls `httpx.get(...)`, patch `"mymodule.httpx.get"`.

## Decision guide

| Situation | Use |
|-----------|-----|
| Simple replacement, no call inspection | `monkeypatch.setattr` |
| Need to count calls or inspect args | `patch(..., autospec=True)` |
| Guard against signature drift | `autospec=True` / `create_autospec` |
| Own repo/gateway interface | in-memory fake behind a `Protocol`, not a mock |
| Sequential call sequence (first fails, second succeeds) | `side_effect=[...]` list |
| Async network call | `patch` + [`AsyncMock`](mocking.md#asyncmock) |
| Whole client under test, not one call | `httpx.MockTransport` — no patching at all |

## Related notes

- [`mocking.md`](mocking.md) — Mock/MagicMock mechanics, autospec, AsyncMock, when to mock
- [`testing-patterns.md`](testing-patterns.md) — seam-based isolation: file/DB deps, stdout, DI strategies
