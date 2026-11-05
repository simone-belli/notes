# Dynamic attributes: `setattr` and friends

When an attribute's name is only known at runtime — a config key, a CSV header, a command name — the dot syntax can't help. Four builtins take the name as a **string** and run the exact same machinery as `obj.x`: descriptors, properties, `__slots__`, and any `__getattr__` / `__setattr__` override all fire.

## The builtins

| Builtin | Equivalent to |
|---|---|
| `getattr(obj, "x")` | `obj.x` |
| `getattr(obj, "x", default)` | `obj.x`, or `default` on `AttributeError` |
| `setattr(obj, "x", v)` | `obj.x = v` |
| `delattr(obj, "x")` | `del obj.x` |
| `hasattr(obj, "x")` | `True` unless `getattr` raises `AttributeError` |

```python
class Config: ...

cfg = Config()
for key, value in {"host": "localhost", "port": 8080}.items():
    setattr(cfg, key, value)

cfg.port                          # 8080
getattr(cfg, "timeout", 30)       # 30 — default, no exception
delattr(cfg, "host")
hasattr(cfg, "host")              # False
```

- No `default` → a missing name raises `AttributeError`, just like the dot.
- `hasattr` *calls* `getattr`, so property getters run — see [introspection.md](introspection.md) for its pitfalls.
- The instance `__dict__` accepts any string, so `setattr(obj, "my-key", 1)` works — but only `getattr` can read it back.

## Common uses

**Dispatch by name** — a command router without an `if` chain:

```python
class Shell:
    def do_ls(self): ...
    def do_cd(self): ...
    def unknown(self): print("?")

    def run(self, cmd: str):
        getattr(self, f"do_{cmd}", self.unknown)()
```

**Generic code over fields:**

```python
from dataclasses import dataclass, fields

@dataclass
class Point:
    x: float
    y: float

def scaled(p: Point, k: float) -> Point:
    q = Point(0, 0)
    for f in fields(p):
        setattr(q, f.name, getattr(p, f.name) * k)
    return q
```

**Monkeypatching** — `unittest.mock.patch` and pytest's `monkeypatch.setattr` are `setattr` on the target plus a restore on exit (see [patch.md](../../../testing/mocking/patch.md)).

## Overriding `__setattr__` / `__delattr__`

Reading has two hooks (`__getattribute__` and the fallback `__getattr__`, see [attribute-lookup.md](attribute-lookup.md)); writing and deleting have one each, and they run on **every** assignment — `__init__` included.

```python
class Tracked:
    def __init__(self, x):
        self.x = x                          # goes through __setattr__ too

    def __setattr__(self, name, value):
        print(f"set {name}={value!r}")
        super().__setattr__(name, value)    # do the real store
```

- Uses: read-only objects, validation on every field, dirty-tracking, registries — PyTorch's `nn.Module` overrides it so `self.fc = nn.Linear(...)` registers a sub-module ([modules.md](../../../../ml/pytorch/modules.md)).
- `object.__setattr__` is the default store: call a data descriptor's `__set__` if the Method Resolution Order (MRO) has one, else write into `obj.__dict__`.

!!! warning "`self.x = ...` inside `__setattr__` recurses forever"
    The assignment calls `__setattr__` again. Always delegate the store with `super().__setattr__(name, value)` (or `object.__setattr__`). The same applies to `__delattr__` and `super().__delattr__(name)`.

!!! note "How frozen dataclasses write to themselves"
    A `frozen=True` dataclass's `__setattr__` raises `FrozenInstanceError`. Its generated `__init__` — and your `__post_init__` — sidestep the override by calling `object.__setattr__(self, name, value)` directly (see [dataclasses.md](../dataclasses.md)).

## `vars()` and `__dict__`

```python
from types import SimpleNamespace

ns = SimpleNamespace()
vars(ns).update(host="localhost", port=8080)   # bulk-set
vars(ns)                                       # {'host': 'localhost', 'port': 8080}
```

- `vars(obj)` *is* `obj.__dict__` — the live namespace, not a copy.
- Writing to it **bypasses** `__setattr__`, properties, and validation; it also fails on slotted objects, which have no `__dict__`. `setattr` in a loop is the protocol-respecting version.

## When not to

!!! tip "Prefer the dot when the names are fixed"
    String-named access is invisible to type checkers (mypy infers `Any`), IDE rename, and grep. Reach for it only when the name genuinely arrives at runtime.

- Never `setattr` with **untrusted** names: `"__class__"` or a method name overwrites behaviour. Whitelist first (`if key in ALLOWED`).
- A bag of arbitrary keys is often better as a plain `dict` than as attributes.
