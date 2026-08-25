---
quiz: core
---

# `__hash__` — Making Objects Hashable

## What and why

`__hash__` returns an `int` that lets an object live in a `set` or be used as a `dict` key. Hash-based containers map this integer to a bucket for O(1) lookup; `__eq__` then resolves collisions within the bucket.

**The hash contract**: if `a == b` then `hash(a) == hash(b)`. Violating it silently corrupts sets and dicts.

!!! warning "Defining __eq__ alone makes your class unhashable"
    Python sets `__hash__ = None` automatically when you define `__eq__` without `__hash__`. The reason: two objects that compare equal must have the same hash — if you define equality by value but keep the default identity-based hash, equal objects could end up in different dict buckets, silently corrupting lookups. Python makes this impossible by removing hashability until you explicitly define both.

## The `__eq__` / `__hash__` coupling

Python enforces the contract by managing `__hash__` automatically:

| What you define | What Python does |
|---|---|
| Neither | Both inherited from `object` (id-based) |
| `__eq__` only | `__hash__ = None` → **unhashable** |
| `__hash__` only | Works, unusual |
| Both | Your definitions win |

Defining `__eq__` alone kills hashability because two equal-but-differently-hashed objects would be treated as distinct dict keys — silent data corruption.

## Implementing `__hash__`

Hash the same fields used in `__eq__` as a tuple:

```python
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __eq__(self, other):
        return isinstance(other, Point) and (self.x, self.y) == (other.x, other.y)

    def __hash__(self):
        return hash((self.x, self.y))
```

`hash()` on a tuple combines field hashes correctly.

## Mutable objects and hash corruption

Mutating state after insertion makes the object unreachable:

```python
b = Bad(1)
s = {b}
b.x = 99
print(b in s)   # False — b is "lost" in the wrong bucket
```

This is why `list`, `dict`, and `set` are unhashable by design. Only hash **immutable** or **effectively frozen** objects.

## `@dataclass`

```python
@dataclass
class Trade:               # __eq__ generated, __hash__ = None → unhashable
    symbol: str
    price: float

@dataclass(frozen=True)
class ImmutableTrade:      # __eq__ + __hash__ both generated → hashable
    symbol: str
    price: float
```

`unsafe_hash=True` forces hash generation for a mutable dataclass — only safe if you guarantee no mutation after hashing. See [dataclasses.md](../dataclasses.md) for the full set of decorator parameters.

## Restoring hashability in subclasses

Defining `__eq__` in a subclass silently sets `__hash__ = None`. Re-inherit explicitly:

```python
class Sub(Point):
    def __eq__(self, other): ...
    __hash__ = Point.__hash__   # restore parent hash
```

## Hash randomization (`PYTHONHASHSEED`)

Since Python 3.3, hash values are salted per session to prevent hash-flooding DoS. Never serialize `hash()` output or compare it across processes. Disable with `PYTHONHASHSEED=0` for debugging.

## Default `object.__hash__`

Returns a value derived from `id(obj)` (roughly memory address). Two distinct objects never collide, and equality is identity.

See also: [data-model.md](data-model.md) for the broader data model and `@dataclass` overview; [functools.md](../../functional/functools.md) for `@lru_cache`, which requires hashable arguments as cache keys.