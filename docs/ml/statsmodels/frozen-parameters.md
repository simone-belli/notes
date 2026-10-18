# Frozen parameters

`fit()` does two things: **search** for the parameters that maximise the likelihood, and
**run the recursion** at the parameters it found. [`statsmodels`](statsmodels.md) exposes
the second half on its own, so you can re-run a model at parameters you already have —
on the same data, on more of it, or on an entirely different series.

```python
import statsmodels.api as sm

res = mod.fit()              # optimise, then filter at the argmax
res = mod.filter(params)     # filter at params you supply — no optimisation
```

That matters because re-estimating on a window containing the point you are about to
predict is a lookahead bug, and re-estimating at every step of a backtest is slow.

## filter and smooth

`filter` and `smooth` are methods on the **model**: they need a specification, data and a
parameter vector, and they return a full results object.

- **State space models** — `MLEModel` and its descendants (`SARIMAX`, `ARIMA`,
  `UnobservedComponents`, `VARMAX`, `DynamicFactor`). The recursion is the **Kalman
  filter**: a forward pass giving the latent state distribution at each $t$ conditioned
  on $y_{1:t}$, plus the one-step prediction errors whose log densities sum to `llf`.
- **Markov switching models** — `MarkovRegression`, `MarkovAutoregression`. The recursion
  is the **Hamilton filter**, propagating $\Pr(S_t = i \mid y_{1:t})$ instead of a
  Gaussian state.

`mod.smooth(params)` adds the backward pass, conditioning on the **whole sample**:

```python
mod_all = sm.tsa.SARIMAX(y, order=(1, 0, 1))   # whole series, nothing estimated
res_oos = mod_all.filter(res_train.params)     # θ̂ fitted strictly before the split

res_oos.filtered_state                         # conditioned on y[:t] — real time
res_oos.llf, res_oos.resid, res_oos.forecast(10)
```

Filtered quantities are admissible in a forecast evaluation; smoothed ones are
retrospective and are not.

!!! warning "Three unrelated things called filter"
    `statsmodels.tsa.filters` (`hpfilter`, `bkfilter`, `convolution_filter`) is a
    namespace of **signal-extraction** filters for detrending — nothing to do with
    `mod.filter`. And `res.filter_results` is the raw state space object hanging off a
    results instance.

### Arguments

```python
mod.filter(params, transformed=True, cov_type=None,
           return_ssm=False, low_memory=False)
```

- `transformed=True` (default) — `params` are in the natural, constrained space, the same
  scale as `res.params`. Pass `False` only for a vector from the optimiser's space.
- `cov_type` — nothing was estimated, so there is no Hessian to hand. Take `llf`, `aic`,
  the states and the predictions; ignore the summary's inference block.
- `return_ssm=True` — the bare `FilterResults` rather than wrapped `MLEResults`, cheaper
  when you only want the filtered state.
- `low_memory=True` — keeps only what forecasting needs; disables smoothing and most
  diagnostics. Matters on long series.

`mod.loglike(params)` is a thin wrapper over the same recursion returning just the scalar
— useful for profiling a parameter or checking that a restart found a better optimum.

## append, extend, apply

The state space **results** classes wrap the same idea with the model construction done
for you — plus `AutoReg`, which also has `append` and `apply`:

```python
res.append(endog, exog=None, refit=False, fit_kwargs=None, copy_initialization=False)
res.extend(endog, exog=None, fit_kwargs=None)
res.apply(endog,  exog=None, refit=False, fit_kwargs=None, copy_initialization=False)
```

| | new data vs. old | result covers | cost |
|---|---|---|---|
| `append` | must follow immediately | old + new | O(total) |
| `extend` | must follow immediately | new only | O(new) |
| `apply` | unrelated | new only | O(new) |

### append

New observations must continue the existing index — the next period, or a `ValueError`.
The returned object is filtered over *original + new* from the original initialization,
so it is equivalent to building the model on the concatenated series and calling
`mod.filter(res.params)`. `nobs`, `llf`, `aic` and `fittedvalues` cover the whole sample.

`refit=True` re-estimates on the extended data, forwarding `fit_kwargs` to `.fit()`.

### extend

Same contiguity requirement, but the result covers only the **new** observations,
initialized from the state distribution at the end of the previous results. Forecasts
match `append`'s; the differences are practical:

- Cost is O(new), not O(total) — it never re-filters the history. Over a long
  walk-forward loop that is the difference between seconds and minutes.
- `llf`, `aic`, `nobs` describe the new chunk alone, so they are not comparable with the
  original fit. Don't model-select on them.
- There is no `refit` — `extend` is strictly a continuation.

### apply

No relationship to the old sample is assumed: take these parameters, run the model on
*this* data instead. Useful for the same model on another entity, a rolling window of
fixed-length slices, or a revised vintage of the same dates.

The new run uses the model's **default** initialization unless `copy_initialization=True`.
With a diffuse or estimated initial state that changes the first several filtered values.

!!! tip "`apply` is `filter` with the plumbing done"
    `res.apply(new_y)` clones the model onto new data and filters at the existing
    parameters. Write `mod.filter(params)` yourself when the class has no `apply`
    (`MarkovRegression`), when you want a different specification or initialization, or
    when you need `return_ssm` / `low_memory`.

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

- **`params` never change** unless `refit=True`. That is the whole point.
- **`exog` is mandatory if the model has one**, with matching columns and length.
- **Index discipline** — pass pandas objects with a `DatetimeIndex`/`PeriodIndex` carrying
  a frequency, or a continuing `RangeIndex`. A frequency mismatch is the usual cause of
  the `ValueError` from `append`/`extend`.
- **The result is a full results object** — `.forecast(h)`, `.get_prediction()`,
  `.summary()` and `.simulate()` all work on it.
- **[`MarkovRegression`](markov-regression.md) has no `append`/`extend`/`apply`**, only
  `filter` and `smooth` on the model.

## Related

- [statsmodels](statsmodels.md) — the Model→Results split all of this exploits
- [MarkovRegression](markov-regression.md) — the Hamilton filter in a walk-forward loop
