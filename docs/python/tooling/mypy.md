---
tags:
  - typing
quiz: core
---

# Mypy

## What mypy is

- mypy is a static type checker for Python.
- It analyses your code before runtime and checks whether your type hints are used consistently.
- Python itself remains dynamically typed; mypy is an external development tool.

## Why it is useful

- Mypy helps catch mistakes such as passing a `str` where a `float` is expected.
- It also improves readability because function signatures document expected inputs and outputs.
- This is especially useful in larger projects where functions, classes, and modules interact.

## What mypy checks

- Mypy checks type consistency across variables, functions, classes, and modules.
- [Type hints](../language/typing/type-hints.md) such as `x: int`, `list[str]`, or `float | None` give mypy information to reason about.
- The special type `Any` disables most checking for a value and should be used carefully.

## What mypy does not check

- Mypy does not prove that a program is logically correct.
- It checks type consistency, not numerical accuracy, performance, or business logic.

## Using mypy with Poetry

- In a [Poetry](poetry.md) project, mypy is usually added as a development dependency:

```bash
poetry add --group dev mypy
```

Run it against your source folder with:

```bash
poetry run mypy src
```

For stricter checking, use:

```bash
poetry run mypy src --strict
```

## Configuration

Common configuration can be placed in `pyproject.toml` under `[tool.mypy]`:

```text
[tool.mypy]
python_version = "3.12"
strict = true
```
## Good project structure

- A typical typed project keeps messy external data at the boundaries.
- Validation or parsing code converts raw data into clean typed objects.
- The core domain logic can then use precise types and benefit most from mypy.

## Mental model

!!! note "mypy checks type consistency, not correctness — it's a design aid, not a proof"
    mypy can verify that a `float` is passed where a `float` is expected, but it cannot verify that the float is a valid price, that a calculation is numerically correct, or that business logic is sound. Think of it as enforcing the *contracts* between functions. Pair it with tests (which check behaviour) — they're complementary, not redundant.

- Mypy is best viewed as a design aid.
- It makes code contracts explicit and helps reveal unclear assumptions in your program.