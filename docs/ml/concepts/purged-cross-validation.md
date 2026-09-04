# Purged Cross-Validation

[Expanding-window CV](time-series-validation.md) gives you one backtest path:
five chronological folds are one history cut five times, so fold variance badly
understates uncertainty. **Combinatorial Purged Cross-Validation** (CPCV, de
Prado) trades the strict train-before-test ordering for many paths — partition
the sample into `N` groups, put every combination of `k` of them in test, and
reassemble the out-of-sample predictions into a *distribution* of Sharpe ratios
rather than a point estimate.

```
N = 6, k = 2, test groups {1,3}

groups   0        1        2        3        4        5
       [TRAIN ][ TEST ][TRAIN ][ TEST ][TRAIN ][TRAIN ]
```

- **Splits** — `C(N,k)`; with `N=6, k=2` that's 15.
- **Paths** — `k·C(N,k)/N`, here 5. Each group is tested in several splits, and
  one prediction per group per path reassembles a full backtest.

Everything that follows comes from one structural change: **training rows now
exist on both sides of the test rows**, and the test set is no longer contiguous.

## Purge and embargo

Ordering was doing protective work, and dropping it opens two leakage channels
that need explicit closing.

| | targets | direction | sized by |
|---|---|---|---|
| **Purge** | training rows whose **label span** overlaps a test label span | both sides | label horizon |
| **Embargo** | training rows **immediately after** a test block | after only | feature memory |

- **Embargo cuts *training* rows, not test rows.** Every test row is kept — CPCV
  needs them all to reconstruct paths.
- **Embargo applies only after the test block.** Training rows before it are
  already covered by purging, since their labels resolve before the test labels
  do. What survives purging is a *feature* whose window reaches back into the
  test period.

!!! note "Embargo exists because of this splitter"
    Under forward chaining there are no training rows after the test block, so
    the embargo is vacuous and only purging matters — which is why
    `TimeSeriesSplit(gap=g)`, documented as excluding samples from the *end of
    each train set*, is purging rather than embargo. Combinatorial splits are
    what make the embargo a live concern.

## Sizing the embargo

A training row `d` rows after a test block carries a feature whose memory still
reaches into that block. Perturbing only test-period values and measuring how far
the contamination survives gives, for an exponentially weighted moving average
(EWMA) with `halflife=10`:

| `d` rows after test | 6 | 10 | 20 | 50 | 100 |
|---|---|---|---|---|---|
| residual contamination | 0.62 | 0.47 | 0.23 | 0.03 | 0.001 |

It tracks `2^(-d/halflife)` — the same constant that sizes a
[burn-in buffer](../scikit-learn/custom-transformers.md#carrying-a-burn-in-buffer).

!!! tip "One quantity, two sides"
    Burn-in and embargo are both the transform's memory. Burn-in is how many
    prior rows you **feed** the transform; embargo is how many later training
    rows you **drop**. Lengthen a half-life and you pay on both sides at once.

De Prado's suggested `h ≈ 1%` of the sample is far too small for a real feature:
on 600 rows that's 6 rows, leaving **66%** of the test-period signal in the first
surviving training row. Size it per feature instead — 10 half-lives (≈ 3.5
`span`) for exponential memory, the window length for a `rolling`.

## The cost is training data

Embargo is charged against the training set, and combinatorial splits cut
several boundaries per split rather than one. Measured over 600 rows, `N=6, k=2`:

| embargo | training set size |
|---|---|
| 0 | 390–400 |
| 100 (10 half-lives) | **190–395** |

The worst split loses over half its training rows. Check the *minimum* across
splits, not the mean — and treat it as a real argument for short-memory
features, not just a modelling preference.

## Consequences for transformers

A transformer receives `X` as a **concatenation of disjoint time segments**, so
anything order-sensitive breaks in two independent ways — a buffer keyed to the
training block goes empty, and a recursion runs straight across the time gap
between two test runs. Both fail silently, and both are correct for exactly the
splits that resemble `TimeSeriesSplit`. See
[Custom Transformers](../scikit-learn/custom-transformers.md#non-contiguous-folds)
for the failure table and the fix.

The underlying correction is one line of principle:

!!! warning "Burn-in belongs to the series, not the partition"
    The correct feature value at `t` depends on the raw series up to `t`. Which
    side of a train/test split those prior rows landed on is irrelevant — under
    CPCV the rows before a test run may be training, purged, embargoed, or other
    test rows, and all four are legitimate causal inputs.

## Related

- [Time-Series Validation](time-series-validation.md) — expanding-window CV, the protocol this one generalises
- [Data Leakage](data-leakage.md) — the taxonomy purging and embargo close two entries in
- [Custom Transformers](../scikit-learn/custom-transformers.md) — burn-in buffers and the non-contiguous case
- [Tuning a Trading Strategy](strategy-tuning.md) — the selection channel no splitter closes
- [Train/Test Splitting](../scikit-learn/splitting.md) — the splitter catalogue
