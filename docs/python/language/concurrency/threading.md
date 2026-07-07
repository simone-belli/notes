# Threading — `concurrent.futures` API

`ThreadPoolExecutor` is the high-level interface for running I/O-bound work across threads. See [concurrency.md](concurrency.md) for when to use threads vs multiprocessing vs asyncio.

## Basic usage

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=10) as pool:
    futures = [pool.submit(fetch, url) for url in urls]
    results = [f.result() for f in futures]  # .result() blocks; re-raises exceptions
```

Manual thread control:

```python
import threading

t = threading.Thread(target=fn, args=(x,), daemon=True)
t.start()
t.join()   # wait for completion
```

`daemon=True` — thread is killed when the main program exits without waiting for it.

## Future mechanics

`submit()` returns a `Future` immediately — the task is scheduled and the caller moves on. `.result()` is where blocking actually happens:

```python
f1 = pool.submit(fetch, url_a)   # returns at once
f2 = pool.submit(fetch, url_b)   # returns at once
r1 = f1.result()                 # blocks until f1 done
r2 = f2.result()                 # then blocks until f2 done
```

Trap: iterating `.result()` in submission order means you wait on `f1` even if `f2` finished first.

## `as_completed` — process results as they arrive

```python
from concurrent.futures import as_completed

futures = {pool.submit(fetch, url): url for url in urls}
for f in as_completed(futures):
    url = futures[f]   # recover original arg from the dict
    try:
        data = f.result()
    except Exception as e:
        print(f"{url} failed: {e}")
```

`as_completed()` yields futures in completion order, not submission order. The `{submit(fn, x): x}` dict is the idiomatic way to map a future back to its input.

## Exception handling

Exceptions raised inside a thread are captured in the `Future` — they don't propagate until you call `.result()`:

```python
f = pool.submit(bad_fn, 42)
# no error in the main thread yet
f.result()           # raises here

f.exception()        # returns the exception object without raising, or None
f.done()             # True if finished (success or error)
```

`as_completed()` yields failed futures too — use `f.exception()` to inspect without aborting the batch.

## Shared state

!!! warning "counter += 1 is not atomic — concurrent threads will corrupt it"
    `counter += 1` compiles to three bytecode instructions: LOAD, ADD, STORE. The GIL can be released between any two of them, letting another thread read the pre-increment value. The result: updates are silently lost. Use `threading.Lock()` around any read-modify-write cycle, or `queue.Queue` to communicate between threads without shared mutable state.

Threads share memory. `counter += 1` is not atomic (read → add → write), so concurrent threads can corrupt it:

```python
lock = threading.Lock()
with lock:
    counter += 1   # only one thread at a time
```

`queue.Queue` is thread-safe by design — the idiomatic way to pass work items between threads without explicit locking.

## Related notes

- [concurrency.md](concurrency.md) — GIL, when to use threads vs processes vs asyncio, decision guide
- [asyncio.md](asyncio.md) — cooperative concurrency alternative for high-scale I/O
