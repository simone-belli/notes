---
tags:
  - testing
quiz: core
---

# pytest Fixtures

Fixtures are **dependency-injected setup functions**. A test declares what it needs by naming the fixture as a parameter — pytest resolves and runs it automatically.

```python
def test_total(sample_trades):   # pytest injects sample_trades
    assert sum(t["qty"] for t in sample_trades) == 15
```

!!! note "Why fixtures beat setUp/tearDown"
    Fixtures compose: a fixture can depend on other fixtures. pytest builds the dependency graph automatically. Tests stay declarative — they name what they need, not how to build it.

## Defining a fixture

```python
import pytest

@pytest.fixture
def sample_trades():
    return [{"symbol": "AAPL", "qty": 10, "price": 150.0}]
```

## Setup and teardown with `yield`

```python
@pytest.fixture
def db_conn():
    conn = psycopg2.connect(dsn="postgresql://localhost/testdb")
    conn.autocommit = False
    yield conn          # test receives this
    conn.rollback()     # runs even if the test fails
    conn.close()
```

## Scope

Controls how long the fixture instance lives:

| scope | lifetime |
|-------|---------|
| `"function"` (default) | new per test |
| `"class"` | shared within a test class |
| `"module"` | shared within a file |
| `"session"` | shared across the entire run |

```python
@pytest.fixture(scope="session")
def expensive_model():
    return load_large_ml_model()
```

!!! warning "Shared mutable state"
    A `scope="session"` fixture that holds mutable state acts like a global — mutations in one test bleed into the next. Higher-scope fixtures can only depend on same-or-higher scope fixtures.

## `conftest.py` — sharing fixtures

Fixtures in `conftest.py` are automatically visible to all tests in the same directory and below. No import needed.

```
tests/
├── conftest.py       # visible everywhere below
└── integration/
    ├── conftest.py   # overrides or adds for integration tests only
    └── test_db.py
```

## Fixtures using other fixtures

```python
@pytest.fixture
def db_with_schema(db_conn):
    db_conn.execute("CREATE TABLE trades (id INT, status TEXT)")
    yield db_conn
    db_conn.execute("DROP TABLE trades")
```

## Parametrized fixtures

Multiplies every test that uses the fixture — one run per parameter:

```python
@pytest.fixture(params=["sqlite", "postgres"])
def db(request):
    if request.param == "sqlite":
        return sqlite3.connect(":memory:")
    return psycopg2.connect(...)

def test_query(db):   # runs twice
    assert db.execute("SELECT 1").fetchone() is not None
```

Use `request.param` to access the current parameter. See [contract-tests.md](contract-tests.md) for the pattern applied to Protocol implementations.

## `@pytest.mark.parametrize` — one test body, many cases

Unlike a parametrized fixture, this parametrizes the test function directly — no fixture needed:

```python
@pytest.mark.parametrize("qty,price,expected", [
    (10, 5.0, 50.0),
    (0, 5.0, 0.0),
    (-1, 5.0, -5.0),
], ids=["normal", "zero", "negative"])
def test_notional(qty, price, expected):
    assert qty * price == expected
```

!!! tip "Use `ids=`"
    Without `ids=`, a failure reports `test_notional[10-5.0-50.0]` — the raw values. With `ids=`, it reports `test_notional[negative]`, which tells you which case failed without decoding tuples.

## `autouse` — implicit fixtures

```python
@pytest.fixture(autouse=True)
def reset_state(db_conn):
    yield
    db_conn.execute("DELETE FROM trades")
```

Runs for every test in scope without being declared as a parameter.

## Fixture factories

Return a callable when tests need multiple instances with different arguments:

```python
@pytest.fixture
def make_trade():
    def _make(symbol="AAPL", qty=1, price=100.0):
        return {"symbol": symbol, "qty": qty, "price": price}
    return _make

def test_portfolio(make_trade):
    t1 = make_trade("BTC", qty=2, price=30000.0)
    t2 = make_trade()   # defaults
```

## Built-in fixtures

| fixture | provides |
|---------|---------|
| `tmp_path` | fresh temp `Path` dir, deleted after test |
| `capsys` | captures stdout/stderr; `.readouterr()` → `.out`, `.err` |
| `capfd` | same as `capsys` but at file-descriptor level (catches C extensions) |
| `monkeypatch` | attribute/env patching with auto-restore after test |
| `caplog` | captures stdlib log records |
| `request` | test context, `request.param`, `request.addfinalizer()` |

`monkeypatch` and `capsys` are covered with examples in [testing-patterns.md](testing-patterns.md) and [mocking.md](mocking.md).
