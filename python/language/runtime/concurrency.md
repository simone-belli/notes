# Concurrency in Python: GIL, Threads, Processes, asyncio

## Foundations

**Process**: OS-level container with private memory and at least one thread. Isolated — processes can't read each other's memory.

**Thread**: unit of execution *within* a process. Threads share memory with each other, which makes them fast to create and dangerous to use carelessly.

**Preemptive scheduling**: the OS interrupts threads every few milliseconds and switches between them, giving the illusion of simultaneous execution on a single core. Threads have no say in when they're interrupted.

**Blocking I/O**: when a thread asks the OS for data (network, disk), the OS parks the thread and schedules other work. The thread does nothing until the data arrives. This "wasted" time is what concurrency exploits.

**Concurrency vs parallelism**:

- Concurrency — multiple tasks *in progress* at once, possibly interleaved on one core.
- Parallelism — multiple tasks *literally running simultaneously* on separate cores.

I/O-bound work only needs concurrency (one core is fine while threads wait). CPU-bound work needs parallelism (multiple cores actually computing).

---

## The GIL

CPython uses reference counting for garbage collection. Because reference counts are not thread-safe, CPython uses a single lock — the **Global Interpreter Lock** — so that only one thread executes Python bytecode at a time.

The GIL is **released** during:

- Any blocking I/O call (network, disk, `sleep`) — OS takes over, Python doesn't need it.
- C extensions that explicitly release it (numpy, scipy).

The GIL protects CPython internals, **not your shared data**. Concurrent access to a Python `list` or `dict` still requires explicit locking.

---

## Threading — I/O-bound work

While one thread waits for I/O (GIL released), another thread runs Python code. Threads genuinely overlap during I/O waits.

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=10) as pool:
    futures = [pool.submit(fetch, url) for url in urls]
    results = [f.result() for f in futures]
```

See [threading.md](threading.md) for `Future` mechanics, `as_completed`, exception handling, and shared state.

---

## Multiprocessing — CPU-bound work

For CPU-bound work, threads don't help: the GIL limits execution to one thread at a time regardless of how many cores you have. **Multiprocessing** spawns separate OS processes, each with its own interpreter and GIL — real parallelism across cores.

```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(heavy_fn, inputs))
```

Costs:

- Data is **pickled** (serialised) to pass between processes — overhead for large inputs.
- Workers must be defined at module level (lambdas can't be pickled).
- Process startup is slow (~100ms); amortise over many tasks.

For large arrays: use `multiprocessing.shared_memory` to avoid copying.

**numpy exception**: numpy/scipy release the GIL during C operations — threads *can* parallelise numpy work. Profile before using `ProcessPoolExecutor` for numerical code.

---

## asyncio — I/O-bound, high concurrency

A single-threaded **event loop** runs coroutines cooperatively. Instead of the OS interrupting threads, coroutines voluntarily yield at `await` points. The event loop runs another coroutine while one waits for I/O. Scales to tens of thousands of concurrent tasks with low overhead (no per-thread stack, no OS context switches).

See [asyncio.md](asyncio.md) for a deep dive into `async def`, `await`, `asyncio.run()`, and `asyncio.gather()`.

Key primitives:

```python
await asyncio.gather(*coros)                         # run coroutines concurrently, collect results
asyncio.create_task(coro())                          # schedule without waiting
await asyncio.sleep(n)                               # non-blocking sleep
await loop.run_in_executor(None, blocking_fn, arg)   # offload sync call to thread pool
```

**Never call blocking code** (e.g. `requests.get`, `time.sleep`) inside `async def` — it freezes the entire event loop.

---

## Decision guide

| Workload                    | Tool                                         |
| --------------------------- | -------------------------------------------- |
| I/O-bound, few tasks        | `ThreadPoolExecutor`                         |
| I/O-bound, high concurrency | `asyncio` + async libraries                  |
| CPU-bound, pure Python      | `ProcessPoolExecutor`                        |
| CPU-bound, numpy/scipy      | Threads often fine (GIL released in C layer) |

### Threads vs asyncio for I/O

|                    | Threads         | asyncio                               |
| ------------------ | --------------- | ------------------------------------- |
| Context switching  | OS (preemptive) | Cooperative (`await`)                 |
| Scale              | Hundreds        | Tens of thousands                     |
| Existing sync code | Works as-is     | Must use `run_in_executor` or rewrite |
| Risk               | Race conditions | Blocking calls freeze the loop        |

---

## Key vocabulary

| Term           | Meaning                                                                 |
| -------------- | ----------------------------------------------------------------------- |
| **Coroutine**  | `async def` function that suspends at `await` and resumes later         |
| **Event loop** | asyncio's scheduler — runs one coroutine at a time, switches at `await` |
| **Future**     | Placeholder for a result that will exist later (`concurrent.futures`)   |
| **Task**       | asyncio's version of a Future — a scheduled coroutine                   |
| **Pickle**     | Python's serialisation format; used to pass data between processes      |

## Related notes

- [threading.md](threading.md) — `ThreadPoolExecutor` API, futures, `as_completed`, shared state
- [asyncio.md](asyncio.md) — full async/await deep dive
- [functools.md](../functional/functools.md) — `@lru_cache` thread-safety note
- [context-managers.md](context-managers.md) — `async with` uses `__aenter__`/`__aexit__`
