# Machine Learning / scikit-learn

:material-text-box-outline: **[ColumnTransformer](column-transformer.md){ .lvl-intermediate }**
:   Different preprocessing per column group — scale the numerics, encode the categoricals — concatenated into one leak-safe preprocessing step

:material-text-box-outline: **[Running Cross-Validation](cross-validation.md){ .lvl-intermediate }**
:   `cross_val_score` vs `cross_validate` vs `cross_val_predict` — what the loop returns, multi-metric scoring, writing custom scorers, the `neg_` sign convention, and per-fold diagnostics

:material-text-box-outline: **[Custom Transformers](custom-transformers.md){ .lvl-advanced }**
:   Writing your own feature-engineering steps (rolling stats, regime tags) as `fit`/`transform` classes so they live inside the Pipeline and stay leak-free — plus the burn-in buffer that keeps a recursive feature like an EWMA continuous across a fold boundary

:material-text-box-outline: **[The Estimator API](estimators.md){ .lvl-basic }**
:   The one interface every model shares — construct with hyperparameters, `fit` to learn, then `predict` or `transform`; hyperparameters vs `trailing_underscore_` learned attributes

:material-text-box-outline: **[Hyperparameter Search](hyperparameter-search.md){ .lvl-intermediate }**
:   Tuning with `GridSearchCV` and `RandomizedSearchCV` — the `step__param` grid, `refit` semantics, reading `cv_results_`, why the exhaustive product doesn't scale, and nesting for an honest score

:material-text-box-outline: **[Imputation](imputation.md){ .lvl-intermediate }**
:   Filling missing values (`NaN`) that would otherwise crash downstream estimators — SimpleImputer strategies, KNN/iterative imputers, and doing it leak-safe inside a Pipeline

:material-text-box-outline: **[scikit-learn Pipelines](pipelines.md){ .lvl-intermediate }**
:   Chaining preprocessing and an estimator so `fit` touches only the training fold — how it makes `scale-then-split` data leakage structurally impossible

:material-text-box-outline: **[Train/Test Splitting](splitting.md){ .lvl-basic }**
:   Holding out data with `train_test_split` and cross-validation splitters — stratification, and why you never shuffle a time series
