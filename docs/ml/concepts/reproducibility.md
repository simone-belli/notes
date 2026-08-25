---
tags:
  - config
---

# Reproducibility and Seeding

Every layer of an ML stack has its own random number generator (RNG), and
none of them share state: Python's `random`, NumPy's legacy global generator,
NumPy's modern `Generator`, [scikit-learn](../scikit-learn/estimators.md)'s
per-call `random_state`, and [Optuna](../experiments/optuna.md)'s sampler `seed` are five
independent streams. Missing one breaks reproducibility for the whole run
even if the other four are pinned.

## Two strategies

**Global seeding** — `random.seed(N)`, `np.random.seed(N)` once at startup;
every later call draws from that seeded global state.

- Fine for a single-threaded script.
- Breaks under parallelism: workers that fall through to the same global
  generator either race (threads) or, if each inherits a copy of the seeded
  state (multiprocessing), silently draw the **same** stream instead of
  independent ones.
- `np.random.seed` is soft-deprecated by NumPy itself for this reason.

**Explicit RNG instances, passed down** — create one generator per
independent unit of work, pass it as an argument:

```python
import numpy as np

rng = np.random.default_rng(42)     # PCG64, explicit instance
child_rngs = rng.spawn(4)           # independent streams, one per worker/fold
```

`Generator.spawn(n)` (NumPy ≥ 1.25) is the correct way to give parallel
workers independent-but-reproducible randomness instead of one shared or
duplicated stream. This is the model scikit-learn and Optuna are already
built on — it's why they take `random_state=`/`seed=` per call rather than
reading a global seed.

## scikit-learn's `random_state`

```python
RandomForestClassifier(random_state=None)   # draws from the global legacy RNG — not reproducible
RandomForestClassifier(random_state=42)     # int → fresh, independent RandomState(42) every call
RandomForestClassifier(random_state=rs)     # RandomState/Generator instance → consumed and mutated,
                                             # deliberately different draws across repeated calls
```

- **`None`** (the default almost everywhere) is only reproducible if you've
  globally seeded, and isn't independent of other `None` calls sharing that
  same global RNG.
- **An int** is the reproducible default: sklearn wraps it in a fresh
  `RandomState(int)` per call, so the same int handed to two different
  estimators gives each an independent, reproducible stream.
- **A `RandomState`/`Generator` instance** is for deliberately wanting
  *different* draws across repeated calls with the "same" seed — e.g. many
  distinct bootstrap resamples in a loop.

`sklearn.utils.check_random_state(seed)` normalizes all three forms — use it
in a [custom estimator](../scikit-learn/custom-transformers.md) that needs
the same convention.

```python
train_test_split(X, y, random_state=42)
KFold(n_splits=5, shuffle=True, random_state=42)          # ignored (and warns) if shuffle=False
RandomizedSearchCV(estimator, param_distributions, random_state=42)
```

`TimeSeriesSplit` never shuffles and has no `random_state` at all — see
[Time-Series Validation](time-series-validation.md).

!!! warning "Pinned seeds ≠ bit-identical under `n_jobs`"
    Reproducible means the same *sequence of draws*, not necessarily
    bit-identical floating point: parallel workers can sum partial results in
    a nondeterministic completion order, shifting the last bits of a
    float-associativity-sensitive computation.

## Optuna: two seeds, not one

`TPESampler(seed=42)` seeds only *which points the sampler proposes* — it has
no visibility into what the objective does with them:

```python
def objective(trial):
    lr = trial.suggest_float("lr", 1e-4, 1e-1, log=True)        # seeded by TPESampler
    X_tr, X_va, y_tr, y_va = train_test_split(X, y, random_state=42)  # separate seed, own responsibility
    model = RandomForestClassifier(n_estimators=100, random_state=42)
```

Without the split/model seeds, rerunning `study.optimize(...)` reproduces the
same sequence of proposed `lr` values but a *different* `best_value` every
time. Using the same fixed int inside every trial (rather than varying it) is
usually right: it holds the split constant across trials, so score
differences are attributable to the swept hyperparameters, not to a
different random split landing under a different trial.

## A central seeding module

Worth building once rather than sprinkling `random_state=42` as a literal:

```python
# seeding.py
import os
import random
import numpy as np

DEFAULT_SEED = 42

def set_global_seed(seed: int = DEFAULT_SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)                      # catch-all for code that only reads the global
    os.environ["PYTHONHASHSEED"] = str(seed)  # only takes effect on process *start* — see below

def make_rng(seed: int = DEFAULT_SEED) -> np.random.Generator:
    return np.random.default_rng(seed)        # pass this down explicitly — the one to prefer
```

- Two exports because the two strategies solve different problems:
  `set_global_seed` is a best-effort catch-all for third-party code that only
  reads ambient global state; `make_rng` / passing an explicit int is what
  sklearn and Optuna calls actually rely on.
- `PYTHONHASHSEED` affects `str`/`bytes`/`datetime` hashing (and thus
  `set`/`dict` iteration order, hash-based sketches) — but CPython reads it
  once at interpreter *startup*, so setting it from inside the running
  process has no effect. It only works launched (`PYTHONHASHSEED=42 python
  run.py`) or via a self-exec. Skip it unless something depends on a
  reproducible hash-based fingerprint.
- One overridable `DEFAULT_SEED` constant, not a hardcoded literal per call
  site — makes a seed sweep (checking a result isn't a one-seed artifact) a
  one-line change.
- Call `set_global_seed` once, at the entrypoint (`if __name__ ==
  "__main__":`) — not inside library code or a function that might run more
  than once.
- Extend with `torch.manual_seed(seed)` / `tf.random.set_seed(seed)` for
  other libraries in the stack — same principle, each library's own hook.

!!! note "What seeding doesn't cover"
    GPU kernels (some convolutions, atomic-add reductions) can be
    nondeterministic regardless of seed unless deterministic algorithms are
    explicitly requested, usually at a performance cost. Reproducibility
    across time also needs dependency versions pinned — a `random_state=42`
    forest isn't guaranteed bit-identical across library versions.

## Related

- [Optuna](../experiments/optuna.md) — `TPESampler(seed=...)`
- [The Estimator API](../scikit-learn/estimators.md) — `random_state` as a hyperparameter
- [Hyperparameter Search](../scikit-learn/hyperparameter-search.md) — `random_state` on `RandomizedSearchCV`
- [Train/Test Splitting](../scikit-learn/splitting.md) — `random_state` on splitters
- [Random permutations](../../python/language/stdlib/random.md) — `random.seed` vs `random.Random`, the stdlib layer this builds on
