# Concurrency in Python: GIL, Threads, Processes, asyncio

## The GIL

The **Global Interpreter Lock** is a CPython mutex that allows only one thread to execute Python bytecode at a time. It exists to protect CPython's reference-counting garbage collector, which is not thread-safe.

- The GIL is a CPython detail — Jython and PyPy-STM don't have one.
- The GIL protects CPython internals, **not your shared data**. You still need locks for shared mutable state.

## Threading — I/O-bound work

The GIL is **released during I/O waits** (network, disk, `sleep`). Threads run concurrently while blocked on I/O, making them effective for I/O-bound workloads despite the GIL.

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=10) as pool:
    futures = [pool.submit(fetch, url) for url in urls]
    results = [f.result() for f in futures]
```

- `Thread(target=fn, args=(...), daemon=True)` for manual control.
- Use `threading.Lock` / `queue.Queue` to protect shared state.

## Multiprocessing — CPU-bound work

Separate OS processes each have their own GIL → true parallelism across cores.

```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(heavy_fn, inputs))
```

- **Cost**: data is pickled between processes. Large arrays → use `multiprocessing.shared_memory`.
- Workers must be defined at module level (lambdas can't be pickled).
- **numpy exception**: numpy/scipy release the GIL during C operations — threads can parallelise numpy work.

## asyncio — I/O-bound, high concurrency

Single-threaded cooperative multitasking. Coroutines yield at `await` points; the event loop runs another coroutine while one waits for I/O.

```python
import asyncio, aiohttp

async def fetch(session, url):
    async with session.get(url) as r:
        return await r.text()

async def main():
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch(session, u) for u in urls])

asyncio.run(main())
```

Key primitives:

```python
await asyncio.gather(*coros)       # run concurrently, collect results
asyncio.create_task(coro())        # schedule without waiting
await asyncio.sleep(n)             # non-blocking sleep
await loop.run_in_executor(None, blocking_fn, arg)  # offload sync code to thread pool
```

**Never call blocking code** (e.g. `requests.get`) inside `async def` — it blocks the entire event loop.

## Decision guide

| Workload | Tool |
|---|---|
| I/O-bound, simple | `ThreadPoolExecutor` |
| I/O-bound, high concurrency | `asyncio` + async libs |
| CPU-bound, pure Python | `ProcessPoolExecutor` |
| CPU-bound, numpy/scipy | Threads often fine (GIL released) |

## asyncio vs threads for I/O

| | Threads | asyncio |
|---|---|---|
| Context switching | OS (preemptive) | Cooperative (`await`) |
| Scale | Hundreds | Tens of thousands |
| Existing sync code | Works as-is | Must use `run_in_executor` |
| Complexity | Lower | Requires async throughout |

## Related notes

- [`functools.md`](functools.md) — `@lru_cache` thread-safety caveat
- [`context-managers.md`](context-managers.md) — `async with` uses the same `__aenter__`/`__aexit__` protocol
