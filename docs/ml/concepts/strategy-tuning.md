# Tuning a Trading Strategy

Cross-validation (CV) controls leakage across the train/test boundary. It does
nothing about leakage through **you** — the selection channel, where information
flows from the validation set into the model via the configurations you keep.
Three rules, all saying the same thing: the number you optimise and the number
you report are different numbers, and both are easy to compute wrongly.

## Rule 1 — score once on the pooled out-of-sample series

The strongest of the three. Write the objective directly; don't route it through
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
  return distribution, so averaging fold ratios doesn't estimate the pooled one.

!!! warning "This is where the ratio genuinely misbehaves"
    Not in the numerator-vs-denominator choice of Rule 2 — *here*. On short
    per-fold windows `σ̂` is unstable, and across folds with heterogeneous
    volatility regimes a quiet fold's Sharpe dominates the average. Pooling
    first estimates one denominator from all the data and the problem disappears.

!!! note "No tradeable equity curve produces a mean-of-fold-Sharpes"
    The pooled OOS series is something you can hold: what the strategy would have
    returned, day by day, refitting as it went. No account statement anywhere
    shows "the average of five fold Sharpes". A statistic with no realisable path
    behind it is not a performance estimate.

**Why not `cross_val_predict`?** It requires the folds to *partition* the sample.
Purged folds don't: purging drops training rows whose label horizon crosses the
boundary, embargo drops test rows after it, and `TimeSeriesSplit` never tests on
the first block. Rows fall in no test fold, so it raises or silently misaligns —
collect manually and control the index yourself.

## Rule 2 — pin the scale in the position map, then select on the mean

Three steps, and the order is the point:

1. **Pin position scale** in the position map — before any objective is computed.
2. **Select on** mean OOS return (or rank information coefficient).
3. **Report** pooled-OOS Sharpe with its standard error.

At fixed variance, `argmax(mean) = argmax(Sharpe)` **exactly**. There is no
economic disagreement between the two objectives — so the only question worth
asking is whether a hyperparameter can move the position scale. It can:

> With positions ∝ raw prediction, shrinking ridge `alpha` inflates the
> coefficients → inflates the predictions → inflates the positions → inflates
> mean return, with **Sharpe unchanged**. Selecting on mean return would rank
> configurations by a leverage artefact.

The fix belongs in the position map, not the objective. **Volatility-target** the
positions to a constant ex-ante annualised volatility, using a forecast fit on
the **training** fold:

```python
pipe.fit(X.iloc[tr], y.iloc[tr])
scale = pipe.predict(X.iloc[tr]).std()          # prediction scale — from TRAIN
sigma = forecast_ann_vol(ret.iloc[tr])          # vol forecast  — from TRAIN

pred = pipe.predict(X.iloc[te])
pos  = (pred / scale) * (TARGET_VOL / sigma)    # constant ex-ante vol
oos.append(pd.Series(pos * fwd_ret.iloc[te], index=X.index[te]))
```

The denominator is now estimated **once, ex ante**, instead of floating free per
configuration on test data. With scale pinned, mean return and Sharpe agree, and
you select on the simpler one.

!!! warning "Don't justify this with 'ratio estimators are noisy'"
    That is false here. `Var(SR̂) ≈ (1 + SR²/2)/n`, and at an annualised Sharpe
    of 1 — daily `SR ≈ 1/√252 ≈ 0.063` — the volatility term `SR²/2 ≈ 0.002` is
    negligible against the mean term of 1. Essentially all the sampling variance
    of a Sharpe estimate comes from `µ̂`. The denominator is a *scale-invariance*
    problem, not a noise problem.

**The genuine case for rank IC** — the Spearman correlation between prediction
and realised forward return — is **tail robustness**. Both `µ̂` and `σ̂` have poor
breakdown: one 6-sigma FX day can dominate either. Rank IC has bounded
per-observation influence, so any single day moves it `O(1/n)`.

**Lo's standard error** for the annualised Sharpe under i.i.d. returns
(Lo, 2002), with `q` = periods per year and `n` = number of observations:

```
SE(SR_ann) ≈ sqrt(q / n)
```

Three years of daily data: `sqrt(252/756) ≈ 0.58`. So a reported 1.0 is really
"1.0 ± 0.6" — *before* correcting for having searched. Quote the interval, not
the point. (Autocorrelated returns inflate it further.)

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
- **This is not a Sharpe-specific problem.** It applies to any noisy objective
  equally, including the mean return or rank IC of Rule 2. Switching estimator
  buys you nothing here, so pre-registering K is **unconditional**.
- **It is not a formal correction either.** The Deflated Sharpe Ratio (DSR) and
  the Probability of Backtest Overfitting (PBO) are the real machinery, and both
  take K as an input. Logging it now is what makes deflation possible later; you
  cannot reconstruct it afterwards.

## Related

- [Time-Series Validation](time-series-validation.md) — purging, embargo, and why the folds don't partition
- [Model Validation](model-validation.md) — selection bias on the maximum, and nested CV
- [Optuna](../optuna.md) — where the objective function and trial count live
- [Hyperparameter Search](../scikit-learn/hyperparameter-search.md) — the searchers this replaces the scoring of
