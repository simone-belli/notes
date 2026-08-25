# Random permutations

- `random.shuffle(x)` — shuffles a mutable sequence **in place**, returns `None`. Only works on lists (not tuples/strings).
- `random.sample(population, k)` — returns a **new** list of `k` unique elements, original untouched. Pass `k=len(population)` for a full permutation. Works on any sequence, including tuples/strings.

```python
import random

items = [1, 2, 3, 4, 5]
random.shuffle(items)                    # items reordered in place

items = [1, 2, 3, 4, 5]
new_order = random.sample(items, len(items))  # items unchanged, new_order is the permutation
```

!!! tip "Fisher-Yates under the hood"
    Both use the Fisher-Yates (Knuth) shuffle: O(n), uniform over all n! permutations.

Reproducible results: `random.seed(42)` (module-global) or `random.Random(42)` (private instance, no global side effects).

numpy equivalent: `numpy.random.default_rng().permutation(arr)` (copy) or `.shuffle(arr)` (in place).

For seeding an ML stack end to end — why a global seed isn't enough once
[scikit-learn](../../../ml/scikit-learn/estimators.md) or
[Optuna](../../../ml/experiments/optuna.md) are involved — see
[Reproducibility and Seeding](../../../ml/concepts/reproducibility.md).
