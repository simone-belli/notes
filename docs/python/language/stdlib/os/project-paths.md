---
tags:
  - config
  - packaging
---

# Project Paths

Relative paths resolve against the **current working directory (CWD)**, which is set by whoever launched the process — not by the code. `python scripts/train.py` and `cd scripts && python train.py` give `"data/prices.csv"` two different meanings.

!!! note "The rule"
    Never let a relative path reach the filesystem. Anchor every path to something the program knows independently of how it was launched. There are three legitimate anchors: the **package** (files you ship), the **project root** (a repo you run from), and **configuration** (everything the user owns).

## Anchor 1 — the package

Files that are part of the code (a schema, a template, a lookup table) live inside the package and are addressed by import name, via [`importlib.resources`](../../runtime/import-system.md):

```python
from importlib.resources import files

schema = (files("mypkg.data") / "schema.json").read_text(encoding="utf-8")
```

- `files()` returns a `Traversable` — supports `/`, `read_text()`, `read_bytes()`, `open()`, `iterdir()`.
- Need a real `Path` (for a C library, say)? `with as_file(files("mypkg.data") / "model.onnx") as p:` — extracts to a temp file if the package is zipped.
- `Path(__file__).parent / "schema.json"` works for a plain checkout but assumes the package is loose files on disk; it fails for a zipped or non-filesystem loader.
- Remember to declare data files in `pyproject.toml` so the build backend ships them in the wheel.

## Anchor 2 — the project root

Count directories up from a known module, once:

```python
# src/mypkg/paths.py   →   <root>/src/mypkg/paths.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
```

`.resolve()` **before** `.parents` matters: `__file__` may be relative, and `.parents` is purely lexical (see [pathlib.md](pathlib.md#parent-and-ancestors)) — it neither collapses `..` nor follows symlinks.

The alternative is a **marker search** — walk up until `pyproject.toml` or `.git` appears:

```python
def find_root(start: Path, marker: str = "pyproject.toml") -> Path:
    for d in [start, *start.parents]:
        if (d / marker).exists():
            return d
    raise FileNotFoundError(f"no {marker} above {start}")
```

- `parents[N]` — cheap, no I/O, breaks loudly at import time if the file moves. Prefer for a library.
- Marker search — survives file moves (this is what pytest and ruff do), but can find the wrong root in a monorepo or vendored tree. Prefer for a tool that runs inside someone else's project.

!!! warning "Project root is a development-time concept"
    Once a package is installed as a dependency there is no repo root — only `site-packages`. A library that computes `ROOT` and expects `ROOT / "data"` to exist breaks for every consumer. Libraries use anchor 1 or 3; applications may use anchor 2.

## Anchor 3 — configuration

Anything whose location is a deployment decision comes from outside the code — env var, config file, or CLI flag — validated into a `Path` at startup with [pydantic-settings](../../../libraries/pydantic/pydantic-settings.md):

```python
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    data_dir: Path = ROOT / "data"     # absolute default, not "./data"
```

- **Resolve configured values once** at startup (`settings.data_dir.resolve()`); a user-supplied `./data` is still CWD-relative.
- **Make defaults absolute against `ROOT`**, so the program behaves the same from any directory.
- For user-level caches and config with no project root, don't hand-roll `~/.myapp` — `platformdirs` knows each operating system's convention:

```python
from platformdirs import user_cache_path

cache = user_cache_path("myapp")   # ~/.cache/myapp, ~/Library/Caches/myapp, %LOCALAPPDATA%
```

## A single `paths.py`

One module owns every path constant; everything else imports from it.

```python
# src/mypkg/paths.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = ROOT / "output"
```

- **One place to change** — renaming `data/` is a one-line diff, not a grep across the codebase.
- **It documents the on-disk contract** — the file replaces tribal knowledge of the layout.
- **Any path literal outside it is visibly a smell**, which makes review easy.

Better still, take paths as parameters and let only the entry point know real locations — [dependency injection](../../objects/repository-di.md) applied to the filesystem:

```python
class PriceLoader:
    def __init__(self, raw_dir: Path) -> None:
        self._raw_dir = raw_dir

loader = PriceLoader(settings.data_dir / "raw")   # main.py only
```

A hybrid is normal: `paths.py` constants as *defaults* for those parameters.

## Creating directories

Writing under a missing parent raises `FileNotFoundError` — a confusing error for "I never made the folder".

```python
out = OUTPUT_DIR / "2026" / "report.csv"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(data, encoding="utf-8")
```

- Do it at the **write site**, not at import time — a module that makes directories on import litters the filesystem during test collection and `--help`.
- Never create *input* directories. A missing `RAW_DIR` is a real error and should fail loudly.

## Paths as values

- Annotate as `Path`, not `str` — [mypy](../../../tooling/mypy.md) then catches string surgery like `dir + "/" + name`.
- Accept `str | os.PathLike[str]` at public boundaries and normalise on line one: `p = Path(p)`.
- Build with `/`, never `+` or f-strings. Note `Path("/a") / "/b"` is `Path("/b")` — an absolute segment wins.
- Compare and store resolved forms, so equality means what you expect.
- Serialise as `str(p)`, and prefer paths **relative to a root** in any file that gets committed or shared — absolute paths make artefacts machine-bound.

## Anti-patterns

| Anti-pattern | Why it breaks | Fix |
|---|---|---|
| `open("data/x.csv")` | depends on CWD | anchor to `ROOT` or settings |
| `os.chdir(...)` | global mutable state; breaks threads and libraries | pass absolute paths |
| `Path(__file__).parent.parent` scattered around | duplicated layout knowledge | one `paths.py` |
| `"/Users/me/project/data"` | machine-bound | settings / env var |
| `dir + "/" + name` | separator and type bugs | `dir / name` |
| `sys.path.append("../..")` | breaks packaging and tooling | install the package (`pip install -e .`) |
| `__file__` for library data files | fails when zipped or installed | `importlib.resources` |

Reaching *up* the tree to import is the same mistake as reaching up to read a file — the fix is the same: address the thing by name, not by location.

## Testing

Anchoring pays off because tests then never touch the real layout — inject a [`tmp_path`](../../../tooling/testing/fixtures.md):

```python
def test_writes_report(tmp_path):
    write_report(tmp_path / "report.csv")
    assert (tmp_path / "report.csv").exists()
```

`monkeypatch.setattr(mypkg.paths, "OUTPUT_DIR", tmp_path)` works for a stubborn module constant, but needing it signals the path should have been a parameter. `monkeypatch.chdir()` is the wrong fix — it re-introduces the CWD dependence.

## Related

- [pathlib.md](pathlib.md) — the `Path` API itself
- [tempfile.md](tempfile.md) — scratch directories outside tests
- [pydantic-settings.md](../../../libraries/pydantic/pydantic-settings.md) — typed configuration
- [testing-patterns.md](../../../tooling/testing/testing-patterns.md) — seams and file-I/O isolation
