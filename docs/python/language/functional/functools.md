---
quiz: core
---

# Decorators and `functools`

## First-class functions

Python functions are **values**, not a special syntactic category: assign one to a name, store it in a list/dict, pass it as an argument, or return it from another function — the same as an `int` or a `str`.

```python
def shout(text: str) -> str:
    return text.upper()

greeter = shout          # assign to a name
greeter("hi")             # "HI"

def apply(f, value):     # pass a function as an argument
    return f(value)

apply(shout, "hi")        # "HI"
```

A function that **returns** a function is a [closure](../runtime/scopes.md#closures) — the returned function keeps access to variables from the scope it was created in, not just its own arguments:

```python
def make_multiplier(n):
    def multiply(x):
        return x * n   # n is captured from the enclosing scope, see scopes.md
    return multiply

double = make_multiplier(2)
double(5)   # 10
```

See [scopes.md](../runtime/scopes.md#closures) for the full mechanics of what gets captured (the variable, not its value) and the late-binding gotcha that follows from it.

!!! note "A decorator is just a closure, with `@` as sugar"
    `@decorator` above a `def` is exactly equivalent to `func = decorator(func)` written after it. There is no separate decorator mechanism in the interpreter — it's first-class functions (passing `func` in) plus a closure (the `wrapper` returned, which closes over `func`) plus syntax sugar for the reassignment. Everything below follows from just those two ideas.

## Decorators

A function that takes a function as input and returns a new function.

### Transforming vs. registering

Decorators split into two categories that look identical (`@thing` above a `def`) but do fundamentally different jobs:

- **Transforming** — returns a *different* callable (a `wrapper`) that replaces the original. Calling the decorated name now runs different code. Examples: `@functools.wraps`-based wrappers, `@retry`, `@lru_cache`.
- **Registering** — returns `func` itself, unchanged. Its effect is a **side effect at decoration time**: recording `func` in a dict/list/class attribute so something else (a router, a validation framework) can find it later. Examples: `@app.route(...)`, Pydantic's `@field_validator`.

```python
routes = {}

def route(path):
    def register(func):
        routes[path] = func   # side effect
        return func            # same object back — nothing wraps it
    return register

@route("/health")
def health_check():
    return "ok"

health_check is routes["/health"]   # True — registering decorator, identity preserved
```

!!! tip "The tell"
    Does the decorator define a nested function and return *that*? Transforming. Does it return its argument unchanged (aside from bookkeeping)? Registering. Check with `decorated is original` or by reading whether the decorator body has a `return wrapper` vs. `return func`.

A registering decorator applied to a method inside a class body fires *during* that body's execution — before the class object exists — so it can only write to something outside the class (a module-level registry, as above). See [class-creation.md](../objects/class-creation.md) for why that ordering holds and how `__init_subclass__`/metaclasses read the result afterward.

### No arguments — 2 levels of nesting

```python
import functools

def my_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ...
        return func(*args, **kwargs)
    return wrapper
```

`@functools.wraps` preserves the metadata of the original function (name, docstring) instead of exposing the wrapper.

### With arguments — 3 levels of nesting

```python
def my_decorator(x_dec):                # 1. receives decorator arguments
    def decorator(func):                # 2. receives the function being decorated
        def wrapper(*args, **kwargs):   # 3. receives the function call arguments
            ...
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

## Memoization with `@lru_cache`

Memoisation caches the result of a function call keyed on its arguments. On a cache hit, the function body is never executed — the stored result is returned immediately.

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)
```

LRU = Least Recently Used: when `maxsize` entries are stored, the least recently accessed entry is evicted to make room.

### The hashability constraint

The cache key is built from arguments exactly like a `dict` key — every argument must be **hashable**. Passing a `list`, `dict`, or `set` raises `TypeError` at call time.

```python
@lru_cache(maxsize=128)
def process(data: tuple[float, ...]) -> float: ...  # tuple ✓
# process([1.0, 2.0])  → TypeError: unhashable type: 'list'
process((1.0, 2.0))    # ✓
```

Use `tuple` instead of `list`, `frozenset` instead of `set`, `frozen=True` dataclasses instead of mutable ones.

!!! warning "Only cache pure functions — impure caches silently return stale results"
    `@lru_cache` never re-calls the function for a seen input. If the result depends on a DB, file, clock, or any external state, the first result is frozen forever. There's no automatic invalidation; you'd have to call `.cache_clear()` manually. See the decision guide below.

### The determinism constraint

The cache never re-calls the function for a previously seen input. If the output can change for the same input — reads from a DB, file, clock, or RNG — the cached result silently goes stale.

```python
@lru_cache(maxsize=None)
def get_price(symbol: str) -> float:
    return db.query(...)   # BAD: price moves, cache doesn't
```

Memoisation is only correct for **pure functions**: same inputs → same output, always, with no side effects.

### `@cache` — unbounded variant

`@functools.cache` (Python 3.9+) is `lru_cache(maxsize=None)` with no eviction and slightly less overhead. Safe for small, well-bounded input spaces; risky in long-running processes with unbounded inputs.

```python
from functools import cache

@cache
def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)
```

### Introspection and invalidation

```python
fib.cache_info()   # CacheInfo(hits=34, misses=10, maxsize=128, currsize=10)
fib.cache_clear()  # wipe entire cache (no per-key invalidation in stdlib)
```

!!! warning "@lru_cache on instance methods leaks memory"
    Because `self` is part of the cache key, the module-level cache dict holds a strong reference to every instance ever passed to the method. The instance can never be garbage collected. Use `@functools.cached_property` instead for computed attributes with no arguments — it stores the result on the instance itself and is collected with it.

### Pitfall: caching instance methods

`self` is part of the cache key, so the module-level cache dict holds a **strong reference to `self`**, preventing garbage collection of instances.

For a computed attribute with no arguments, use `@functools.cached_property` — it stores the result on the instance itself:

```python
from functools import cached_property

class Pricer:
    @cached_property
    def fair_value(self) -> float:
        return heavy_computation(self.data)   # computed once, stored on self
```

### Decision guide


| Situation                             | Choice                     |
| ------------------------------------- | -------------------------- |
| Pure function, unbounded inputs       | `@lru_cache(maxsize=N)`    |
| Pure function, small/fixed inputs     | `@cache`                   |
| Computed instance attribute (no args) | `@cached_property`         |
| DB / file / network read              | Do not cache at this layer |
| Per-key expiry or invalidation needed | `cachetools` library       |


## Partial Application

`functools.partial` fixes some arguments of a callable, returning a new callable for the rest:

```python
from functools import partial

square = partial(pow, exp=2)
square(3)  # 9
```

