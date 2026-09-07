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
- **Use real fakes behind Protocols for seams you do own** — e.g. an `InMemoryTradeRepo` that actually behaves correctly (see [repository-di.md](../language/objects/repository-di.md)). Fakes catch logic bugs in callers and survive refactors; mocks only verify "the right method was called" and break when internals change.
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

## Mocking a class

`patch` rebinds a **name in a namespace**, and every `from x import C` gives the importing module its *own* binding — so patch the class in the module that *uses* it, not the module that defines it (same rule as for functions: [patch where it's used](mocking-network.md#patch-where-its-used-not-where-its-defined)):

```python
# service.py uses:  from notifiers import Notifier
patch("service.Notifier")        # RIGHT
patch("notifiers.Notifier")      # WRONG — service keeps its own binding

# service.py uses:  import notifiers → notifiers.Notifier(...)
patch("notifiers.Notifier")      # RIGHT — attribute looked up on the module at call time
```

A patched class replaces the class object; "instantiating" it returns `MockClass.return_value` — the **same mock instance every call**. Configure and assert on that instance:

```python
@patch("service.Notifier", autospec=True)
def test_alert(MockNotifier):
    instance = MockNotifier.return_value
    service.alert("BTC dropped")
    MockNotifier.assert_called_once_with()               # constructor args
    instance.send.assert_called_once_with("BTC dropped") # method on the instance
```

!!! warning "Class mock vs instance mock"
    Asserting on `MockNotifier.send` (the class attribute) instead of `MockNotifier.return_value.send` (the instance) is a classic trap — the class-level mock was never called, so `assert_not_called()` on it passes vacuously. With classes, `autospec=True` specs the instances too, so both constructor and method signatures are enforced.

- `patch.object(service, "Notifier", autospec=True)` — same rule without a dotted string; the module is a real reference, only the attribute name is text.
- Module not importable at all (heavyweight SDK absent in CI): `patch.dict(sys.modules, {"heavyweight_sdk": MagicMock()})` *before* importing the code under test. Last resort — prefer patching specific attributes.

!!! note "MagicMock vs Mock"
    `Mock` records calls and returns a child mock for any attribute — but dunder methods are looked up on the *type*, so `len(m)`, `list(m)`, or `with m:` raise `TypeError` on a plain `Mock`. `MagicMock` pre-wires the dunders (`__len__`, `__iter__`, `__enter__`, `__exit__`, …), so it works as a container, iterator, or context manager. Use `MagicMock` by default; drop to `Mock` only if you want dunder access to fail loudly.

## Testing functions that make network calls

Extracted to [mocking-network.md](mocking-network.md) — a worked example covering boundary patching, `monkeypatch` vs `patch`, `side_effect` sequences, and the patch-where-it's-used rule.

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
