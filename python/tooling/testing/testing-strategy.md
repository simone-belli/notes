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

Don't mock what you don't own — mocking third-party library internals lets the mock drift from reality. Mock at your own boundary.

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

Write the failing test first, then write the minimal code to pass it, then clean up.

```
Red (failing test) → Green (passes) → Refactor (clean without breaking)
```

Most useful when fixing bugs (write a test that reproduces the bug, then fix it) and when designing new APIs.

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
- [`pydantic.md`](../pydantic.md) — validation logic concentrates at model boundaries, ideal test target
- [`mypy.md`](../mypy.md) — static types + dynamic tests are complementary, not redundant
- [`testing-patterns.md`](testing-patterns.md) — practical patterns: external deps, file I/O, DB, stdout
