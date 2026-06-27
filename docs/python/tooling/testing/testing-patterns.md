# Testing — Patterns

Practical patterns for testing functions with external dependencies or side effects.

## Testing functions with external dependencies

The problem: a function that opens a CSV or queries a database makes tests slow, fragile, and non-deterministic. The solution is always the same — **create a seam** where the test can swap in a substitute.

### Root cause: hidden coupling

```python
# BAD — dependency is invisible from the outside
def load_prices(symbol: str) -> list[float]:
    with open("/data/prices.csv") as f:   # impossible to swap in tests
        ...

# GOOD — caller decides what file to use (dependency injection)
def load_prices(symbol: str, filepath: str | Path) -> list[float]:
    with open(filepath) as f:
        ...
```

Receive dependencies as arguments rather than creating them internally.

### Strategy 1 — real file via `tmp_path` (best for file I/O)

pytest's built-in `tmp_path` fixture provides a fresh temp directory per test. Deleted automatically after the test.

```python
def test_load_prices(tmp_path):
    csv_file = tmp_path / "prices.csv"
    csv_file.write_text("symbol,price\nBHP,45.5\nBHP,46.0\n")

    result = load_prices("BHP", filepath=csv_file)

    assert result == [45.5, 46.0]
```

### Strategy 2 — in-memory file object (`io.StringIO`)

Accept `TextIO` (any file-like) instead of a path string. Fastest option; no filesystem touched.

```python
import io, csv

def load_prices(symbol: str, file) -> list[float]:
    return [float(r["price"]) for r in csv.DictReader(file) if r["symbol"] == symbol]

def test_load_prices():
    assert load_prices("BHP", io.StringIO("symbol,price\nBHP,45.5\n")) == [45.5]
```

### Strategy 3 — in-memory database (SQLite `:memory:`)

A real SQL engine, zero infrastructure. Best for unit-testing SQL logic.

```python
import sqlite3

def get_open_trades(conn) -> list[dict]:
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute("SELECT * FROM trades WHERE status='OPEN'")]

def test_returns_only_open_trades():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE trades (id INT, status TEXT)")
    conn.execute("INSERT INTO trades VALUES (1, 'OPEN'), (2, 'CLOSED')")

    assert len(get_open_trades(conn)) == 1
```

Limitation: SQLite dialect differs from Postgres/MySQL. Use Testcontainers for full dialect fidelity.

### Strategy 4 — transaction rollback (integration tests against a real DB)

Wrap each test in a transaction rolled back on teardown. State never leaks between tests.

```python
@pytest.fixture
def db_conn():
    conn = psycopg2.connect(dsn="postgresql://localhost/testdb")
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()
```

### Strategy 5 — `patch()` (last resort)

When you can't inject the dependency. Ties the test to implementation details — fragile under refactors.

```python
from unittest.mock import mock_open, patch

def test_load_prices_mocked():
    with patch("builtins.open", mock_open(read_data="symbol,price\nBHP,45.5\n")):
        assert load_prices("BHP", "/any/path") == [45.5]
```

### Decision guide

| Situation | Strategy |
|-----------|----------|
| File I/O, testing parsing logic | `tmp_path` (real file) |
| File I/O, parsing logic is trivial | `io.StringIO` |
| SQL, SQLite dialect is fine | `sqlite3.connect(":memory:")` |
| SQL, need exact dialect | Testcontainers or rollback fixture |
| Can't inject the dep | `patch()` |

## Testing functions that print to stdout

Printing is a side effect — there's no return value to assert against. pytest's `capsys` fixture captures `sys.stdout` / `sys.stderr` during the test.

```python
def greet(name: str) -> None:
    print(f"Hello, {name}!")

def test_greet(capsys):
    greet("Alice")
    captured = capsys.readouterr()   # named tuple: .out, .err
    assert captured.out == "Hello, Alice!\n"
```

`readouterr()` **consumes** the buffer — each call returns only what was printed since the last call.

### Checking stderr separately

```python
import sys

def log_warning(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)

def test_warning_goes_to_stderr(capsys):
    log_warning("low balance")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "low balance" in captured.err
```

### `capfd` — file-descriptor level

Use `capfd` (same API) when output comes from C extensions or subprocesses that bypass `sys.stdout`.

### Partial matching

For long or variable output, use `in` rather than strict equality:

```python
assert "Total:" in capsys.readouterr().out
```

### Design note: prefer a pure function

If you're testing `print` output heavily, the function is probably conflating computation with display. Split them:

```python
# Hard to test — side effect baked in
def report_pnl(trades):
    print(f"P&L: {sum(t.pnl for t in trades):.2f}")

# Easy to test — pure function + thin display layer
def compute_pnl(trades) -> float:
    return sum(t.pnl for t in trades)

def report_pnl(trades):
    print(f"P&L: {compute_pnl(trades):.2f}")
```

Test `compute_pnl` directly; leave `report_pnl` to a single smoke test or skip it entirely.

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
| Need to count calls or inspect args | `patch` + `MagicMock` |
| Sequential call sequence (first fails, second succeeds) | `side_effect=[...]` list |
| Async network call | `patch` + `AsyncMock` |

## Related notes

- [`testing-strategy.md`](testing-strategy.md) — philosophy, pyramid, mocks, TDD
- [`pytest.md`](pytest.md) — command quick-reference
