# Extending results

A [`statsmodels`](statsmodels.md) state space results object is two separable things:
the parameters $\hat\theta$, found by maximum likelihood and expensive, and a Kalman
filter run over one dataset at those parameters, which is cheap. `append`, `extend` and
`apply` all keep $\hat\theta$ and redo the filter on different data:

```python
import statsmodels.api as sm

res = sm.tsa.SARIMAX(y[:split], order=(1, 0, 1)).fit(disp=False)

res.append(endog, exog=None, refit=False, fit_kwargs=None, copy_initialization=False)
res.extend(endog, exog=None, fit_kwargs=None)
res.apply(endog,  exog=None, refit=False, fit_kwargs=None, copy_initialization=False)
```

They exist on the state space classes — `SARIMAX`, `ARIMA`, `UnobservedComponents`,
`VARMAX`, `DynamicFactor`, statespace `ExponentialSmoothing` — plus `AutoReg`.

| | new data vs. old | result covers | cost |
|---|---|---|---|
| `append` | must follow immediately | old + new | O(total) |
| `extend` | must follow immediately | new only | O(new) |
| `apply` | unrelated | new only | O(new) |

## append

New observations must continue the existing index — the next period, or a `ValueError`.
The returned object is filtered over *original + new* from the original initialization,
so it is equivalent to building the model on the concatenated series and calling
`mod.filter(res.params)`. `nobs`, `llf`, `aic` and `fittedvalues` cover the whole sample.

`refit=True` re-estimates on the extended data, forwarding `fit_kwargs` to `.fit()`.

## extend

Same contiguity requirement, but the result covers only the **new** observations,
initialized from the state distribution at the end of the previous results. Forecasts
match `append`'s; the differences are practical:

- Cost is O(new), not O(total) — it never re-filters the history. Over a long
  walk-forward loop that is the difference between seconds and minutes.
- `llf`, `aic`, `nobs` describe the new chunk alone, so they are not comparable with the
  original fit. Don't model-select on them.
- There is no `refit` — `extend` is strictly a continuation.

## apply

No relationship to the old sample is assumed: take these parameters, run the model on
*this* data instead. Useful for the same model on another entity, a rolling window of
fixed-length slices, or a revised vintage of the same dates.

The new run uses the model's **default** initialization unless `copy_initialization=True`.
With a diffuse or estimated initial state that changes the first several filtered values.

!!! tip "The point is that parameters stay frozen"
    `res.params` is unchanged unless you pass `refit=True`. Refitting on data that
    includes the observation you are about to predict is a lookahead bug; these methods
    are how you avoid it without paying for re-estimation at every step.

## Walk-forward

```python
order = (1, 0, 1)
res = sm.tsa.SARIMAX(y[:split], order=order).fit(disp=False)

fcasts = []
for t in range(split, len(y)):
    fcasts.append(res.forecast(1).iloc[0])        # predict before seeing y[t]
    if (t - split) % 250 == 0:                    # periodic re-estimation
        res = sm.tsa.SARIMAX(y.iloc[: t + 1], order=order).fit(disp=False)
    else:
        res = res.extend(y.iloc[t : t + 1])       # reveal it, parameters frozen
```

Forecast first, reveal second — that ordering is what makes the backtest causal.

!!! warning "`extend` discards the history"
    The object `extend` returns carries a model holding **only the block you passed**.
    Chaining `res.append(..., refit=True)` onto it re-estimates on a handful of points.
    Rebuild from the full series for the refit leg, as above.

## Gotchas

- **`exog` is mandatory if the model has one**, with matching columns and length.
- **Index discipline** — pass pandas objects with a `DatetimeIndex`/`PeriodIndex` carrying
  a frequency, or a continuing `RangeIndex`. A frequency mismatch is the usual cause of
  the `ValueError` from `append`/`extend`.
- **The result is a full results object** — `.forecast(h)`, `.get_prediction()`,
  `.summary()` and `.simulate()` all work on it.
- **[`MarkovRegression`](markov-regression.md) has none of these.** Its equivalent is
  `mod_new.filter(res_old.params)` on a model built over the longer series.

## Related

- [statsmodels](statsmodels.md) — the Model→Results split these methods exploit
- [MarkovRegression](markov-regression.md) — frozen-parameter filtering without `append`
