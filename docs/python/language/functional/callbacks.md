---
tags:
  - design-patterns
---

# Callbacks

A callback is a function handed to other code so that code can call it back when
it chooses. You supply the *what*; the callee owns the *when* — that reversal is
**inversion of control**.

Python needs no special machinery for this: functions are values (see
[Decorators](decorators.md)), so passing a callback is just passing an argument
that happens to be callable.

```python
# you own the "when"
for row in rows:
    process(row)

# sorted() owns the "when" — it decides when and how often to call key
sorted(rows, key=lambda r: r.price)
```

## Where they show up

- **Sort keys and predicates** — `sorted(key=...)`, `min`/`max(key=...)`,
  `filter(pred, xs)`, `map(f, xs)`.
- **Factories** — `collections.defaultdict(list)`,
  `dataclasses.field(default_factory=list)`.
- **Lifecycle hooks** — `atexit.register(fn)`, `signal.signal(SIGINT, handler)`.
- **Concurrency** — `threading.Thread(target=fn)`, `Future.add_done_callback(fn)`
  (see [Threading](../concurrency/threading.md)). Here a callback is genuinely
  necessary: the result does not exist yet.
- **Frameworks** — route handlers, GUI events, training-loop and experiment
  hooks.

## Carrying state

A bare function has no memory. Three idiomatic ways to attach context:

### `functools.partial` — freeze arguments

```python
from functools import partial

def on_done(future, *, label):
    print(label, future.result())

executor.submit(work).add_done_callback(partial(on_done, label="job-1"))
```

Best when the context is just arguments — unlike a lambda it is picklable
(required by `multiprocessing`) and introspectable. See
[`functools`](functools.md).

### Closure — capture the enclosing scope

```python
def make_handler(label):
    def handler(future):
        print(label, future.result())
    return handler
```

Flexible, but subject to the late-binding trap below.

### Callable object — state that accumulates

```python
class Collector:
    def __init__(self):
        self.results = []

    def __call__(self, future):
        self.results.append(future.result())
```

When the callback accumulates across calls, an object beats a closure over a
mutable default — and it is far easier to inspect and test.

## Gotchas

!!! warning "Late binding in loops"
    A closure captures the *variable*, not its value:

    ```python
    handlers = [lambda: print(i) for i in range(3)]
    [h() for h in handlers]        # 2 2 2 — not 0 1 2
    ```

    All three share one `i`, read at call time. Bind at definition time with a
    default argument (`lambda i=i: ...`) or `partial`. Full mechanics in
    [Scopes and Closures](../runtime/scopes.md#closures).

- **Exceptions cross an ownership boundary.** Because the callee calls you, your
  exception surfaces in *their* stack, and their policy decides what happens:
  `add_done_callback` logs and swallows, `atexit` prints and continues, a GUI
  loop may die. Catch what you care about inside the callback.
- **Bound methods at class level.** `callback = some_function` in a class body
  makes it a method that receives `self` — Python functions are descriptors.
  Assign in `__init__` (`self.callback = fn`) or wrap in
  [`staticmethod`](../objects/classes/data-model.md#method-types).
- **Callback hell.** In async code, `async`/`await` exists to flatten nested
  callbacks back into straight-line code — prefer it to `add_done_callback`
  chains. See [asyncio](../concurrency/asyncio.md).

## Typing

`Callable[[Arg], Return]` covers the common case but cannot express keyword
arguments, defaults, or `*args` — for those use a callback `Protocol` with
`__call__`.

```python
from typing import Callable

def retry(op: Callable[[], int], on_error: Callable[[Exception], None]) -> int:
    ...
```

Details and the variance rules are in [Callable](../typing/callable.md).

## When not to use one

!!! tip "Only invert control when the callee owns the timing"
    If *you* own the timing, a plain return value is simpler and far easier to
    debug — a callback buys nothing and costs you a stack frame you don't
    control.

- **Iterator or generator** instead of a per-item callback — the consumer keeps
  control and can compose lazily. See
  [Iterators and Generators](iterators-generators.md).
- **Context manager** instead of a setup/teardown callback pair, covered in
  [Context Managers](../runtime/context-managers.md).
- **Protocol or strategy object** when you need several related hooks; a bag of
  five `on_*` callbacks usually wants to be one object.

## Related

- [Decorators](decorators.md) — first-class functions; a registering decorator is
  callback registration with `@` sugar
- [Scopes and Closures](../runtime/scopes.md) — what a closure captures
- [Callable](../typing/callable.md) — annotating the callback parameter
