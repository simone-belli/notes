---
tags:
  - config
  - performance
---

# Optuna — Distributions

`trial.suggest_float("lr", 1e-5, 1e-1, log=True)` looks like one call with three
arguments. It is two things: the arguments build a `FloatDistribution`, which
[Optuna](optuna.md) records in storage under the name `"lr"`, and the sampler then
returns a value drawn from it. That recorded object is a first-class value — you
can read it off a trial, build it by hand, and round-trip it through JSON.

!!! note "The escape hatch from define-by-run"
    Define-by-run makes the search space *implicit*: it exists only while the
    objective executes. Distribution objects make it explicit and portable again —
    the same space as **data** you can store in a config file, diff against last
    week's, and ship to a worker.

## The three classes

Since Optuna 4.0 there are exactly three, all in `optuna.distributions`:

```python
from optuna.distributions import (
    FloatDistribution, IntDistribution, CategoricalDistribution)

FloatDistribution(1e-5, 1e-1, log=True)         # ↔ suggest_float(..., log=True)
FloatDistribution(0.1, 1.0, step=0.05)          # ↔ suggest_float(..., step=0.05)
IntDistribution(16, 1024, log=True)             # ↔ suggest_int(..., log=True)
IntDistribution(2, 10, step=2)                  # ↔ suggest_int(..., step=2)
CategoricalDistribution(["linear", "rbf"])      # ↔ suggest_categorical
```

- The old zoo — `UniformDistribution`, `LogUniformDistribution`,
  `DiscreteUniformDistribution`, `IntUniformDistribution`,
  `IntLogUniformDistribution` — was deprecated in 3.0 and **removed in 4.0**,
  collapsing into the `log=` / `step=` flags. The names survive inside old SQLite
  files, which is why the JSON reader still understands them.
- `log=` and `step=` are mutually exclusive: a log-spaced grid isn't expressible.
- `dist.single()` is `True` when the distribution holds exactly one value
  (`FloatDistribution(0.1, 0.1)`); samplers check it and skip sampling, so a
  degenerate axis costs nothing.

### What `step` and `log` mean

A `step` turns the interval into a finite grid anchored at `low`:

$$
S = \{\, l + k s \;:\; k \in \mathbb{Z}_{\ge 0},\; l + k s \le h \,\}
$$

If $h - l$ is not an integer multiple of $s$ the top of the range is
unreachable, so Optuna narrows the distribution to $h'$ and warns:

$$
h' = l + \left\lfloor \frac{h - l}{s} \right\rfloor s
$$

`FloatDistribution(0.0, 1.0, step=0.3)` becomes $[0, 0.9]$ — worth knowing before
concluding the optimiser "never tried the top of the range". `log=True` instead
moves the uniform draw into log space, giving each decade equal mass:

$$
u \sim \mathcal{U}(\ln l,\, \ln h), \qquad x = e^{u}
$$

## Reading the space off a trial

`Trial` and `FrozenTrial` both carry a `distributions` dict parallel to `params`:

```python
study.best_trial.params          # {"lr": 0.0123, "max_depth": 7}
study.best_trial.distributions   # {"lr": FloatDistribution(...), "max_depth": IntDistribution(...)}
```

On a live `Trial` the dict grows as the objective runs — it holds only what has
been suggested *so far*. Since a conditional objective gives each trial a
different key set, samplers reason over the intersection instead:

```python
from optuna.search_space import intersection_search_space

intersection_search_space(study.get_trials(deepcopy=False))
```

It takes a list of trials rather than a study (changed in Optuna 3.2) and
silently **drops** parameters whose distributions disagree.

## JSON round-trip

Two module-level functions, and the string they speak is the format Optuna's own
parameter table stores:

```python
from optuna.distributions import distribution_to_json, json_to_distribution

blob = distribution_to_json(FloatDistribution(1e-5, 1e-1, log=True))
# '{"name": "FloatDistribution", "attributes": {"low": 1e-05, "high": 0.1, "step": null, "log": true}}'

json_to_distribution(blob)       # FloatDistribution(high=0.1, log=True, low=1e-05, step=None)
```

- A tagged union: `"name"` is the class, `"attributes"` the constructor keywords.
- `distribution_to_json` returns a **string**, not a dict — nest the parsed object
  to embed a whole space in one config file.
