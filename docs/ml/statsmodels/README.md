# Machine Learning / statsmodels

Classical statistical and econometric models — estimation, inference, and the results
objects they return.

:material-text-box-outline: **[Frozen parameters](frozen-parameters.md){ .lvl-intermediate }**
:   Re-running a model at parameters you already have — `mod.filter` / `mod.smooth`, the `append` / `extend` / `apply` trio on a results object, and the causal walk-forward loop they enable

:material-text-box-outline: **[MarkovAutoregression](markov-autoregression.md){ .lvl-advanced }**
:   Hamilton's switching autoregression — the mean-adjusted form and its $K^{p+1}$ cost, mean- vs intercept-switching, the presample offset, and why a point forecast is a mixture

:material-text-box-outline: **[MarkovRegression](markov-regression.md){ .lvl-advanced }**
:   Markov-switching regression in `statsmodels` — the constructor defaults that change the model, random restarts, reading the results object, and filtering out-of-sample with frozen parameters

:material-text-box-outline: **[statsmodels](statsmodels.md){ .lvl-basic }**
:   Inference rather than prediction — the Model→Results split, array vs formula API, the results vocabulary, `cov_type`, and what the library actually contains
