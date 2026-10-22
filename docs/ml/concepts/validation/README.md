# Machine Learning / Concepts / Validation

Keeping a score honest: what the train/validation/test split is for, the ways information leaks across it, and the splitting protocols that survive time-ordered data.

:material-text-box-outline: **[Model Validation](model-validation.md){ .lvl-basic }**
:   Why training error lies, the train/validation/test roles, hold-out vs k-fold, stratified and group-aware splits, and nested cross-validation

---

:material-text-box-outline: **[Data Leakage](data-leakage.md){ .lvl-intermediate }**
:   The six kinds — preprocessing, look-ahead, target, feature-selection, group, selection bias — plus the question that catches most of them

---

:material-text-box-outline: **[Purged Cross-Validation](purged-cross-validation.md){ .lvl-advanced }**
:   De Prado's combinatorial splits — many backtest paths instead of one, why an embargo becomes necessary, and how to size both

:material-text-box-outline: **[Tuning a Trading Strategy](strategy-tuning.md){ .lvl-advanced }**
:   Three rules for hyperparameter search on a strategy — score once out-of-sample, pin position scale first, and log the trial count

:material-text-box-outline: **[Time-Series Validation](time-series-validation.md){ .lvl-advanced }**
:   Honest model selection on financial data — how a shuffled KFold lies, expanding-window splits as the floor, and the overlapping-label leak
