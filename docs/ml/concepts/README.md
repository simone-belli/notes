# Machine Learning / Concepts

:material-text-box-outline: **[Data Leakage](data-leakage.md){ .lvl-intermediate }**
:   The six kinds — preprocessing, look-ahead, target, feature-selection, group, selection bias — plus the question that catches most of them

:material-text-box-outline: **[Gradient Descent](gradient-descent.md){ .lvl-intermediate }**
:   SGD and Adam — step size and conditioning, momentum as a filter, the AdaGrad→RMSProp→Adam lineage, and bias correction

:material-text-box-outline: **[Learning Rate Range Test](lr-range-test.md){ .lvl-intermediate }**
:   Smith's one-run measurement of the usable band of rates — the linear ramp, reading the two bounds off the curve, and the cyclical schedule they feed

:material-text-box-outline: **[Long Short-Term Memory](lstm.md){ .lvl-intermediate }**
:   Why a plain RNN's gradient dies, the constant error carousel that replaces it, and the three gates and two states

:material-text-box-outline: **[Model Validation](model-validation.md){ .lvl-basic }**
:   Why training error lies, the train/validation/test roles, hold-out vs k-fold, stratified and group-aware splits, and nested cross-validation

:material-text-box-outline: **[Normalisation Layers](normalisation.md){ .lvl-intermediate }**
:   Standardise then re-scale — which axes each variant reduces over, why it buys a larger learning rate, BatchNorm's train/eval buffers, and pre-norm vs post-norm

:material-text-box-outline: **[Reproducibility and Seeding](reproducibility.md){ .lvl-intermediate }**
:   Why every random number generator needs its own seed — global seeding vs explicit generators, `random_state`, and a central seeding module

:material-text-box-outline: **[Purged Cross-Validation](purged-cross-validation.md){ .lvl-advanced }**
:   De Prado's combinatorial splits — many backtest paths instead of one, why an embargo becomes necessary, and how to size both

:material-text-box-outline: **[Tuning a Trading Strategy](strategy-tuning.md){ .lvl-advanced }**
:   Three rules for hyperparameter search on a strategy — score once out-of-sample, pin position scale first, and log the trial count

:material-text-box-outline: **[Time-Series Validation](time-series-validation.md){ .lvl-advanced }**
:   Honest model selection on financial data — how a shuffled KFold lies, expanding-window splits as the floor, and the overlapping-label leak

:material-text-box-outline: **[Training Diagnostics](training-diagnostics.md){ .lvl-intermediate }**
:   Karpathy's recipe and the per-layer, per-step quantities a loss curve hides — gradient norms, update:param ratio, activation statistics, and telling a high learning rate from no signal
