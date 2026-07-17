---
tags:
  - design-patterns
  - testing
  - typing
quiz: core
---

# Repository Pattern + Dependency Injection

## What and why

A **repository** is an object that hides where data lives (DB, file, API) behind a clean interface. **Dependency injection** means passing that object in via constructor rather than creating it internally. Together they make business logic testable without a real database.

## Define the interface as a Protocol

```python
from typing import Protocol
from dataclasses import dataclass

@dataclass
class Trade:
    id: int
    symbol: str
    status: str  # "OPEN" | "CLOSED"

class TradeRepo(Protocol):
    def get(self, trade_id: int) -> Trade: ...
    def save(self, trade: Trade) -> None: ...
    def list_open(self) -> list[Trade]: ...
```

Use [`Protocol`](typing/structural-typing.md) (structural typing), not ABC. Implementations don't need to inherit — they just need the right methods.

## Business logic — only knows the Protocol

```python
class TradingService:
    def __init__(self, repo: TradeRepo) -> None:  # ← injection point
        self._repo = repo

    def close_trade(self, trade_id: int) -> None:
        trade = self._repo.get(trade_id)
        trade.status = "CLOSED"
        self._repo.save(trade)
```

No database import, no connection string. `TradingService` is portable and testable.

## Real implementation

```python
class PostgresTradeRepo:
    def __init__(self, conn) -> None:
        self._conn = conn

    def get(self, trade_id: int) -> Trade:
        row = self._conn.execute(
            "SELECT id, symbol, status FROM trades WHERE id = %s", (trade_id,)
        ).fetchone()
        return Trade(*row)

    def save(self, trade: Trade) -> None:
        self._conn.execute(
            "INSERT INTO trades (id, symbol, status) VALUES (%s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status",
            (trade.id, trade.symbol, trade.status),
        )

    def list_open(self) -> list[Trade]:
        rows = self._conn.execute(
            "SELECT id, symbol, status FROM trades WHERE status = 'OPEN'"
        ).fetchall()
        return [Trade(*r) for r in rows]
```

## In-memory fake (for tests)

```python
class InMemoryTradeRepo:
    def __init__(self) -> None:
        self._db: dict[int, Trade] = {}

    def get(self, trade_id: int) -> Trade:
        return self._db[trade_id]

    def save(self, trade: Trade) -> None:
        self._db[trade.id] = trade

    def list_open(self) -> list[Trade]:
        return [t for t in self._db.values() if t.status == "OPEN"]
```

!!! tip "Prefer a fake over a mock for repositories"
    A fake (like `InMemoryTradeRepo`) actually implements the behaviour correctly — `list_open()` really filters by status. A mock just records calls and returns canned values. Fakes catch logic bugs in callers; mocks only catch that the right method was called with the right args. Fakes also survive refactors; mocks break when implementation details change.

This is a **fake**, not a mock — it actually behaves correctly. Prefer fakes over mocks for repositories; mocks tie tests to implementation details.

## Tests — no database needed

```python
def test_close_trade():
    repo = InMemoryTradeRepo()
    repo.save(Trade(id=42, symbol="BTC", status="OPEN"))

    TradingService(repo).close_trade(42)

    assert repo.get(42).status == "CLOSED"
```

## Production wiring

```python
def build_trading_service(conn) -> TradingService:
    return TradingService(PostgresTradeRepo(conn))
```

This factory is the only place that knows both `PostgresTradeRepo` and `TradingService` exist together.

## Key rules

- **Inject at the constructor** — makes the dependency visible and overridable per test; never use module-level globals.
- **Keep the Protocol minimal** — only add methods the business logic actually calls.
- **Protocol > ABC** — external storage libraries can't inherit your ABC; they can satisfy your Protocol.

## Related

- [structural-typing.md](typing/structural-typing.md) — Protocol vs ABC detail, verifying conformance
- [testing-patterns.md](../../tooling/testing/testing-patterns.md) — seams, `tmp_path`, in-memory DB strategies
- [mocking.md](../../tooling/testing/mocking.md) — when a mock beats a fake, and the mechanics (`patch`, `autospec`)
- [fastapi.md](../../tooling/fastapi.md) — how `Depends()` extends this pattern to request-scoped resources
