# Ruff

Ruff is a fast Python linter and formatter written in Rust. It replaces tools like `flake8`, `isort`, and `black` in a single tool.

## Installation

```bash
poetry add --group dev ruff
```

## Usage

```bash
poetry run ruff check src    # lint
poetry run ruff format src   # format
```
