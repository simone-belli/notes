---
tags:
  - cli
---

# Python CLI

## Running Python from the shell

```bash
python script.py          # run a file
python -c 'import sys'   # run a string
python -m module          # run a module (no .py extension)
```

See [run-function-cli.md](../runtime/run-function-cli.md) for how these differ and how to
reach a specific function in a module.

---

## sys.argv — raw argument list

`sys.argv` is a plain list of strings: `argv[0]` is the script name, the rest are tokens passed by the shell.

```python
# python script.py foo --bar 42
import sys
print(sys.argv)  # ['script.py', 'foo', '--bar', '42']
```

Everything is a string; no type conversion, no `--help`, no error messages. Fine for zero/one positional args; use `argparse` for anything more.

---

## argparse — structured argument parsing

```python
import argparse

parser = argparse.ArgumentParser(description="What this script does")

# positional — required, no -- prefix
parser.add_argument("filename", help="input file")

# optional flags
parser.add_argument("--count", type=int, default=10, help="number of items")
parser.add_argument("--verbose", action="store_true")

args = parser.parse_args()  # reads sys.argv[1:] by default
# args.filename → str, args.count → int, args.verbose → bool
```

`--help` is generated automatically. Bad input prints an error and exits.

### Full script pattern

Wrap parsing in `main()` behind the [`__name__ == "__main__"` guard](../runtime/entrypoint.md) so the file works both as a script and as an importable module:

```python
import argparse

def main() -> None:
    parser = argparse.ArgumentParser(description="What this script does")
    parser.add_argument("filename")
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()

    print(args.filename, args.count)

if __name__ == "__main__":
    main()
```

### Positional vs optional

| | Positional | Optional flag |
|---|---|---|
| `add_argument` syntax | `"name"` | `"--name"` / `"-n"` |
| Required? | yes | no (use `required=True` to force) |
| Access | `args.name` | `args.name` |

### Key `add_argument` parameters

| Parameter | Effect |
|-----------|--------|
| `type` | convert string: `int`, `float`, `Path`, any callable |
| `default` | value when flag is absent (`None` if omitted) |
| `action="store_true"` | boolean switch: present → `True` |
| `action="append"` | `--tag a --tag b` → `["a", "b"]` |
| `nargs` | `"?"` 0–1, `"*"` any, `"+"` one+, `N` exactly N |
| `choices` | restrict values: `choices=["json", "csv"]` |

Dashes in long flags become underscores in the namespace: `--output-file` → `args.output_file`.

`type` is any callable taking one string; it runs per token, and anything it raises becomes
a clean argparse error — so it doubles as validation:

```python
from datetime import datetime
from pathlib import Path

parser.add_argument("--out", type=Path)
parser.add_argument("--since", type=datetime.fromisoformat)
```

List arguments, structured values, config files, subcommands, and testing are in
[argparse-patterns.md](argparse-patterns.md).

---

## Boolean flags

```python
parser.add_argument("--verbose", action="store_true")   # absent → False, present → True
parser.add_argument("--no-cache", action="store_false", dest="cache")  # absent → True, present → False
```

`store_true`/`store_false` take no value — the flag's mere presence sets it. This
is almost always what you want for a boolean switch.

For a flag that also needs an explicit `--no-` form (so callers can override a
`True` default on the command line), use `BooleanOptionalAction` (3.9+):

```python
parser.add_argument("--feature", action=argparse.BooleanOptionalAction, default=True)
# --feature     → args.feature is True
# --no-feature  → args.feature is False
# (absent)      → args.feature is True (the default)
```

!!! warning "`type=bool` does not do what it looks like"
    `parser.add_argument("--flag", type=bool)` calls `bool("false")`, and
    `bool()` on any non-empty string is `True` — so `--flag false` sets
    `args.flag` to `True`. `type` converts the string token; it is not a
    validator against "truthy words". Use `action="store_true"` /
    `BooleanOptionalAction` instead, or a custom `type=` function
    (`lambda s: s.lower() in {"1", "true", "yes"}`) if the CLI must accept an
    explicit `--flag=true`/`--flag=false` value (e.g. to match another tool's
    interface).

---

## Short and long flags

```python
parser.add_argument("-v", "--verbose", action="store_true")
# -v and --verbose both set args.verbose
```

Short flags are conventionally reserved for the handful of options used most
often; everything else gets a long flag only, so the command stays readable in
scripts.

---

## See also

- [argparse-patterns.md](argparse-patterns.md) — lists, structured values, config files, subcommands, testing
- [run-function-cli.md](../runtime/run-function-cli.md) — `python -m`, console scripts, reaching a function
- [entrypoint.md](../runtime/entrypoint.md) — the `__name__ == "__main__"` guard
