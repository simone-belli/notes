---
tags:
  - testing
  - concurrency
quiz: core
---

# Testing — Mocking

Patterns for replacing dependencies with controlled substitutes. Use mocks when you can't inject a seam (see [testing-patterns.md](testing-patterns.md)) or when you need to assert a side effect was triggered.

## `patch` vs mocks

Not alternatives — they answer different questions. A **mock is an object** (`Mock`, `MagicMock`, `AsyncMock`): a fake that records calls and returns what you configure. **`patch` is an installer**: it temporarily rebinds a name in a namespace and restores the original on exit. They get conflated because `patch`'s default replacement is a freshly made `MagicMock`.

```python
from unittest.mock import MagicMock, patch

m = MagicMock()                      # mocking — an object exists, nothing is replaced
with patch("service.send_email"):    # patching — service.send_email is now a MagicMock
    ...                              # original restored on exit
```

- **Mock without `patch`** — the dependency is injected, so hand the fake in: `AlertService(MagicMock())`. Preferred: no namespace surgery, no dotted string to get wrong.
- **`patch` without a mock** — install a real value instead of a recording fake with `new=`: `patch("config.TIMEOUT", new=0.01)`, `patch("service.clock", new=FakeClock())`. Nothing is injected into the test when `new=` is given. `monkeypatch.setattr` is the pytest-native version of this ([mocking-network.md](mocking-network.md#monkeypatch-simpler-pytest-native)).

Patching is the part that breaks: a misbehaving mock fails loudly, but a patch aimed at the wrong namespace silently does nothing and the test runs against the real dependency.

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

Dotted keys are the one channel that reaches nested children in a single expression — which is why they are the way to configure depth inside `patch(...)`, where no mock object exists yet to assign to.

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

To keep the real behaviour and merely record the calls, configure `wraps=` instead — a spy rather than a stub ([below](#how-strict-and-configured-with-what)).

### Plain attributes

Anything that isn't a call is just an attribute — `m.status_code = 200`. Two snags:

- `name` is consumed by the constructor to label the mock in reprs, so `MagicMock(name="x")` does *not* set `.name`. Use `m.configure_mock(name="x")` or assign after creation.
- A real `property` on a spec'd class still behaves as an attribute on the mock; `PropertyMock` is needed only when [patching a real class's property](#properties-and-other-descriptors).

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

## Mocking a method of a class

Three different targets; picking the wrong one is the usual bug.

**Every instance — patch the attribute on the class.** Methods are class attributes looked up at call time, so this also affects instances created before the patch. The patch-where-it's-used rule doesn't bite here: every `from pricing import PriceFeed` points at the *same* class object, and you are mutating an attribute on that object.

```python
from unittest.mock import patch
from myapp.pricing import PriceFeed

with patch("myapp.pricing.PriceFeed.get_price", return_value=42.0):
    assert PriceFeed().get_price("BTC") == 42.0

with patch.object(PriceFeed, "get_price", return_value=42.0) as mock_get:
    PriceFeed().get_price("BTC")
mock_get.assert_called_once_with("BTC")
```

**One instance only — patch the attribute on the object.** Shadows the class attribute; other instances are untouched. Use it when two instances must behave differently in one test.

```python
feed = PriceFeed()
with patch.object(feed, "get_price", return_value=42.0):
    assert feed.get_price("BTC") == 42.0
```

**A method on an already-mocked instance — configure the mock** (see [Mocking a class](#mocking-a-class) above):

```python
@patch("service.PriceFeed", autospec=True)
def test_report(MockFeed):
    MockFeed.return_value.get_price.return_value = 42.0
    assert service.report("BTC") == "BTC: 42.0"
```

!!! warning "`autospec` changes whether `self` is recorded"
    Patching `PriceFeed.get_price` without `autospec` installs a plain mock on the class, so `self` is **not** passed: `mock_get.assert_called_once_with("BTC")`. With `autospec=True` the mock mimics the real function's descriptor behaviour and the instance **is** recorded: `mock_get.assert_called_once_with(feed, "BTC")`. Prefer `autospec=True` and expect the extra first argument.

### Properties and other descriptors

A `property` is *accessed*, not called, so a normal mock returns the mock itself. Use `PropertyMock`, which must be attached to the **type**:

```python
from unittest.mock import PropertyMock, patch

with patch.object(PriceFeed, "is_live", new_callable=PropertyMock) as mock_live:
    mock_live.return_value = True
    assert PriceFeed().is_live
```

- `staticmethod` / `classmethod` — patch like any other class attribute; `autospec=True` gets the implicit first argument right (none for static, `cls` for class methods).
- Dunder methods are looked up on the type, so instance-level patching never works — patch the class attribute or use a `MagicMock`.

## `patch` — arguments and variants

```python
from unittest.mock import patch

patch(target, new=DEFAULT, spec=None, create=False,
      spec_set=None, autospec=None, new_callable=None, **kwargs)
```

Every input answers one of three questions: **what gets replaced**, **what replaces it**, **how strict and how configured** the replacement is.

### What gets replaced

`target` is a **dotted string**, not a reference — `patch` imports everything up to the last dot and setattrs the final name, so `myapp.service` must be importable at patch time.

| Variant | Targets | Use for |
|---|---|---|
| `patch("pkg.mod.name")` | a module attribute, class, method, or builtin | the common case |
| `patch.object(obj, "attr")` | an attribute of an object you already hold | class/instance methods, no string to typo |
| `patch.dict(d, {...}, clear=False)` | a dict's **contents**, restored afterwards | `os.environ`, `sys.modules`, config dicts |
| `patch.multiple(target, a=DEFAULT, b=DEFAULT)` | several attributes at once | avoids three nested `with` blocks |

```python
import os
from unittest.mock import patch

with patch.dict(os.environ, {"API_KEY": "test-key"}, clear=True):
    ...   # restored exactly, including keys the block deleted
```

`patch.multiple` injects its mocks as **keyword** arguments named after the attributes; plain `patch` injects positionally.

### What replaces it

- **Nothing given** — `patch` builds a `MagicMock` and injects it (as the `as` target or an extra test argument). Since Python 3.8 it inspects the original first: an `async def` target gets an `AsyncMock` automatically.
- **`new=<object>`** — install exactly this object; **nothing is injected**, since you already hold it. A bare second positional argument *is* `new`.
- **`new_callable=<factory>`** — `patch` builds the replacement from your factory instead of `MagicMock`, and injects it.

!!! warning "`new=` is not `return_value=`"
    `patch("service.fetch", 3)` makes `service.fetch` *be* the integer `3`. `patch("service.fetch", return_value=3)` leaves it a callable mock that returns `3`. The decorator form differs too: with `new=`, no extra argument is appended to the test signature.

The three `new_callable` factories worth knowing:

```python
from unittest.mock import Mock, PropertyMock, mock_open, patch
from myapp.pricing import PriceFeed

with patch("builtins.open", new_callable=mock_open, read_data="a,b\n1,2\n") as m:
    assert open("x.csv").read().startswith("a,b")   # fake file contents

with patch.object(PriceFeed, "is_live", new_callable=PropertyMock) as live:
    live.return_value = True        # a property is accessed, not called

with patch("service.registry", new_callable=Mock):
    ...                             # dunders not pre-wired — len()/iter() fail loudly
```

### How strict, and configured with what

- **`spec=` / `spec_set=`** — restrict which attribute names exist; `spec_set` also rejects *setting* an unknown attribute, catching a test that configures a typo. **`autospec=True`** additionally enforces real call signatures — the default choice (see [`spec` and `autospec`](#spec-and-autospec) above).
- **`create=True`** — permit patching a name that doesn't exist yet. The default failure is a feature: it catches renames. Needed only for genuinely runtime-created attributes.
- **`**kwargs`** — anything the `Mock` constructor accepts, applied at creation:

```python
from myapp.service import fetch as real_fetch

patch("service.fetch", return_value={"price": 42.0})
patch("service.fetch", side_effect=TimeoutError)            # always raises
patch("service.fetch", side_effect=[1, 2, TimeoutError()])  # per-call sequence
patch("service.fetch", wraps=real_fetch)                    # spy — calls through, records
patch("service.session", **{"get.return_value.json.return_value": {"price": 42.0}})
```

`wraps=` is the underused one: the real function still runs *and* every call is recorded, so `assert_called_once_with` works on real behaviour. That's a spy, not a stub.

### How the patch is applied

| Form | Mock delivery | Scope ends |
|---|---|---|
| `@patch(...)` on a function | appended as an argument — **bottom decorator = first argument** | function returns |
| `@patch(...)` on a class | applied to every `test_*` method | each method |
| `with patch(...) as m:` | the `as` target | block exits |
| `p = patch(...); m = p.start()` | `start()`'s return value | `p.stop()` / `patch.stopall()` |

```python
@patch("service.send_alert")   # outermost → LAST argument
@patch("service.fetch")        # innermost → FIRST argument
def test_flow(mock_fetch, mock_alert):
    ...
```

Decorators apply inside-out, hence the bottom-up reading. The manual `start()`/`stop()` form leaks: a test that fails before `stop()` leaves the patch installed for the rest of the session — use it only with guaranteed cleanup (a [fixture](fixtures.md) teardown, `addCleanup`), never bare.

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

Async [fixtures](fixtures.md) work the same way — no extra decorator needed with `asyncio_mode = "auto"`:

```python
import aiohttp

@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s
```

## Related notes

- [`testing-patterns.md`](testing-patterns.md) — seam-based isolation: file/DB deps, stdout, DI strategies
- [`testing-strategy.md`](testing-strategy.md) — philosophy, pyramid, mocks, TDD
- [`pytest.md`](pytest.md) — command quick-reference
