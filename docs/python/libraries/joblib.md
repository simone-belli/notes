---
tags:
  - concurrency
  - performance
---

# joblib

Three small tools for numerical Python: a parallel loop, a disk-backed cache,
and a fast pickle for array-heavy objects. No scheduler, no cluster, no daemon
— and it is the layer behind every `n_jobs=` argument in
[scikit-learn](../../ml/scikit-learn/estimators.md).

```python
import joblib
from joblib import Parallel, delayed, Memory, parallel_config
```

---

## Parallel + delayed

```python
from joblib import Parallel, delayed

results = Parallel(n_jobs=-1)(delayed(f)(x, scale=2) for x in items)
```

- `delayed(f)(x, scale=2)` does not call `f` — it returns a deferred
  `(func, args, kwargs)` tuple.
- Results come back **in input order**, not completion order (unlike
  `concurrent.futures`, see [threading.md](../language/concurrency/threading.md)).
- `Parallel(n_jobs=1)(...)` runs in-process — drop to it to get usable
  tracebacks and `pdb`.

`n_jobs` values:

| Value | Workers |
|---|---|
| `1` | serial, no pool created |
| `-1` | $n_{\text{cores}}$ |
| `-2` | $n_{\text{cores}} - 1$ — leaves a core to type on |
| `None` | 1, unless a `parallel_config` block says otherwise |

`return_as="generator"` yields results as they finish (still ordered) instead of
materialising all $n$ at once.

## Backends

| Backend | Mechanism | Use for |
|---|---|---|
| `loky` (default) | processes, pool reused | CPU-bound pure Python |
| `threading` | threads | work that releases the Global Interpreter Lock (GIL) — numpy, scipy, I/O |
| `multiprocessing` | `fork` pool | legacy; avoid |

```python
from joblib import parallel_config

with parallel_config(backend="threading", n_jobs=8):
    Parallel()(delayed(load_url)(u) for u in urls)
```

Why `loky` beats a raw `ProcessPoolExecutor`
([concurrency.md](../language/concurrency/concurrency.md)):

- Workers are **reused** across successive `Parallel` calls — process startup
  (~100 ms) is paid once, not per call.
- It serialises with **cloudpickle**, so lambdas, closures, and
  notebook-defined functions work; plain `pickle` refuses all three.
- It always spawns, never bare-`fork`s, avoiding deadlocks when the parent holds
  a lock or thread pool.

!!! tip "Large arrays are memory-mapped, not pickled"
    Arguments above `max_nbytes` (default 1 MB) are dumped to a temp `.npy` and
    passed to workers as a read-only `numpy.memmap`, so the OS shares one copy
    of the pages instead of pickling the array $n_{\text{jobs}}$ times. The
    corollary: a worker must never mutate its inputs.

## Oversubscription

Nested parallelism multiplies, it does not add:

$$
n_{\text{threads}}^{\text{total}} = n_{\text{jobs}} \times n_{\text{threads}}^{\text{inner}}
$$

8 processes × 8 Basic Linear Algebra Subprograms (BLAS) threads = 64 threads on
8 cores, all fighting for the same caches — slower than serial. joblib caps the
inner libraries at $\lfloor n_{\text{cores}} / n_{\text{jobs}} \rfloor$ threads
per worker (via `threadpoolctl`), but it cannot see nesting in *your* code.

!!! warning "Parallelise at exactly one level"
    `GridSearchCV(n_jobs=-1)` wrapped around an estimator that itself has
    `n_jobs=-1` is the canonical mistake — set the inner one to `1`. Same for
    `cross_val_score(n_jobs=-1)`; see
    [hyperparameter-search.md](../../ml/scikit-learn/hyperparameter-search.md).

## Task overhead

Each task costs a serialise → send → deserialise round trip:

$$
T_{\text{parallel}} \approx \frac{n \cdot t_{\text{task}}}{n_{\text{jobs}}} + n \cdot t_{\text{overhead}}
$$

When $t_{\text{task}} \ll t_{\text{overhead}}$ the second term wins and
parallelism is a net loss. The default `batch_size="auto"` grows the batch until
one batch takes ~$0.2\,\text{s}$, which rescues the many-tiny-tasks case.

## Memory — disk-backed cache

```python
from joblib import Memory

memory = Memory("cache_dir", verbose=0)

@memory.cache
def featurise(df, window):
    ...
```

Differences from
[`functools.lru_cache`](../language/functional/functools.md):

- **Persistent** — survives the process; lives in `cache_dir`.
- Hashes argument **contents**, so numpy arrays and DataFrames are valid keys.
- The key includes the function source, so editing the body invalidates its
  entries.
- Hashing a big array is a full pass over it, and the directory grows until
  `memory.clear()`.

`Pipeline(..., memory=memory)` caches fitted transformers, so a search that only
varies the final estimator skips re-running preprocessing
([pipelines.md](../../ml/scikit-learn/pipelines.md)).

## dump / load

```python
import joblib

joblib.dump(model, "model.joblib", compress=3)
model = joblib.load("model.joblib")
```

Pickle with a numpy fast path — arrays are written as raw contiguous blocks,
which is faster and permits `mmap_mode="r"` on load.

!!! warning "A `.joblib` file is executable code, not data"
    `joblib.load` on an untrusted file runs arbitrary code. It is also not an
    archival format: the pickle embeds class paths, so a numpy or scikit-learn
    upgrade can make it unloadable. For anything long-lived, persist the
    params and refit.

## When not to use it

- **I/O-bound at high concurrency** — [asyncio](../language/concurrency/asyncio.md)
  scales past what a thread pool can.
- **Distributed compute** — joblib is single-machine; `backend="dask"` just
  hands the work to Dask.
- **One big array operation** — a threaded BLAS build already parallelises it;
  `Parallel` adds only overhead.

## Related notes

- [concurrency.md](../language/concurrency/concurrency.md) — GIL, processes vs threads, pickling costs
- [cross-validation.md](../../ml/scikit-learn/cross-validation.md) — `n_jobs` on fold loops
- [reproducibility.md](../../ml/concepts/reproducibility.md) — why `n_jobs > 1` breaks bit-identical runs
