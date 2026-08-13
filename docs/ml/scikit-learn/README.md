# Machine Learning / scikit-learn

:material-text-box-outline: **[ColumnTransformer](column-transformer.md)**
:   Different preprocessing per column group — scale the numerics, encode the categoricals — concatenated into one leak-safe preprocessing step

:material-text-box-outline: **[Custom Transformers](custom-transformers.md)**
:   Writing your own feature-engineering steps (rolling stats, regime tags) as `fit`/`transform` classes so they live inside the Pipeline and stay leak-free

:material-text-box-outline: **[The Estimator API](estimators.md)**
:   The one interface every model shares — construct with hyperparameters, `fit` to learn, then `predict` or `transform`; hyperparameters vs `trailing_underscore_` learned attributes

:material-text-box-outline: **[Imputation](imputation.md)**
:   Filling missing values (`NaN`) that would otherwise crash downstream estimators — SimpleImputer strategies, KNN/iterative imputers, and doing it leak-safe inside a Pipeline

:material-text-box-outline: **[scikit-learn Pipelines](pipelines.md)**
:   Chaining preprocessing and an estimator so `fit` touches only the training fold — how it makes `scale-then-split` data leakage structurally impossible

:material-text-box-outline: **[Train/Test Splitting](splitting.md)**
:   Holding out data with `train_test_split` and cross-validation splitters — stratification, and why you never shuffle a time series
