---
tags:
  - design-patterns
---

# ColumnTransformer

Real feature matrices are heterogeneous: numeric columns (returns, volumes) want
scaling, categorical columns (a regime label, an exchange code) want encoding,
and a single transformer over everything is nonsense — scaling a category or
one-hot-encoding a float both destroy the data. `ColumnTransformer` applies a
**different transformer to each group of columns in parallel** and concatenates
the results side by side.

It is itself a transformer, so it drops into a [Pipeline](pipelines.md) as the
preprocessing step and inherits the leakage guarantee — now *per column group*.

```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

numeric = ["returns", "volume", "spread"]
categorical = ["regime"]

pre = ColumnTransformer([
    ("num", StandardScaler(),                       numeric),      # (name, transformer, columns)
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
])
```

- Each entry is a triple `(name, transformer, columns)`. `columns` may be a list
  of names, integer indices, a boolean mask, or a `make_column_selector(...)`.
- `fit` fits each sub-transformer on **its columns of the training data only** —
  numeric statistics learned from numeric columns, never contaminated by the
  categoricals or the test set.
- `transform` applies each fitted branch and **concatenates outputs horizontally**
  in listed order. Output is a NumPy (or sparse) array; recover names with
  `pre.get_feature_names_out()` (prefixed `num__returns`, `cat__regime_bull`, …).

!!! note "Horizontal split vs vertical chain"
    A Pipeline chains steps *vertically* — each feeds the next. A
    ColumnTransformer splits *horizontally* — each branch sees a different slice
    of the same input, never each other's output. Compose them: ColumnTransformer
    for the width, Pipelines for the depth inside each branch.

## `remainder`: unlisted columns

Any column not routed to a branch is handled by `remainder`, which defaults to
`"drop"` — so unrouted columns silently disappear from the output.

!!! warning "Unlisted columns are dropped by default"
    Add a feature, forget to route it, and it vanishes. Set
    `remainder="passthrough"` to append untouched columns (or pass a transformer
    to apply to them).

## Dropping and renaming columns

scikit-learn has no standalone drop or rename step. A `ColumnTransformer` decides
which columns survive, and `get_feature_names_out()` decides what they are called.
`set_output(transform="pandas")` turns those names into DataFrame columns.

### Dropping

```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler

ct = ColumnTransformer(
    [("ids", "drop", ["id"]),                    # deny-list: name what goes
     ("num", StandardScaler(), ["ret", "vol"])],
    remainder="passthrough",                     # everything else kept as-is
)
```

- `"drop"` / `"passthrough"` in the transformer slot discard or keep the listed
  columns. `remainder="drop"` (the default) is the opposite style: an allow-list
  where every unlisted column is dropped.
- Select by regex or dtype with
  `sklearn.compose.make_column_selector(pattern=..., dtype_include=...)`.
- A branch is a parameter, so a search can try it both ways:
  `{"pre__ids": ["drop", "passthrough"]}` turns feature ablation into a
  [hyperparameter](hyperparameter-search.md).

### Renaming

- `verbose_feature_names_out=False` removes the `num__` / `remainder__` prefixes
  (`num__ret` → `ret`). If two names collide, it raises a `ValueError` rather
  than guessing.
- A format string (scikit-learn ≥ 1.6) sets your own pattern:
  `verbose_feature_names_out="{feature_name}_{transformer_name}"` → `ret_num`.
- For an arbitrary mapping, add a [`FunctionTransformer`](custom-transformers.md) step after the
  ColumnTransformer:

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

mapping = {"ret": "returns", "vol": "volume"}
rename = FunctionTransformer(
    lambda df: df.rename(columns=mapping),
    feature_names_out=lambda self, names: [mapping.get(n, n) for n in names],
)
pipe = Pipeline([("pre", ct), ("rename", rename)]).set_output(transform="pandas")
```

!!! warning "`feature_names_out` wins under pandas output"
    With `set_output(transform="pandas")`, scikit-learn overwrites a returned
    DataFrame's columns with `get_feature_names_out()`. A `func` that renames
    without a matching `feature_names_out` callable has its names replaced.
    Keep the two in sync.

## Canonical pattern: nest Pipelines inside branches

A branch's transformer can be a Pipeline, giving "[impute](imputation.md) then scale" for numerics
and "impute then one-hot" for categoricals — the whole recipe as one leak-safe
`fit` boundary:

```python
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler

pre = ColumnTransformer([
    ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                      ("scale",  StandardScaler())]),                    numeric),
    ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                      ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
])

model = Pipeline([("pre", pre), ("clf", LogisticRegression())])
model.fit(X_train, y_train)   # every median/mean/vocabulary learned on train only
```

- `handle_unknown="ignore"` emits an all-zeros row for a category unseen at fit
  time (a new regime in the test window) instead of raising — the honest
  behaviour, since the encoder's vocabulary is learned on train only.
- `GridSearchCV` addresses nested params with chained double underscore:
  `"pre__num__impute__strategy"`, `"pre__cat__onehot__min_frequency"`.
- `make_column_transformer(...)` is the terser constructor that auto-names
  branches from class names; use explicit `ColumnTransformer([...])` names when
  you want stable handles for tuning.
