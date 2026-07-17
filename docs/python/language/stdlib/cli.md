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
