# Decorators

A decorator is a function that takes a function and returns a replacement for
it. Nothing in the interpreter implements decorators specially — they fall out
of two features Python already has: functions as values, and closures.

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

## Transforming vs. registering

Decorators split into two categories that look identical (`@thing` above a `def`) but do fundamentally different jobs:

- **Transforming** — returns a *different* callable (a `wrapper`) that replaces the original. Calling the decorated name now runs different code. Examples: `@functools.wraps`-based wrappers, `@retry`, [`@lru_cache`](functools.md#memoization-with-lru_cache).
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

A registering decorator applied to a method inside a class body fires *during* that body's execution — before the class object exists — so it can only write to something outside the class (a module-level registry, as above). See [class-creation.md](../objects/classes/class-creation.md) for why that ordering holds and how `__init_subclass__`/metaclasses read the result afterward.

## No arguments — 2 levels of nesting

```python
import functools

def my_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ...
        return func(*args, **kwargs)
    return wrapper
```

`@functools.wraps` preserves the metadata of the original function (name, docstring) instead of exposing the wrapper. To preserve the *type signature* as well, annotate the decorator with `ParamSpec` — see [callable.md](../typing/callable.md).

## With arguments — 3 levels of nesting

```python
def my_decorator(x_dec):                # 1. receives decorator arguments
    def decorator(func):                # 2. receives the function being decorated
        def wrapper(*args, **kwargs):   # 3. receives the function call arguments
            ...
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

Each level exists for one reason: the outermost captures the decorator's own
arguments, the middle captures the function, the innermost captures the call.
Drop a level and you lose one of the three.

## Related

- [functools.md](functools.md) — the stdlib decorators built on this shape: `lru_cache`, `cache`, `cached_property`, `partial`
- [scopes.md](../runtime/scopes.md#closures) — what a closure captures and when
- [callable.md](../typing/callable.md) — typing a decorator with `ParamSpec`
