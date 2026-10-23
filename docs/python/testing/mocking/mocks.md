---
tags:
  - testing
  - concurrency
quiz: core
---

# Mocking — Mock objects

A mock is a controlled substitute: it accepts any call, returns whatever you configure, and records what happened. Reach for one when you can't inject a seam (see [testing-patterns.md](../testing-patterns.md)) or when you need to assert a side effect was triggered. Getting the mock *in front of* the real dependency is a separate job — see [patch.md](patch.md).

## When to mock at all — the decision rule

- **Mock boundaries you don't own** — network, clock, randomness, filesystem at the true edge. Slow, nondeterministic, unavailable in CI; patch the outermost function of *yours* that touches them.
- **Use real fakes behind Protocols for seams you do own** — e.g. an `InMemoryTradeRepo` that actually behaves correctly (see [repository-di.md](../../language/objects/repository-di.md)). Fakes catch logic bugs in callers and survive refactors; mocks only verify "the right method was called" and break when internals change.
- **Never mock the thing under test** — patching a method of the class being tested makes the test exercise the mock, not the code; passing is vacuous. If tempted, split the collaborator out behind a seam and fake that.
- Prefer asserting state/output over asserting calls; assert calls only when the side effect *is* the behaviour ("an alert was sent"). See [testing-strategy.md](../testing-strategy.md) for the broader philosophy.

## MagicMock

`MagicMock` accepts any attribute access or method call without raising `AttributeError` — returning a new child `MagicMock` each time. It's a stand-in for any object without needing to subclass it.

```python
from unittest.mock import MagicMock

m = MagicMock()
m.foo()                  # → MagicMock
m.bar.baz.qux            # → MagicMock (arbitrary depth)
```

!!! note "MagicMock vs Mock"
    `Mock` records calls and returns a child mock for any attribute — but dunder methods are looked up on the *type*, so `len(m)`, `list(m)`, or `with m:` raise `TypeError` on a plain `Mock`. `MagicMock` pre-wires the dunders (`__len__`, `__iter__`, `__enter__`, `__exit__`, …), so it works as a container, iterator, or context manager. Use `MagicMock` by default; drop to `Mock` only if you want dunder access to fail loudly.

## Configuring a mock

Four channels, all equivalent — pick by convenience:

```python
from unittest.mock import MagicMock

m = MagicMock(return_value=7)                              # 1. constructor kwargs
m.get_price.return_value = 42.0                            # 2. attribute assignment
m.configure_mock(status=200, **{"fetch.return_value": 1})  # 3. configure_mock
MagicMock(**{"session.get.return_value.json.return_value": {"price": 42.0}})
                                                           # 4. dotted keys
```

Dotted keys are the one channel that reaches nested children in a single expression — which is why they are the way to configure depth inside [`patch(...)`](patch.md#how-strict-and-configured-with-what), where no mock object exists yet to assign to.

### `return_value` and `side_effect`

```python
m.get_price.return_value = 42.0                                  # fixed result
m.session.get.return_value.json.return_value = {"price": 42.0}   # chained

m.fetch.side_effect = ValueError("bad")             # always raises
m.fetch.side_effect = [42.0, 43.0, ValueError()]    # sequential — pops per call
m.fetch.side_effect = lambda s: PRICES[s]           # dynamic
```

- `side_effect` **wins** over `return_value` — unless the callable returns `unittest.mock.DEFAULT`, the sentinel that means "fall through to `return_value`".
- A `side_effect` list is consumed per call; a 4th call raises `StopIteration`. Any exception *class* or *instance* in it is raised rather than returned.
- Setting `side_effect = None` removes it, restoring `return_value`.

```python
from unittest.mock import DEFAULT, MagicMock

m = MagicMock(return_value=0.0)
m.side_effect = lambda s: PRICES[s] if s in PRICES else DEFAULT   # 0.0 for unknowns
```

To keep the real behaviour and merely record the calls, configure `wraps=` instead — a spy rather than a stub ([patch.md](patch.md#how-strict-and-configured-with-what)).

### Plain attributes

Anything that isn't a call is just an attribute — `m.status_code = 200`. Two snags:

- `name` is consumed by the constructor to label the mock in reprs, so `MagicMock(name="x")` does *not* set `.name`. Use `m.configure_mock(name="x")` or assign after creation.
- A real `property` on a spec'd class still behaves as an attribute on the mock; `PropertyMock` is needed only when [patching a real class's property](patch.md#properties-and-other-descriptors).

### Resetting

`m.reset_mock()` clears recorded calls but **keeps** configuration. Pass flags to drop that too:

```python
m.reset_mock(return_value=True, side_effect=True)
```

Prefer a fresh mock per test over resetting a shared one — resetting is for loops inside a single test.

### Inspecting calls

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
from unittest.mock import ANY

m.send.assert_called_once_with(to="ops@example.com", body=ANY)
```

### `spec` and `autospec`

**`spec`** — constrains the mock to a real class's interface; typos raise `AttributeError`:

```python
from unittest.mock import MagicMock

from notifiers import Notifier

m = MagicMock(spec=Notifier)
m.sned_email(...)   # AttributeError — typo caught immediately
```

`spec` checks attribute *names* only — it does **not** validate call signatures. `spec_set=` is the stricter form: it also rejects *setting* an attribute the real class lacks, catching a test that silently configures a typo.

**`autospec=True`** — builds the mock recursively from the real object, so every method enforces the real signature; wrong arguments raise `TypeError`. This catches **API drift**: with a bare mock, `m.assert_called_once_with("BTC", threshold=1000)` keeps passing after the real function is refactored to `send_alert(symbol, *, limit)` — the suite stays green while production breaks.

```python
from unittest.mock import patch

with patch("mymodule.send_alert", autospec=True) as m:
    run_checks()
m.assert_called_once_with("BTC", threshold=1000)   # TypeError if signature drifted
```

Use `autospec=True` on `patch` by default (`create_autospec(obj)` for standalone mocks). Fall back to `spec=`/bare mocks only for [attributes created dynamically at runtime](patch.md#attributes-created-in-__init__) (e.g. set in `__init__`), which autospec can't see.

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
import pytest

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

Async [fixtures](../fixtures.md) work the same way — no extra decorator needed with `asyncio_mode = "auto"`:

```python
import aiohttp

@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s
```

## Related notes

- [`patch.md`](patch.md) — installing the mock: targets, arguments, patching classes and methods
- [`network.md`](network.md) — worked example: testing HTTP-calling functions
- [`../testing-patterns.md`](../testing-patterns.md) — seam-based isolation: file/DB deps, stdout, DI strategies
- [`../testing-strategy.md`](../testing-strategy.md) — philosophy, pyramid, mocks, TDD
- [`../pytest.md`](../pytest.md) — command quick-reference
