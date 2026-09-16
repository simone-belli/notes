---
tags:
  - performance
  - concurrency
---

# Data Loading

`Dataset` and `DataLoader` are an **iteration protocol**, not a data-management
framework. A `Dataset` answers two questions; a `DataLoader` turns those answers
into batches. That is the whole contract — and it says nothing about *which*
observations may legitimately sit in a batch together.

```python
from torch.utils.data import Dataset, DataLoader

class WindowDataset(Dataset):
    def __init__(self, series, targets, length):
        self.series, self.targets, self.length = series, targets, length

    def __len__(self):                      # how many items exist
        return len(self.series) - self.length

    def __getitem__(self, i):               # give me item i, as one sample
        return self.series[i : i + self.length], self.targets[i + self.length]

ds = WindowDataset(series, targets, length=20)
loader = DataLoader(ds, batch_size=32, shuffle=True, num_workers=4)
```

!!! note "The boundary is yours"
    scikit-learn encodes the fit/transform boundary in
    [`Pipeline`](../scikit-learn/pipelines.md) and can therefore make some
    [leakage](../concepts/data-leakage.md) unreachable. PyTorch has no equivalent
    — no fit/transform distinction, no notion of a fold. The boundary exists only
    where you put it.

## The two protocols

**Map-style** — `__len__` + `__getitem__`. Indices are just an address space;
they need not be contiguous or meaningful. Nothing requires the returned object
to be a tensor or `__getitem__` to be cheap — per-sample decoding, disk I/O and
augmentation all live there.

```python
from torch.utils.data import TensorDataset
ds = TensorDataset(X, y)        # __getitem__(i) -> (X[i], y[i]); no subclass needed
```

**Iterable-style** — subclass `IterableDataset` and implement `__iter__`, for
sources with no random access (a stream, a file too large to index). The
trade-off is severe: `shuffle=` and `sampler=` are unavailable, and with
`num_workers > 1` every worker runs the same `__iter__` unless you shard with
`torch.utils.data.get_worker_info()`. Prefer map-style unless you genuinely
cannot index.

## What DataLoader does

Each iteration is a four-stage pipeline:

1. **Sampler** — emits single indices. `shuffle=False` → `SequentialSampler`,
   `shuffle=True` → `RandomSampler`. That is all `shuffle` is.
2. **Batch sampler** — chunks them into lists of `batch_size`; `drop_last=True`
   discards the final short list.
3. **Fetcher** — calls `dataset[i]` for each index, in a worker process if
   `num_workers > 0`.
4. **`collate_fn`** — merges that list of samples into one batch.

So `for xb, yb in loader` yields whatever stage 4 returns, and there is no hidden
state beyond the sampler's random number generator (RNG).

## collate_fn

`default_collate` is recursive and structure-preserving: a list of same-shape
tensors becomes one tensor with a leading batch dimension, a list of `(x, y)`
tuples becomes a tuple of stacked tensors, a list of dicts becomes a dict of
stacked values, strings pass through as a list.

The load-bearing words are **same shape**. Variable-length samples raise
`RuntimeError: stack expects each tensor to be equal size`:

```python
import torch
from torch.nn.utils.rnn import pad_sequence

def pad_collate(batch):
    xs, ys = zip(*batch)
    lengths = torch.tensor([len(x) for x in xs])
    xs = pad_sequence(xs, batch_first=True, padding_value=0)
    return xs, torch.stack(ys), lengths
```

`collate_fn` is also the right home for anything genuinely *batch-level* — mixup,
attention masks, whole-batch tokenisation. `__getitem__` can't see the other
samples, and the [training loop](training-loop.md) would do it on the main
process instead of in the workers.

## Splitting: what random_split assumes

```python
from torch.utils.data import random_split
train_ds, val_ds = random_split(ds, [0.8, 0.2])
```

This permutes `0..len-1` and slices — correct only when every index is an
independent observation. It is silently wrong when:

- **The data is a time series** — future rows land in train, past rows in
  validation. See [Time-Series Validation](../concepts/time-series-validation.md).
- **Windows overlap** — index `i` and `i+1` of a `WindowDataset(length=20)` share
  19 of 20 observations, so both sides of the split hold near-duplicates. Needs a
  purge and embargo at least as wide as the window; see
  [Purged Cross-Validation](../concepts/purged-cross-validation.md) for the splitting
  and [LSTM Shapes](lstm.md) for the window arithmetic itself.
- **Rows are grouped** — several rows per patient, user, session, or augmented
  copy. Every group belongs entirely on one side.

The fix is to split the **index space** with a splitter that understands the
dependence structure, then re-map with `Subset`:

