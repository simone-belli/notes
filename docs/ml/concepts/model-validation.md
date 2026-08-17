---
quiz: core
---

# Model Validation

Training error is not generalisation error. Any model with enough capacity can
memorise the data it was fitted on, so its score on that data measures recall, not
skill. Validation is the practice of estimating performance on data the model has
never seen — and the estimate is only as trustworthy as the protocol that
produced it.

## Three roles for data

- **Training set** — the model fits its parameters here.
- **Validation set** — you compare candidates here: hyperparameters, feature sets,
  model families. Consumed by every decision you make against it.
- **Test set** — used once, on a frozen model, to report a number.

The three are separate because they answer different questions, and because each
choice made against a set costs some of that set's independence.

!!! warning "Validation and test are not synonyms"
    Merging them is the most common protocol error. If you tuned against it, it
    is a validation set — no matter what the variable is called. The reported
    number then describes the best of your attempts rather than the model, and
    the gap grows with the number of attempts.

## Hold-out versus k-fold

A single hold-out split is cheap and gives one estimate from one arbitrary
partition. On small data that estimate has high variance — reshuffle and the score
moves several points, telling you more about the split than the model.

**k-fold cross-validation** partitions the data into `k` folds, and uses each fold
as the test set once against a model trained on the remaining `k-1`:

```
fold 1:  TEST  train train train train
fold 2:  train TEST  train train train
fold 3:  train train TEST  train train   →  k scores, one per fold
```

- Every row is used for both training and testing, at different times.
- You get `k` scores, and their **spread matters as much as their mean**. A high
  variance across folds says the estimate is unstable — report it.
- Cost is `k` fits. `k=5` and `k=10` are conventional; larger `k` means lower bias
  (more training data per fold) and higher cost.
- **Leave-one-out** is the `k = n` extreme: near-unbiased, expensive, and its
  folds are so correlated that the variance of the estimate is often *worse*.

Two common refinements to which rows land where:

- **Stratification** preserves the class proportions in every fold. Standard for
  imbalanced classification, where a random split can hand a fold almost none of
  the minority class.
- **Group-aware splitting** keeps all rows sharing an identity (patient, user,
  instrument) on one side of the boundary, so near-duplicates cannot straddle it.

## The premise underneath it all

k-fold rests on one assumption: rows are **independent and identically
distributed** (i.i.d.), and therefore exchangeable. That is exactly what licenses
shuffling.

When the assumption fails, the score does not merely get noisier — it is biased
*upward*, because the folds share information. It fails for time series
(neighbouring rows are correlated, and the distribution shifts with regime), for
repeated measures, and for any dataset with clustered observations. See
[Time-Series Validation](time-series-validation.md) for the replacement protocol.

!!! note "Cross-validation scores a procedure, not a model"
    The loop fits `k` models and throws all of them away. What you get back
    estimates how well *the recipe* — this preprocessing, this model family,
    these hyperparameters — performs when trained on data of this size. The model
    you ship is a separate final fit on everything. This is why every learned step
    must sit inside the loop: the recipe includes the preprocessing.

## Nested cross-validation

If you tune hyperparameters against the same folds you report, the reported score
includes the noise you selected for. Optimistic bias grows with the size of the
search.

The fix is two loops. The **inner** loop searches hyperparameters within each
training fold; the **outer** loop scores the whole tuned procedure on data the
inner loop never touched:

```
outer fold 1 ── train ──▶ [inner CV picks hyperparameters] ──▶ score on outer test
outer fold 2 ── train ──▶ [inner CV picks hyperparameters] ──▶ score on outer test
```

Cost multiplies (`outer × inner × candidates`), which is why it is often skipped —
but skipping it means the headline number is a best-of, not an estimate. Note that
each outer fold may select *different* hyperparameters: nested cross-validation
evaluates the tuning procedure, and does not by itself hand you one model to
deploy.

## Choosing the metric

The protocol decides *what* data the score sees; the metric decides what the score
means. Accuracy on a 99%-negative dataset is 99% for a model that predicts nothing
— pick a metric that is sensitive to the errors you care about (precision and
recall, Area Under the Receiver Operating Characteristic curve (ROC AUC), mean
absolute error), and compare every candidate against a trivial baseline: the
majority class, the mean, or yesterday's value.

## Related

- [Data Leakage](data-leakage.md) — the failure modes this protocol exists to prevent
- [Time-Series Validation](time-series-validation.md) — what to do when i.i.d. fails
- [Running Cross-Validation](../scikit-learn/cross-validation.md) — executing the loop in scikit-learn
- [Train/Test Splitting](../scikit-learn/splitting.md) — the splitter catalogue
