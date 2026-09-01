---
tags:
  - cli
  - testing
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

### Lists

Three idioms, in decreasing order of how idiomatic they are:

```python
parser.add_argument("--symbols", nargs="+")                 # --symbols BTC ETH
parser.add_argument("--symbol", action="append", default=[]) # --symbol BTC --symbol ETH
parser.add_argument("--tags", type=lambda s: s.split(","))   # --tags a,b,c
```

With `nargs`, `type=` applies to **each element** — `nargs="+", type=int` gives `list[int]`,
and `choices` validates every element. `nargs="*"` allows an empty list; `nargs="+"`
requires at least one.

!!! warning "A greedy `nargs` flag swallows the next positional"
    `--symbols BTC ETH output.csv` puts `output.csv` in `args.symbols`. End the list with
    `--` (`--symbols BTC ETH -- output.csv`), or avoid positionals alongside a variadic
    flag. `action="append"` never has this problem, which makes it the safer choice for
    script-generated commands.

`action="append"` mutates the `default=[]` list object itself, so a parser reused twice in
one process accumulates values — use `default=None` and `args.symbol or []` if that matters.

### Structured values

Take one JSON string for anything non-flat:

```python
import json

parser.add_argument("--params", type=json.loads, default={})
# --params '{"lr": 0.01, "layers": [64, 32]}'
```

Single-quote it in the shell so the double quotes reach Python. For a flat mapping,
`KEY=VALUE` pairs read better:

```python
def kv(s: str) -> tuple[str, str]:
    key, _, value = s.partition("=")
    return key, value

parser.add_argument("--set", action="append", type=kv, default=[])
# --set lr=0.01 --set epochs=10  →  dict(args.set)
```

Long lists belong in a file rather than on the command line — pass `type=Path` and read it,
or let argparse read the *arguments* from a file:

```python
parser = argparse.ArgumentParser(fromfile_prefix_chars="@")
# mycli @args.txt      (one argument per line)
```

!!! tip "Prefer `type=Path` over `argparse.FileType`"
    `FileType` opens the file during parsing and never closes it — including on runs that
    fail later for unrelated reasons. Convert to a `Path` and open it yourself.

### Values from a YAML or JSON file

Given a list in a [YAML](../../../tools/yaml.md) or JSON file, pass the *path* and parse inside `type=` — the program then only
ever sees a `list[str]`, and a malformed file becomes a clean argparse error:

```python
from pathlib import Path

import yaml     # pip install pyyaml

def read_symbols(path: str) -> list[str]:
    return yaml.safe_load(Path(path).read_text())["symbols"]

parser.add_argument("--symbols-file", type=read_symbols, dest="symbols")
```

Use `yaml.safe_load`, never `yaml.load` — the latter can construct arbitrary Python objects
from the file.

When the file holds a whole configuration, load it into `set_defaults` with a pre-parser so
flags still win:

```python
pre = argparse.ArgumentParser(add_help=False)
pre.add_argument("--config", type=Path)
known, remaining = pre.parse_known_args()

parser = argparse.ArgumentParser(parents=[pre])
parser.add_argument("--window", type=int, default=30)

if known.config:
    parser.set_defaults(**yaml.safe_load(known.config.read_text()))

args = parser.parse_args(remaining)
```

Precedence is **`add_argument` defaults < config file < command line**. The file's keys must
match the argument `dest` names; unmatched keys are silently added to the namespace rather
than rejected.

!!! tip "Expanding a file's list in the shell instead"
    For a program you don't control, `yq` (the YAML counterpart to [jq](../../../tools/jq.md))
    plus word splitting works: `mycli --symbols $(yq -r '.symbols[]' params.yaml)`. The
    unquoted `$( )` is what splits the lines into tokens — it breaks on values containing
    spaces or globs, so use a shell array (`symbols=("${(@f)$(...)}")` in
    [zsh](../../../tools/shell/zsh.md)) when that's possible.

### Boolean flags

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

### Short and long flags

```python
parser.add_argument("-v", "--verbose", action="store_true")
# -v and --verbose both set args.verbose
```

### Subcommands

```python
sub = parser.add_subparsers(dest="command")

push = sub.add_parser("push")
push.add_argument("--force", action="store_true")

args = parser.parse_args()
if args.command == "push":
    ...
```

### Mutually exclusive flags

```python
group = parser.add_mutually_exclusive_group()
group.add_argument("--quiet", action="store_true")
group.add_argument("--verbose", action="store_true")
```

### Testing

**Level 1 — test the parser directly** (pass a list; never touches real `sys.argv`):

```python
args = parser.parse_args(["file.txt", "--count", "5"])
```

**Level 2 — smoke-test the full entry point** by patching `sys.argv` and calling `main()`.
Needed because in a pytest session `sys.argv` contains pytest's own arguments, which argparse
will reject or misparse. `sys` is a singleton, so patching `"sys.argv"` affects all code:

```python
from unittest.mock import patch

def test_main_smoke():
    with patch("sys.argv", ["myprog", "--count", "5", "file.txt"]):
        main()   # raises → test fails; returns normally → test passes
```

No assertion required — any uncaught exception (including `SystemExit`) fails the test.

`argv[0]` must be present (argparse skips it), `argv[1:]` are the tokens parsed.

**`patch.object` variant** — takes the live `sys` object instead of a string path; IDE-navigable, no typo risk:

```python
import sys
from unittest.mock import patch

def test_main_smoke():
    with patch.object(sys, "argv", ["cli", "--symbols", "BTCUSDT", "--limit", "5"]):
        main()
```

`patch.object(target, attribute, new)` replaces `target.attribute` with `new` for the duration of the block.

**`monkeypatch` variant** — same effect, no import:

```python
def test_main_smoke(monkeypatch):
    monkeypatch.setattr("sys.argv", ["myprog", "--count", "5", "file.txt"])
    main()
```

**Asserting a clean exit** — if `main()` calls `sys.exit(0)`, that raises `SystemExit`:

```python
import pytest

def test_main_exits_cleanly():
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["myprog", "--count", "5"]):
            main()
    assert exc_info.value.code == 0
```

**Asserting bad-input rejection** (argparse exits with code 2 on parse error):

```python
def test_missing_required_arg():
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["myprog"]):   # missing required arg
            main()
    assert exc_info.value.code == 2
```

!!! tip "Extract logic from parsing"
    Keep `parse_args()` in `main()`; pass the namespace into pure functions. Unit-test those functions directly — no patching needed, no parser involved.

!!! warning "Error handling"
    `parse_args()` calls `sys.exit(2)` on bad input. Use `ArgumentParser(exit_on_error=False)` (Python 3.9+) to catch `ArgumentError` instead.
