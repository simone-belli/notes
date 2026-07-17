---
tags:
  - testing
quiz: core
---

# Testing — Strategy

Tests are executable claims about behaviour. They exist to enable *change* safely — refactors, upgrades, onboarding — not to reach a coverage number.

## The test pyramid

```
         ▲  E2E / smoke tests     (few, slow, high confidence)
        ▲▲▲ Integration tests     (moderate — real deps wired together)
       ▲▲▲▲▲ Unit tests           (many, fast, pinpoint failures)
```

Most tests should be units. Integration tests catch what units can't (schema mismatches, transaction semantics). E2E tests cover only the critical path.

## What to test

Test **behaviour, not implementation**. The rule of thumb: risk × value.

- **Test heavily**: pure functions, validation/parsing, error paths, business rules
- **Skip**: trivial getters, third-party library internals, UI layout

> "Test the things that scare you." — Kent Beck

## AAA pattern

Every test has three acts:

```python
def test_trade_rejects_negative_quantity():
    # Arrange
    data = {"symbol": "BHP", "quantity": -10, "price": 45.5, "side": "BUY"}

    # Act + Assert
    with pytest.raises(ValidationError):
        Trade(**data)
```

One test, one behaviour. If a test has 10 assertions, split it into 10 tests.

## Fakes, stubs, mocks

| Term | What it does | When to use |
|------|-------------|-------------|
| **Stub** | Returns a canned value | Drive a code path |
| **Mock** | Stub that records calls | Assert a side effect was triggered |
| **Fake** | Lightweight real implementation (e.g. in-memory dict) | When a stub is too thin |

!!! tip "Mock at your own boundary — don't mock what you don't own"
    Mocking third-party library internals (e.g. `httpx.Response` internals) lets the mock drift from the real API — the library updates and your tests keep passing while your code breaks. Instead, mock at the boundary you own: your function that calls the library, or your repository interface. See the [testing-patterns.md](testing-patterns.md) decision guide.

Don't mock what you don't own — mocking third-party library internals lets the mock drift from reality. Mock at your own boundary. For the mechanics (`patch`, `autospec`, `side_effect`) and the full when-to-mock decision rule, see [mocking.md](mocking.md).

```python
from unittest.mock import MagicMock, patch

def test_sends_alert_on_breach():
    with patch("myapp.notifier.send_email") as mock_send:
        check_risk_limit(position=1_000_000)
        mock_send.assert_called_once()
```

## How much is enough?

80–90% line coverage is a reasonable floor; beyond that, returns diminish fast. Better questions:

- Do the scary parts (validation, error handling, business rules) have tests?
- Would a new reader understand expected behaviour from the test suite?
- Does a real bug cause a test to fail? (Use `mutmut` for mutation testing.)

## TDD: Red → Green → Refactor

Test-Driven Development (TDD) writes the failing test *before* the code that satisfies it — the test drives the design rather than verifying it after the fact.

```
Red (failing test) → Green (minimal code to pass) → Refactor (clean without breaking)
```

Robert C. Martin's three laws make the loop concrete: write no production code without a failing test first; write no more test than needed to fail; write no more production code than needed to pass the current test. The cycle is meant to be seconds to minutes long, not hours.

!!! tip "Why write the test first, not after"
    Tests written after the code tend to confirm what the code already does, not what it should do — and are the first thing skipped under deadline pressure. A test-first workflow also forces callable, decoupled designs, since untestable code can't be driven from a test at all.

Two schools differ on what a test should verify:

- **Chicago / classic (state-based)** — assert on return values or resulting state; prefers real collaborators over mocks. Resilient to refactoring but can be slower to pinpoint a failure.
- **London / mockist (interaction-based)** — [mocks](mocking.md) collaborators and asserts the right calls happened; designs top-down, mocking out not-yet-built pieces. Pinpoints failures precisely but the tests can break on refactors that don't change behaviour (testing implementation, not behaviour).

Most useful when fixing bugs (write a test that reproduces the bug, then fix it) and when designing new APIs. Less natural for exploratory/throwaway prototyping, where the shape of the solution isn't known yet — spike without tests, then rebuild with TDD once the design settles.

## Useful pytest ecosystem

| Package | Role |
|---------|------|
| [`pytest`](pytest.md) | Runner, discovery, assertions |
| `pytest-cov` | Coverage (`--cov=myapp --cov-report=term-missing`) |
| `pytest-mock` | Cleaner `mocker` fixture |
| `hypothesis` | Property-based testing — auto-generates edge cases |
| `factory_boy` | Generates fixture data for models |
| `mutmut` | Mutation testing to verify test quality |

### hypothesis example

```python
from hypothesis import given, strategies as st

@given(st.integers(max_value=-1))
def test_rejects_any_negative_quantity(qty):
    with pytest.raises(ValidationError):
        Trade(symbol="BHP", quantity=qty, price=1.0, side="BUY")
```

## Related notes

- [`pytest.md`](pytest.md) — command quick-reference
- [`pydantic.md`](../../libraries/pydantic/pydantic.md) — validation logic concentrates at model boundaries, ideal test target
- [`mypy.md`](../mypy.md) — static types + dynamic tests are complementary, not redundant
- [`testing-patterns.md`](testing-patterns.md) — practical patterns: external deps, file I/O, DB, stdout
