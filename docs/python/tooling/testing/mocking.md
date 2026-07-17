---
tags:
  - testing
  - concurrency
quiz: core
---

# Testing — Mocking

Patterns for replacing dependencies with controlled substitutes. Use mocks when you can't inject a seam (see [testing-patterns.md](testing-patterns.md)) or when you need to assert a side effect was triggered.

## When to mock at all — the decision rule

- **Mock boundaries you don't own** — network, clock, randomness, filesystem at the true edge. Slow, nondeterministic, unavailable in CI; patch the outermost function of *yours* that touches them.
- **Use real fakes behind Protocols for seams you do own** — e.g. an `InMemoryTradeRepo` that actually behaves correctly (see [repository-di.md](../../language/objects/repository-di.md)). Fakes catch logic bugs in callers and survive refactors; mocks only verify "the right method was called" and break when internals change.
- **Never mock the thing under test** — patching a method of the class being tested makes the test exercise the mock, not the code; passing is vacuous. If tempted, split the collaborator out behind a seam and fake that.
- Prefer asserting state/output over asserting calls; assert calls only when the side effect *is* the behaviour ("an alert was sent"). See [testing-strategy.md](testing-strategy.md) for the broader philosophy.

## MagicMock

`MagicMock` accepts any attribute access or method call without raising `AttributeError` — returning a new child `MagicMock` each time. It's a stand-in for any object without needing to subclass it.

```python
from unittest.mock import MagicMock

m = MagicMock()
m.foo()                  # → MagicMock
m.bar.baz.qux            # → MagicMock (arbitrary depth)
```

**Set return values:**

```python
m.get_price.return_value = 42.0
m.session.get.return_value.json.return_value = {"price": 42.0}   # chained
```

**Side effects** — overrides `return_value`:

```python
m.fetch.side_effect = ValueError("bad")             # always raises
m.fetch.side_effect = [42.0, 43.0, ValueError()]    # sequential — pops per call
m.fetch.side_effect = lambda s: PRICES[s]           # dynamic
```

**Call inspection:**

```python
m.send_alert.assert_called_once()
m.send_alert.assert_called_once_with("BTC", threshold=1000)
m.send_alert.assert_not_called()
m.send_alert.call_count          # int
m.send_alert.call_args           # most recent: (args, kwargs)
m.send_alert.call_args_list      # all calls in order
```

`unittest.mock.ANY` is an equality wildcard that matches anything:

```python
m.send.assert_called_once_with(to="ops@example.com", body=ANY)
```

**`spec`** — constrains the mock to a real class's interface; typos raise `AttributeError`:

```python
m = MagicMock(spec=Notifier)
m.sned_email(...)   # AttributeError — typo caught immediately
```

`spec` checks attribute *names* only — it does **not** validate call signatures.

**`autospec=True`** — builds the mock recursively from the real object, so every method enforces the real signature; wrong arguments raise `TypeError`. This catches **API drift**: with a bare mock, `m.assert_called_once_with("BTC", threshold=1000)` keeps passing after the real function is refactored to `send_alert(symbol, *, limit)` — the suite stays green while production breaks.

```python
with patch("mymodule.send_alert", autospec=True) as m:
    run_checks()
m.assert_called_once_with("BTC", threshold=1000)   # TypeError if signature drifted
```

Use `autospec=True` on `patch` by default (`create_autospec(obj)` for standalone mocks). Fall back to `spec=`/bare mocks only for attributes created dynamically at runtime (e.g. set in `__init__`), which autospec can't see.

!!! note "MagicMock vs Mock"
    `Mock` records calls and returns a child mock for any attribute — but dunder methods are looked up on the *type*, so `len(m)`, `list(m)`, or `with m:` raise `TypeError` on a plain `Mock`. `MagicMock` pre-wires the dunders (`__len__`, `__iter__`, `__enter__`, `__exit__`, …), so it works as a container, iterator, or context manager. Use `MagicMock` by default; drop to `Mock` only if you want dunder access to fail loudly.

## Testing functions that make network calls

