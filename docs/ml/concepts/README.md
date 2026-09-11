# Machine Learning / Concepts

:material-text-box-outline: **[Data Leakage](data-leakage.md){ .lvl-intermediate }**
:   The taxonomy — preprocessing, look-ahead, target, feature-selection, group, and selection bias — plus the one question that catches most of it and the signals that betray the rest

:material-text-box-outline: **[Gradient Descent](gradient-descent.md){ .lvl-intermediate }**
:   The textbook account of SGD and Adam — the descent bound that sets the usable step size, why conditioning makes plain descent slow, why constant-rate SGD never converges, momentum as a filter, the AdaGrad→RMSProp→Adam lineage, bias correction, and why $L^2$ is not weight decay

:material-text-box-outline: **[Model Validation](model-validation.md){ .lvl-basic }**
:   Why training error lies, the train/validation/test roles, hold-out vs k-fold and its i.i.d. premise, stratified and group-aware splits, and nested CV for honest post-tuning scores

:material-text-box-outline: **[Reproducibility and Seeding](reproducibility.md){ .lvl-intermediate }**
:   Why every RNG in the stack needs its own seed, global seeding vs explicit generators, `random_state` semantics, Optuna's sampler seed vs the objective's own, and a central seeding module

:material-text-box-outline: **[Purged Cross-Validation](purged-cross-validation.md){ .lvl-advanced }**
:   De Prado's combinatorial splits — many backtest paths instead of one, why giving up train-before-test is what makes an embargo necessary, and sizing purge by label horizon against embargo by feature memory

:material-text-box-outline: **[Tuning a Trading Strategy](strategy-tuning.md){ .lvl-advanced }**
:   Three rules for hyperparameter search on a strategy — score once on the pooled out-of-sample series, pin position scale in the position map before selecting on mean return, and log the trial count before you start

:material-text-box-outline: **[Time-Series Validation](time-series-validation.md){ .lvl-advanced }**
:   Honest model selection on financial data — how a shuffled KFold lies, expanding-window CV as the floor, and the overlapping-label leak that purging and embargo exist to stop
