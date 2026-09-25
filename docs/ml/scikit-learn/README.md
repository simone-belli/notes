# Machine Learning / scikit-learn

:material-text-box-outline: **[ColumnTransformer](column-transformer.md){ .lvl-intermediate }**
:   Different preprocessing per column group — scale the numerics, encode the categoricals — concatenated into one leak-safe preprocessing step

:material-text-box-outline: **[Running Cross-Validation](cross-validation.md){ .lvl-intermediate }**
:   `cross_val_score` vs `cross_validate` vs `cross_val_predict` — multi-metric scoring, custom scorers, the `neg_` sign convention, and per-fold diagnostics

:material-text-box-outline: **[Custom Loss Functions](custom-loss.md){ .lvl-advanced }**
:   Why `scoring=` never changes fitting, the built-in `loss=` menu, `sample_weight` as the cheap option, and two custom-objective routes

:material-text-box-outline: **[Custom Transformers](custom-transformers.md){ .lvl-advanced }**
:   Feature-engineering steps as `fit`/`transform` classes that live inside the Pipeline and stay leak-free, plus `FunctionTransformer` for the stateless case

:material-text-box-outline: **[The Estimator API](estimators.md){ .lvl-basic }**
:   The one interface every model shares — construct, `fit`, then `predict` or `transform`; hyperparameters vs `trailing_underscore_` learned attributes

:material-text-box-outline: **[Fold-Safe Transformers](fold-safe-transformers.md){ .lvl-advanced }**
:   Rolling and recursive features across a fold boundary — causal windows, the burn-in buffer, burn-in vs embargo, and why non-contiguous splits fail silently

:material-text-box-outline: **[Hyperparameter Search](hyperparameter-search.md){ .lvl-intermediate }**
:   Tuning with `GridSearchCV` and `RandomizedSearchCV` — the `step__param` grid, `refit` semantics, `cv_results_`, and nesting for an honest score

:material-text-box-outline: **[Imputation](imputation.md){ .lvl-intermediate }**
:   Filling `NaN` values that would crash downstream estimators — `SimpleImputer` strategies, KNN and iterative imputers, leak-safe inside a Pipeline

:material-text-box-outline: **[scikit-learn Pipelines](pipelines.md){ .lvl-intermediate }**
:   Chaining preprocessing and an estimator so `fit` touches only the training fold — how it makes `scale-then-split` data leakage structurally impossible

:material-text-box-outline: **[Train/Test Splitting](splitting.md){ .lvl-basic }**
:   Holding out data with `train_test_split` and cross-validation splitters — stratification, and why you never shuffle a time series
