---
quiz: core
---

# Scopes and Namespaces

A **namespace** is a dict mapping names to objects. Every module, every function call, and every class body gets its own. Name resolution searches them in LEGB order.

## LEGB rule

When Python sees a bare name, it searches four scopes in order and stops at the first hit:

| Level | Scope | Example |
|-------|-------|---------|
| **L** — Local | current function's namespace | `x = 1` inside `def f()` |
| **E** — Enclosing | any enclosing function's namespace | closure variables |
| **G** — Global | module top-level namespace | `x = 1` at module level |
| **B** — Built-in | `builtins` module | `len`, `print`, `range` |

```python
x = "global"

def outer():
    x = "enclosing"
    def inner():
        x = "local"
        print(x)   # "local"
    inner()
    print(x)       # "enclosing"

outer()
print(x)           # "global"
```

## Local variables

Any name **assigned** anywhere inside a function is local — Python decides at compile time, not runtime.

```python
x = 10

def f():
    print(x)   # UnboundLocalError — x is assigned below, so Python
    x = 20     # classifies it as local for the whole function
```

This is the most common scope bug: Python sees an assignment for `x` in the function body and makes it local everywhere in that function, including lines above the assignment.

## `global` — write to module-level from inside a function

Reading a global works without any declaration. Assigning requires `global`:

```python
counter = 0

def increment():
    global counter   # without this: UnboundLocalError
    counter += 1
```

Only needed when **rebinding** the name. Mutating a mutable global (`.append`, `.update`) doesn't need `global` — you're not reassigning the name, just modifying the object.

## `nonlocal` — write to an enclosing function's variable

Same problem one scope up — assignment creates a local instead of updating the closure variable:

```python
def make_counter():
    count = 0
    def increment():
        nonlocal count   # without this: UnboundLocalError
        count += 1
    return increment
```

`nonlocal` searches outward through enclosing function scopes (never global or built-in).

## Closures

A function defined inside another function captures the **enclosing variable**, not its value. Closures are the mechanism behind decorators — see [functools.md](../functional/decorators.md#first-class-functions) for how `@decorator` reduces to "a closure, plus `@` sugar for reassignment."

```python
def make_multiplier(n):
    def multiply(x):
        return x * n   # n is a free variable — captured from enclosing scope
    return multiply

double = make_multiplier(2)
double(5)  # → 10
```

!!! warning "Closures capture the variable, not its value — the late-binding gotcha"
    All three lambdas in `[lambda: i for i in range(3)]` share the same `i` variable. By the time any of them is called, the loop has finished and `i == 2`. The fix is the default-argument trick: `lambda i=i: i` captures the *current value* at definition time because default arguments are evaluated once when the `lambda` statement executes.

### Late-binding gotcha

Closures capture the variable, not its value at capture time:

```python
funcs = [lambda: i for i in range(3)]
funcs[0]()  # → 2, not 0 — all three see the final value of i
```

Fix: bind the value as a default argument (evaluated at definition time):

```python
funcs = [lambda i=i: i for i in range(3)]
funcs[0]()  # → 0
```

!!! note "Class scope is not part of the LEGB chain for methods"
    A bare name inside a method skips the class body entirely, jumping straight from Local to Enclosing (outer functions) to Global. Class attributes must always be accessed as `self.x` or `ClassName.x` — never as a bare `x` inside a method.

## Class scope is not enclosing scope

Class bodies create a namespace, but methods defined inside them cannot access it via bare names:

```python
class C:
    x = 10
    def f(self):
        return x        # NameError — class scope is not in LEGB chain
        return self.x   # correct
```

## Quick reference

| Goal | Syntax |
|------|--------|
| Read a global | just use the name — LEGB finds it |
| Write to a global | `global x` inside the function |
| Write to an enclosing variable | `nonlocal x` inside the inner function |
| Capture value (not variable) in a closure | `lambda x=x: x` default-argument trick |

## Related

- [import-system.md](import-system.md) — module namespaces (`__dict__`, `sys.modules`)
- [../functional/iterators-generators.md](../functional/iterators-generators.md) — generator functions and their frame state
- [../functional/lazy-evaluation.md](../functional/lazy-evaluation.md) — closures as lazy pipelines