The goal: test what your code does **with** the response, not whether the network is up. Never hit a real endpoint in a unit test.

### Patch at the function boundary

Mock the **outermost function that crosses a boundary you don't own**:

- Testing `fetch_price` itself (response parsing)? Mock `httpx.get`.
- Testing code that *calls* `fetch_price` (orchestration)? Mock `fetch_price`.

### `monkeypatch` — simpler, pytest-native

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

### `unittest.mock.patch` — when you need call inspection

```python
from unittest.mock import patch, MagicMock

def test_fetch_price():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"price": 42.0}

    with patch("mymodule.httpx.get", return_value=mock_resp):
        assert mymodule.fetch_price("BTC") == 42.0
```

### Happy path

```python
def test_portfolio_value_happy(monkeypatch):
    prices = {"BTC": 30000.0, "ETH": 2000.0}
    monkeypatch.setattr("portfolio.fetch_price", lambda s: prices[s])
    assert portfolio_value(["BTC", "ETH"]) == 32000.0
```

### Partial-failure path — some symbols raise, others succeed

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

### Patch where it's used, not where it's defined

!!! warning "Patch where the name is *used*, not where it's *defined*"
    `from httpx import get` binds `get` in `mymodule`'s namespace. Patching `httpx.get` replaces the original, but `mymodule.get` still points to the old function. The rule: patch the dotted path of the name as it appears in the module under test, e.g. `"mymodule.get"`. If it uses `import httpx`, patch `"mymodule.httpx.get"`.

```python
# mymodule.py uses:  from httpx import get
with patch("httpx.get", ...):      # WRONG — has no effect in mymodule
with patch("mymodule.get", ...):   # RIGHT
```

If the module uses `import httpx` and calls `httpx.get(...)`, patch `"mymodule.httpx.get"`.

### Decision guide

| Situation | Use |
|-----------|-----|
| Simple replacement, no call inspection | `monkeypatch.setattr` |
| Need to count calls or inspect args | `patch(..., autospec=True)` |
| Guard against signature drift | `autospec=True` / `create_autospec` |
| Own repo/gateway interface | in-memory fake behind a `Protocol`, not a mock |
| Sequential call sequence (first fails, second succeeds) | `side_effect=[...]` list |
| Async network call | `patch` + `AsyncMock` |

## Testing async code

Without pytest-asyncio, `async def test_*` returns a coroutine object that pytest never awaits — the body never runs and the test passes vacuously.

```bash
poetry add --group dev pytest-asyncio
```

Enable globally in `pyproject.toml` so every `async def test_*` is automatically run in an event loop:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Without `asyncio_mode = "auto"`, decorate each async test individually:

```python
@pytest.mark.asyncio
async def test_fetch():
    result = await fetch(url)
    assert result["status"] == "ok"
```

### AsyncMock

!!! warning "MagicMock is not awaitable — use AsyncMock for async functions"
    `await MagicMock()()` raises `TypeError`. `AsyncMock` makes the mock awaitable and makes its return value also an async mock, so `await mock.json()` works without extra setup.

```python
from unittest.mock import AsyncMock, MagicMock, patch

async def test_fetch_price():
    mock_resp = AsyncMock()
    mock_resp.json.return_value = {"price": 42.0}
    mock_resp.raise_for_status = MagicMock()   # raise_for_status is sync

    with patch("mymodule.session.get", return_value=mock_resp):
        assert await mymodule.fetch_price("BTC") == 42.0
```

If the code uses `async with session.get(...) as resp`, the mock also needs `__aenter__`/`__aexit__`:

```python
mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
mock_resp.__aexit__ = AsyncMock(return_value=False)
```

Async [fixtures](fixtures.md) work the same way — no extra decorator needed with `asyncio_mode = "auto"`:

```python
@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s
```

## Related notes

- [`testing-patterns.md`](testing-patterns.md) — seam-based isolation: file/DB deps, stdout, DI strategies
- [`testing-strategy.md`](testing-strategy.md) — philosophy, pyramid, mocks, TDD
- [`pytest.md`](pytest.md) — command quick-reference
