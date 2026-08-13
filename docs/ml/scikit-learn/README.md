# Machine Learning / scikit-learn

:material-text-box-outline: **[ColumnTransformer](column-transformer.md)**
:   Different preprocessing per column group — scale the numerics, encode the categoricals — concatenated into one leak-safe preprocessing step

:material-text-box-outline: **[The Estimator API](estimators.md)**
:   The one interface every model shares — construct with hyperparameters, `fit` to learn, then `predict` or `transform`; hyperparameters vs `trailing_underscore_` learned attributes

:material-text-box-outline: **[Imputation](imputation.md)**
:   Filling missing values (`NaN`) that would otherwise crash downstream estimators — SimpleImputer strategies, KNN/iterative imputers, and doing it leak-safe inside a Pipeline

:material-text-box-outline: **[scikit-learn Pipelines](pipelines.md)**
:   Chaining preprocessing and an estimator so `fit` touches only the training fold — how it makes `scale-then-split` data leakage structurally impossible
