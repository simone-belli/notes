---
quiz: core
---

# Data Leakage

Leakage is when a model sees, during training, information it will not have at
prediction time. The result is not a subtle bias: the validation score measures a
task easier than the real one, so the number is meaningless and the failure only
shows up in production. It is the most common reason a strong backtest does not
reproduce live.

The whole subject reduces to one question, asked of every value that reaches
`fit`:

!!! note "The one diagnostic question"
    *At the moment of prediction, would I actually have had this number?* If the
    answer is no — or "only because I computed it over the whole dataset" — it
    is leakage. Everything below is a category of ways to answer this wrong
    without noticing.

## The taxonomy

**Preprocessing leakage.** A statistic learned from rows outside the training
fold: a scaler's mean and standard deviation, an imputer's median, an encoder's
category list, a Principal Component Analysis (PCA) basis. The model never sees a
test *label*, which is why this one feels safe and is so common.

```python
# WRONG — the mean is computed over train and test together
X_scaled = standardise(X)
X_train, X_test = X_scaled[:split], X_scaled[split:]
```

The fix is structural, not disciplinary: fit every learned step inside the fold.
See [scikit-learn Pipelines](../scikit-learn/pipelines.md).

**Look-ahead (temporal) leakage.** A training row post-dates a test row. Shuffling
a time series does this wholesale — the model learns the test period's regime,
which is most of the predictive battle. See
[Time-Series Validation](time-series-validation.md).

**Target leakage.** A feature that is a downstream consequence of the label rather
than a cause of it, and therefore unavailable when you would actually predict.
`account_closed_date` predicting churn; `discharge_summary_text` predicting
diagnosis; a "days since last trade" field that is only populated after the trade
resolves. These are the hardest to spot, because the pipeline is technically
correct — the data itself is the bug.

**Feature-selection leakage.** Ranking features by correlation with the target on
the full sample, keeping the top 50, then cross-validating the survivors. The
selection already consumed the test labels; every fold afterwards is scoring a
feature set chosen with knowledge of the answers. Selection is a *learned step* —
it belongs inside the fold like any other.

**Group leakage.** Near-duplicate rows split across folds, so the model
interpolates between two copies of one observation instead of generalising.
Multiple rows per patient, per user, per session — or, in a time series,
overlapping rolling windows, where rows at `t` and `t+1` share 19 of 20
observations. The fix is a group-aware splitter that keeps every row of a group on
one side of the boundary.

**Selection bias — leakage through you.** Try 400 configurations, report the best,
and you have a Sharpe ratio of 2 on pure noise. No splitter prevents this, because
the leak runs through the researcher rather than the code: each look at the test
set spends a little of its independence. Record the trial count, deflate the
reported metric for it, and keep one period sealed until the model is frozen.

!!! warning "The test set is consumable"
    A held-out set is a one-shot measurement, not a dashboard. By the tenth time
    you have adjusted a model after seeing its test score, that score is a
    training metric wearing a disguise.

## Detecting it

There is no linter for leakage. The practical signals:

- **A score that is too good.** Domain priors matter here — 65% accuracy on
  next-day market direction is not a breakthrough, it is a bug.
- **The protocol gap.** Run the suspect split and a strict one. Shuffled k-fold
  reporting 0.60 where a chronological split reports 0.51 is not two results; the
  difference *is* a measurement of your leak.
- **A feature that is too strong.** Drop the top feature by importance. If
  performance collapses to baseline, interrogate that column's provenance before
  celebrating it.
- **Live-versus-backtest divergence.** The expensive detector. Everything above
  exists to avoid reaching this one.

!!! tip "Structure beats vigilance"
    Every category here has a structural fix — a fit boundary, a chronological
    splitter, a group-aware splitter, a sealed final period. Reviewing code
    carefully for leakage works until the day you are tired; a `Pipeline` that
    makes the mistake unreachable works permanently.

## Related

- [Model Validation](model-validation.md) — the protocol leakage corrupts
- [Time-Series Validation](time-series-validation.md) — purging and embargo for correlated rows
- [scikit-learn Pipelines](../scikit-learn/pipelines.md) — the fit boundary, enforced
- [Custom Transformers](../scikit-learn/custom-transformers.md) — keeping engineered features inside the fold
- [DVC](../dvc.md) — the same "structure beats vigilance" move applied to file staleness: a pipeline stage declares its deps so re-run-or-skip is computed, not remembered
