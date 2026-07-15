# Python — Language / Objects

| File | Type | Description |
|------|------|-------------|
| [data-model.md](data-model.md) | note | Dunder methods, pythonic objects, `@dataclass` |
| [exceptions.md](exceptions.md) | note | Exception hierarchy, EAFP, raising/chaining, custom exceptions, best practices |
| [hash.md](hash.md) | note | `__hash__`: hash contract, `__eq__` coupling, mutability, dataclasses |
| [mutation.md](mutation.md) | note | Rebind vs mutate: when function argument changes are visible to the caller |
| [numbers.md](numbers.md) | note | Float comparison: `math.isclose`, `rel_tol`/`abs_tol`, `pytest.approx`, `np.isclose` |
| [oop.md](oop.md) | note | Inheritance, MRO, composition over inheritance, ABCs |
| [repository-di.md](repository-di.md) | note | Repository pattern + dependency injection: Protocol interface, in-memory fake, testable services |
| [sets.md](sets.md) | note | `set` and `frozenset`: creation, mutation, set operations, O(1) membership, gotchas |
| [structural-typing.md](structural-typing.md) | note | Structural vs nominal typing: Protocol, ABC comparison, runtime_checkable, verifying conformance |
| [subscriptable.md](subscriptable.md) | note | `__getitem__`, `__class_getitem__`, generic aliases, pre-3.9 annotation fixes |
| [typing.md](typing.md) | note | `typing` module: `Literal`, `TypeAlias`, `overload` — restrict and narrow types |
| [warnings.md](warnings.md) | note | `warnings.warn()`, stacklevel, filters, converting exceptions to warnings |