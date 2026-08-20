---
quiz: core
---

# tempfile

Creates temporary files and directories with unpredictable, collision-free names. Never roll your own with `random` + `os.mkdir` — `tempfile` uses `os.urandom` and creates atomically, closing the race where an attacker pre-creates the guessed name in world-writable `/tmp`.

```python
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    (d / "in.csv").write_text("a,b\n1,2\n")
# whole tree deleted here, even on exception
```

Names look like `/tmp/tmpv3k9x1qz` — `tmp` prefix plus 8 random characters.

!!! warning "The `with` target is a `str`, not a `Path`"
    Wrap it — `Path(tmp)` — before doing path arithmetic. See [pathlib.Path](pathlib.md).

## TemporaryDirectory

A [context manager](../../runtime/context-managers.md); on exit it does a recursive `shutil.rmtree`. Used without `with`, cleanup still runs at garbage collection or interpreter exit, and `.cleanup()` forces it early.

```python
td = tempfile.TemporaryDirectory()
td.name       # the path, as str
td.cleanup()
```

Keyword arguments (shared with `mkdtemp`):

| argument | effect |
|---|---|
| `prefix="build-"` | before the random part → `/tmp/build-v3k9x1qz` |
| `suffix=".d"` | after it → `/tmp/tmpv3k9x1qz.d` |
| `dir="/var/data"` | parent directory instead of the system temp dir |
| `ignore_cleanup_errors=True` | (3.10+) swallow deletion failures |
| `delete=False` | (3.12+) keep the directory, for debugging |

## mkdtemp — you own the lifetime

The low-level primitive. Creates the directory mode `0700` and returns its path as a `str`; **nothing deletes it for you**.

```python
import tempfile, shutil

path = tempfile.mkdtemp(prefix="cache-")
try:
    ...
finally:
    shutil.rmtree(path)
```

Use it when the directory must outlive the function that created it; otherwise prefer `TemporaryDirectory`.

## Temporary files

- `NamedTemporaryFile()` — has a real path on disk (`.name`), deleted on close.
- `TemporaryFile()` — unnamed; unlinked immediately on POSIX.
- `SpooledTemporaryFile(max_size=...)` — in memory until it outgrows `max_size`, then spills to disk.

## Location

`tempfile.gettempdir()` resolves `$TMPDIR`, `$TEMP`, `$TMP`, then platform defaults (`/tmp` on POSIX). Set `TMPDIR` to redirect everything — useful when `/tmp` is a small tmpfs.

!!! tip "In tests, use `tmp_path`"
    pytest's [`tmp_path` fixture](../../../tooling/testing/fixtures.md) hands each test a fresh `Path` and retains the last three runs' directories for post-mortem inspection.

    ```python
    def test_writes_output(tmp_path):
        my_function(tmp_path / "out.txt")
    ```

## Pitfalls

- Don't `os.chdir` into a `TemporaryDirectory` and stay there — deleting the current working directory misbehaves on some platforms.
- Cleanup runs on normal exit and on exception, but not on `os._exit()` or `SIGKILL`.
- A path returned out of the `with` block points at a directory that no longer exists.
