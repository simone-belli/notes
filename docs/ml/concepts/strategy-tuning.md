# Tuning a Trading Strategy

Cross-validation (CV) controls leakage across the train/test boundary. It does
nothing about leakage through **you** — the selection channel, where information
flows from the validation set into the model via the configurations you keep.
Three rules, all saying the same thing: the number you optimise and the number
you report are different numbers, and both are easy to compute wrongly.

## Rule 1 — score once on the pooled out-of-sample series

Write the objective directly; don't route it through
[`cross_val_score`](../scikit-learn/cross-validation.md). Loop the folds
yourself, keep the out-of-fold (OOF) predictions, concatenate them into one
out-of-sample (OOS) return series, and compute the Sharpe ratio **once** on that.

```python
oos = []
for tr, te in splitter.split(X):
    pipe.fit(X.iloc[tr], y.iloc[tr])
    pred = pipe.predict(X.iloc[te])
    oos.append(pd.Series(np.sign(pred) * fwd_ret.iloc[te], index=X.index[te]))

r = pd.concat(oos).sort_index()                 # one OOS return series
sharpe = np.sqrt(252) * r.mean() / r.std(ddof=1)
```

`cross_val_score` hands back one score per fold, and the natural next move —
`scores.mean()` — is the wrong estimand:

- **Equal weight per fold.** A 150-day fold and a 400-day fold count the same.
- **Folds aren't exchangeable.** Under `TimeSeriesSplit` the training set grows
  monotonically, so fold 1's model is a worse-trained object than fold 5's;
  averaging their scores averages over an artefact of the protocol.
- **Mean of ratios ≠ ratio of means.** Sharpe is a nonlinear functional of the
  return distribution. A near-flat fold with tiny realised volatility produces a
  huge ratio that dominates the average.

!!! warning "No tradeable equity curve produces a mean-of-fold-Sharpes"
    The pooled OOS series is something you can hold: what the strategy would have
    returned, day by day, refitting as it went. No account statement anywhere
    shows "the average of five fold Sharpes". A statistic with no realisable path
    behind it is not a performance estimate.

**Why not `cross_val_predict`?** It requires the folds to *partition* the sample.
Purged folds don't: purging drops training rows whose label horizon crosses the
boundary, embargo drops test rows after it, and `TimeSeriesSplit` never tests on
the first block. Rows fall in no test fold, so it raises or silently misaligns —
collect manually and control the index yourself.

## Rule 2 — select on one moment, report the ratio

- **Select on** rank information coefficient (rank IC — the Spearman correlation
  between prediction and realised forward return) or mean OOS return. Each is a
  *single* estimated moment.
- **Report** the pooled-OOS Sharpe, always with its standard error.

A Sharpe ratio is a ratio of two estimated moments, and an optimiser handed a
ratio wins by shrinking the **denominator** — it finds the configuration that
happened to realise low volatility over your sample, a property of the noise. The
variance estimate is itself noisy, so the ratio has fat tails. Rank IC has
neither problem: monotone in skill, bounded, and it doesn't reward a lucky quiet
patch. Decoupling costs nothing — both come from the same pooled series; you just
don't let the search steer on the fragile one.

**Lo's standard error** for the annualised Sharpe under i.i.d. returns
(Lo, 2002), with `q` = periods per year and `n` = number of observations:

```
SE(SR_ann) ≈ sqrt(q / n)
```

Three years of daily data: `sqrt(252/756) ≈ 0.58`. So a reported 1.0 is really
"1.0 ± 0.6" — *before* correcting for having searched. Quote the interval, not
the point. (The exact form carries a `(1 + SR²/2)` factor, a small correction at
believable Sharpe levels; autocorrelated returns inflate it further.)

## Rule 3 — pre-register and log the trial count K

Write **K** down before the study runs, with the search space. Not after, and not
"however many trials it took to get something good". The reported best is a
**maximum order statistic**, and maxima of noise are large. For a model with
*zero* skill:

| Quantity | Value |
|---|---|
| Per-fold SE (3yr daily, 5 folds → ~151 days) | `sqrt(252/151)` ≈ **1.3** |
| 5-fold mean SE (folds treated as independent) | `1.3/√5` ≈ **0.6** |
| `E[max of K standard normals]`, K = 20 | ≈ **1.9** (≈ 2.5 at K = 100) |
| Selection noise in the winner | ≈ **+1.1 annualised Sharpe** |

!!! warning "1.1 out of a 20-trial study is what zero skill looks like"
    That is the *default expectation*, not a worst case.

- **Correlated trials shrink it, but don't remove it.** A Tree-structured Parzen
  Estimator concentrates its draws, so the effective K is below the nominal K —
  though a better optimiser also searches the noise more efficiently.
- **This is not a formal correction.** The Deflated Sharpe Ratio (DSR) and the
  Probability of Backtest Overfitting (PBO) are the real machinery, and both take
  K as an input. Logging it now is what makes deflation possible later; you
  cannot reconstruct it afterwards.

## Related

- [Time-Series Validation](time-series-validation.md) — purging, embargo, and why the folds don't partition
- [Model Validation](model-validation.md) — selection bias on the maximum, and nested CV
- [Optuna](../optuna.md) — where the objective function and trial count live
- [Hyperparameter Search](../scikit-learn/hyperparameter-search.md) — the searchers this replaces the scoring of
