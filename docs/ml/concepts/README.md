# Machine Learning / Concepts

:material-text-box-outline: **[Data Leakage](data-leakage.md)**
:   The taxonomy — preprocessing, look-ahead, target, feature-selection, group, and selection bias — plus the one question that catches most of it and the signals that betray the rest

:material-text-box-outline: **[Model Validation](model-validation.md)**
:   Why training error lies, the train/validation/test roles, hold-out vs k-fold and its i.i.d. premise, stratified and group-aware splits, and nested CV for honest post-tuning scores

:material-text-box-outline: **[Tuning a Trading Strategy](strategy-tuning.md)**
:   Three rules for hyperparameter search on a strategy — score once on the pooled out-of-sample series, select on rank IC but report Sharpe with its standard error, and log the trial count before you start

:material-text-box-outline: **[Time-Series Validation](time-series-validation.md)**
:   Honest model selection on financial data — how a shuffled KFold lies, expanding-window CV as the floor, and the overlapping-label leak that purging and embargo exist to stop