```python
from torch.utils.data import Subset

train_idx, val_idx = my_splitter(metadata)   # chronological / grouped / purged
train_ds = Subset(ds, train_idx)             # Subset(ds, idx)[k] is ds[idx[k]]
val_ds   = Subset(ds, val_idx)
```

`Subset` copies no data and is where an arbitrary, domain-aware split meets
PyTorch's index-based protocol — the index lists can come from scikit-learn's
[splitters](../scikit-learn/splitting.md) or from your own code.

## Statistics: there is no fit boundary

```python
# WRONG — mean/std computed over validation rows too
X = (X - X.mean(0)) / X.std(0)
train_ds, val_ds = random_split(TensorDataset(X, y), [0.8, 0.2])
```

```python
# RIGHT — split first, learn the statistic from training indices, apply to both
mu, sd = X[train_idx].mean(0), X[train_idx].std(0)
train_ds = TensorDataset((X[train_idx] - mu) / sd, y[train_idx])
val_ds   = TensorDataset((X[val_idx]   - mu) / sd, y[val_idx])
```

The same applies to imputation medians, category and tokeniser vocabularies,
Principal Component Analysis (PCA) bases, target encodings and clipping
quantiles — anything *learned* from data.

!!! warning "Shuffling is safe; the split is where the danger is"
    Within a training set, batch order affects optimisation, not leakage —
    `shuffle=True` is almost always right, because stochastic gradient descent
    assumes batches are roughly i.i.d. samples of the training distribution.
    Leave it off for validation and test so predictions stay aligned with an
    index. If the *split* was wrong, no shuffle setting saves you.

## Samplers

```python
from torch.utils.data import WeightedRandomSampler
sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)
loader = DataLoader(ds, batch_size=32, sampler=sampler)   # no shuffle= alongside
```

- `sampler=` and `shuffle=` are mutually exclusive — passing both raises.
- A weighted sampler is the usual answer to class imbalance, and belongs **only**
  on the training loader: resampling validation changes the distribution you are
  measuring against.
- `DistributedSampler` shards indices across ranks; call `set_epoch(epoch)` every
  epoch or every rank reshuffles identically.

## Workers and throughput

`num_workers=N` starts `N` processes, each owning a copy of the dataset and
filling a queue of collated batches.

- **The dataset is pickled or copy-on-write shared.** Large Python containers in
  `self` get duplicated per worker; tensors and NumPy arrays usually don't.
- **Mutating `self` in `__getitem__` doesn't propagate back** — a cache filled in
  a worker is invisible everywhere else.
- **Each worker gets a distinct seed**, but libraries seeded at import time
  (NumPy's global RNG under `fork`) can end up identical, so every worker applies
  the same "random" augmentation. Seed per worker with `worker_init_fn`, or draw
  from `torch` inside the dataset. See
  [Reproducibility and Seeding](../concepts/reproducibility.md).
- `persistent_workers=True` avoids tearing the processes down each epoch;
  `pin_memory=True` stages batches in page-locked memory so `.to(device,
  non_blocking=True)` overlaps transfer with compute; `prefetch_factor` (default
  2) is batches buffered *per worker*.

More workers is not monotonically better — past GPU saturation they only cost RAM
and startup time.

## Reproducible iteration order

```python
g = torch.Generator().manual_seed(0)
loader = DataLoader(ds, batch_size=32, shuffle=True, generator=g)
```

The loader's shuffling RNG is separate from the global seed; an explicit
`generator=` is what makes two runs iterate in the same order.

## Failure checklist

| Symptom | Usual cause |
|---|---|
| `stack expects each tensor to be equal size` | variable-length samples — write a `collate_fn` |
| Validation score implausibly high | `random_split` over a time series, overlapping windows, or grouped rows |
| Score collapses under a chronological split | that gap *is* the size of the leak |
| Every worker produces identical augmentations | NumPy global RNG copied at fork |
| Loader RAM grows with `num_workers` | large Python objects in `self` |
| `BatchNorm` error on the final batch | a batch of size 1 — `drop_last=True` on train only |
| GPU idle between batches | too few workers, no `pin_memory`, expensive `__getitem__` |
| Same seed, different iteration order | no explicit `generator=` |

## Related

- [The Training Loop](training-loop.md) — what consumes the batches this yields
- [Tensors](tensors.md) — dtype and device rules a batch must satisfy
- [Data Leakage](../concepts/data-leakage.md) — the taxonomy this page's split
  rules defend against
- [Train/Test Splitting](../scikit-learn/splitting.md) — splitters that produce
  the index lists `Subset` consumes
- [scikit-learn Pipelines](../scikit-learn/pipelines.md) — the fit boundary made
  structural, which PyTorch leaves to you
