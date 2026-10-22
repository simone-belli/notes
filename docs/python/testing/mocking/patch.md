---
tags:
  - testing
quiz: core
---

# Mocking — patch

`patch` is the installer that puts a fake in front of the real thing. It is the half of mocking that actually breaks: a misbehaving mock fails loudly, but a patch aimed at the wrong namespace silently does nothing and the test runs against the real dependency.

## `patch` vs mocks

Not alternatives — they answer different questions. A **mock is an object** (`Mock`, `MagicMock`, `AsyncMock`): a fake that records calls and returns what you configure (see [mocks.md](mocks.md)). **`patch` is an installer**: it temporarily rebinds a name in a namespace and restores the original on exit. They get conflated because `patch`'s default replacement is a freshly made `MagicMock`.

```python
from unittest.mock import MagicMock, patch

m = MagicMock()                      # mocking — an object exists, nothing is replaced
with patch("service.send_email"):    # patching — service.send_email is now a MagicMock
    ...                              # original restored on exit
```

- **Mock without `patch`** — the dependency is injected, so hand the fake in: `AlertService(MagicMock())`. Preferred: no namespace surgery, no dotted string to get wrong.
- **`patch` without a mock** — install a real value instead of a recording fake with `new=`: `patch("config.TIMEOUT", new=0.01)`, `patch("service.clock", new=FakeClock())`. Nothing is injected into the test when `new=` is given. `monkeypatch.setattr` is the pytest-native version of this ([network.md](network.md#monkeypatch-simpler-pytest-native)).

## Patching a class

`patch` rebinds a **name in a namespace**, and every `from x import C` gives the importing module its *own* binding — so patch the class in the module that *uses* it, not the module that defines it (same rule as for functions: [patch where it's used](network.md#patch-where-its-used-not-where-its-defined)):

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

## Patching a method of a class

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

**A method on an already-mocked instance — configure the mock** (see [Patching a class](#patching-a-class) above):

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

## Arguments and variants

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

- **`spec=` / `spec_set=`** — restrict which attribute names exist; `spec_set` also rejects *setting* an unknown attribute, catching a test that configures a typo. **`autospec=True`** additionally enforces real call signatures — the default choice (see [`spec` and `autospec`](mocks.md#spec-and-autospec)).
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

Decorators apply inside-out, hence the bottom-up reading. The manual `start()`/`stop()` form leaks: a test that fails before `stop()` leaves the patch installed for the rest of the session — use it only with guaranteed cleanup (a [fixture](../fixtures.md) teardown, `addCleanup`), never bare.

## Related notes

- [`mocks.md`](mocks.md) — the objects `patch` installs: configuration, `spec`/`autospec`, `AsyncMock`
- [`network.md`](network.md) — worked example: boundary patching, `monkeypatch` vs `patch`, `side_effect` sequences
- [`../testing-patterns.md`](../testing-patterns.md) — seam-based isolation, the alternative to patching
