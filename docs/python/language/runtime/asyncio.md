# asyncio — Core Mechanics

See [concurrency.md](concurrency.md) for the comparison with threads and the decision guide.

!!! note "async def defines a factory, not a running task — calling it does nothing"
    `async def fetch(url)` is a function that *returns* a coroutine object. The body doesn't run until something drives it with `await` or schedules it as a Task. This surprises people used to regular functions, where calling = executing.

## async def: coroutine function vs coroutine object

`async def` defines a **coroutine function**. Calling it returns an inert **coroutine object** — the body does not run:

```python
async def fetch(url):
    ...

c = fetch("https://example.com")   # returns coroutine object, runs nothing
```

Compare to a regular function, where calling it executes immediately. The coroutine object only runs when driven by `await` or the event loop. Discarding it unrun produces a `RuntimeWarning`.

The most common bug this causes:

```python
result = fetch(url)         # BUG: creates a coroutine object, discards it
result = await fetch(url)   # CORRECT
```

## await: suspension and resumption

`await expr` suspends the current coroutine and yields control to the event loop, which can then run other coroutines. When the awaited thing completes, the event loop resumes this coroutine.

```python
async def process(url):
    response = await session.get(url)   # suspend — event loop runs others
    text = await response.text()         # suspend again
    return text
```

`await` can only appear inside `async def`. You can only `await` an **awaitable**: coroutine objects, `Task`, `Future`, or objects with `__await__`.

`await` is not blocking — a blocked thread holds the GIL and does nothing; an awaited coroutine suspends and frees the event loop to run other work.

## asyncio.run(): the entry point

Bridges synchronous code into the async world. Creates an event loop, runs one top-level coroutine to completion, then closes the loop:

```python
value = asyncio.run(main())   # blocks until main() returns
```

Can only be called from synchronous code — not from inside a running event loop. One loop at a time.

## asyncio.gather(): concurrent execution

Schedules multiple coroutines as Tasks and runs them concurrently. Returns when all complete:

```python
results = await asyncio.gather(
    fetch("https://a.com"),
    fetch("https://b.com"),
    fetch("https://c.com"),
)
# results = [result_a, result_b, result_c]  — submission order, not completion order
```

What gather does: wraps each argument in a `Task` (scheduled immediately), then suspends the caller until all Tasks finish.

**Exception handling**:

```python
# Default (return_exceptions=False): first exception propagates, others cancelled
try:
    results = await asyncio.gather(a(), b(), c())
except Exception as e:
    ...

# return_exceptions=True: all run to completion; exceptions returned as values
results = await asyncio.gather(a(), b(), c(), return_exceptions=True)
for r in results:
    if isinstance(r, Exception):
        print(f"failed: {r}")
```

## create_task(): fire and overlap

`create_task()` schedules a coroutine without awaiting it immediately — the task runs whenever the event loop has cycles:

```python
task = asyncio.create_task(fetch(url))   # scheduled, starts running
await other_work()                        # loop runs fetch() here too
result = await task                       # wait if not done
```

Use `create_task()` to overlap sequential work with background tasks. Use `gather()` for a batch you want to collect all at once.

## Event loop — mental model

Single-threaded scheduler: runs one coroutine at a time, switches at every `await`. Concurrency comes from cooperative yielding, not parallelism.

!!! warning "Any blocking call freezes the entire event loop"
    The event loop is single-threaded. A `time.sleep(5)` or `requests.get(url)` inside `async def` blocks the thread for the full duration — no other coroutine runs. Replace with `await asyncio.sleep()` and async-native libraries (`aiohttp`, `asyncpg`, `aiofiles`). For unavoidable sync calls, use `await loop.run_in_executor(None, blocking_fn)` to offload to a thread pool.

Consequence: **any blocking call freezes all other coroutines**:

```python
# BAD — blocks the whole event loop
async def bad():
    time.sleep(5)
    data = requests.get(url)

# GOOD — suspends this coroutine, others keep running
async def good():
    await asyncio.sleep(5)
    async with aiohttp.ClientSession() as s:   # see aiohttp.md
        data = await s.get(url)
```

Use async-native libraries (`aiohttp`, `asyncpg`, `aiofiles`). Offload unavoidable sync calls with `await loop.run_in_executor(None, blocking_fn, arg)`.

## Async context managers and iterators

```python
async with resource() as r:    # awaits __aenter__ / __aexit__
    ...

async for item in aiter():     # awaits __anext__ each step
    ...
```

## asyncio.Semaphore — capping concurrency

A Semaphore is a counter that starts at `n`. Each `async with sem:` decrements it; when it hits 0, the next coroutine blocks until one exits and increments it back. At most `n` coroutines run the guarded block at any moment.

```python
sem = asyncio.Semaphore(10)   # created once in outer scope

async def fetch(url):
    async with sem:            # blocks here if 10 already running
        ...
```

Primary use case: preventing `asyncio.gather()` from firing hundreds of requests simultaneously — see [aiohttp.md](../../tooling/aiohttp.md#concurrent-requests).

## asyncio.Lock — mutual exclusion

The event loop is single-threaded but switches coroutines at every `await`. If two coroutines share mutable state and both `await` mid read-modify-write, you get a race:

```python
counter = 0

async def increment():
    global counter
    value = counter          # read
    await asyncio.sleep(0)   # yield — another coroutine can run here
    counter = value + 1      # writes stale value
```

`asyncio.Lock` serialises the critical section — only one coroutine can hold it at a time:

```python
lock = asyncio.Lock()   # created once in outer scope

async def increment():
    async with lock:       # suspends here if another coroutine holds the lock
        value = counter
        await asyncio.sleep(0)
        counter = value + 1
```

!!! note "Lock vs Semaphore"
    `asyncio.Lock` is `Semaphore(1)` with clearer intent: use Lock for exclusive access to shared state, Semaphore for capping the number of concurrent workers. Don't use `asyncio.Lock` across threads — it's not thread-safe; use `threading.Lock` there.

## Key vocabulary

| Term | Meaning |
|------|---------|
| Coroutine function | `async def fn()` — calling it returns a coroutine object |
| Coroutine object | Inert result of calling a coroutine function; must be awaited to run |
| `await` | Suspends current coroutine; yields to event loop |
| Event loop | Scheduler — runs one coroutine at a time, switches at `await` |
| Task | A scheduled coroutine that runs independently |
| `asyncio.run()` | Creates loop, runs top-level coroutine, closes loop |
| `asyncio.gather()` | Runs N coroutines concurrently, returns all results |
| `asyncio.create_task()` | Schedules a coroutine as a Task without awaiting it |

## Related notes

- [concurrency.md](concurrency.md) — threads vs asyncio decision guide, GIL, multiprocessing
- [context-managers.md](context-managers.md) — `async with` protocol (`__aenter__`/`__aexit__`)
- [../../tooling/aiohttp.md](../../tooling/aiohttp.md) — async HTTP client built on asyncio