- Everything passes through `json.dumps`, which is the real reason
  `suggest_categorical` accepts only `None`/`bool`/`int`/`float`/`str`. The
  restriction is the serialisation boundary, not taste.

```python
import json

space = {"lr": FloatDistribution(1e-5, 1e-1, log=True),
         "max_depth": IntDistribution(2, 12)}

blob = json.dumps({k: json.loads(distribution_to_json(v)) for k, v in space.items()})
back = {k: json_to_distribution(json.dumps(v)) for k, v in json.loads(blob).items()}
```

!!! warning "Don't hand-write the attribute dicts"
    Build the JSON with `distribution_to_json` and read it with
    `json_to_distribution`. The attribute set has changed across major versions,
    and the reader is the piece that carries the compatibility shims for the
    removed classes.

## Compatibility checking

```python
from optuna.distributions import check_distribution_compatibility

check_distribution_compatibility(FloatDistribution(1e-5, 1e-1),
                                 IntDistribution(1, 10))          # raises ValueError
check_distribution_compatibility(CategoricalDistribution(["a", "b"]),
                                 CategoricalDistribution(["a", "c"]))   # raises
check_distribution_compatibility(FloatDistribution(1e-5, 1e-1),
                                 FloatDistribution(1e-8, 1.0))    # passes
```

It returns `None` and raises `ValueError` on a mismatch — a guard clause, not a
predicate, so `if check_distribution_compatibility(...)` is always falsy.

!!! warning "It compares kind, not range"
    Two `FloatDistribution`s are compatible however far apart their bounds are;
    `CategoricalDistribution`s must have *identical* choices. That is the
    granularity samplers need — a widened numeric range still lets old
    observations inform the model, a changed choice list invalidates the encoding
    — but it is weaker than "the space is unchanged". Resume a study after
    widening `low`/`high` and nothing warns you: the history now mixes two
    spaces. Diff the JSON yourself if that matters.

## Where hand-built distributions are used

Three places take a `dict[str, BaseDistribution]` directly — the payoff for the
round-trip.

### `study.ask(fixed_distributions=...)`

Pre-sample parameters in the [ask-and-tell](optuna-studies.md#ask-and-tell) flow,
so a space loaded from a config drives the search without the objective naming any
ranges:

```python
trial = study.ask(fixed_distributions={"lr": FloatDistribution(1e-4, 1e-1, log=True)})
trial.params["lr"]       # already there
```

### `create_trial` + `add_trial`

To inject trials whose results you *already know* — last quarter's runs, a study
you are migrating — build `FrozenTrial`s by hand. `params` and `distributions`
must be supplied together and must agree:

```python
import optuna

trial = optuna.trial.create_trial(
    params={"lr": 0.05, "max_depth": 6},
    distributions={"lr": FloatDistribution(1e-5, 1e-1, log=True),
                   "max_depth": IntDistribution(2, 12)},
    value=0.23,
)
study.add_trial(trial)
```

The sampler's model now starts warm on borrowed evidence. Contrast
[`study.enqueue_trial`](optuna-studies.md#storage-and-parallelism): that schedules
a point to be *evaluated* and needs no distributions, because the objective's own
`suggest_*` calls supply them. `add_trial` records a completed observation, so it
must carry the space explicitly.

### `OptunaSearchCV`

The scikit-learn-shaped wrapper is define-and-run, so its `param_distributions` is
a literal dict of these objects:

```python
from optuna.integration import OptunaSearchCV

search = OptunaSearchCV(estimator, {"alpha": FloatDistribution(1e-3, 1e3, log=True)})
```

That is the concrete cost of the drop-in interface: a static dict serialises
cleanly, but cannot express "`alpha` exists only when `model == "ridge"`".


## Related

- [Optuna](optuna.md) — define-by-run search spaces, the suggest API, samplers, and pruning
- [Optuna — Studies](optuna-studies.md) — storage, parallelism, ask-and-tell, and reading the run
- [Reproducibility and Seeding](../concepts/reproducibility.md) — the other half of making a search repeatable
- [Hyperparameter Search](../scikit-learn/hyperparameter-search.md) — the define-and-run distribution dicts this mirrors
- [YAML](../../tools/yaml.md) — where a serialised space usually lands
