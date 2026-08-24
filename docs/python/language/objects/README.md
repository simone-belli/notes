# Python — Language / Objects

:material-text-box-outline: **[Attribute lookup protocol](attribute-lookup.md)**
:   `obj.x` lookup order: descriptors, `__getattr__` vs `__getattribute__`, `__slots__`

:material-text-box-outline: **[Class body execution and class creation](class-creation.md)**
:   Classes vs. metaclasses, class body execution order, `__init_subclass__`

:material-text-box-outline: **[The Data Model and Pythonic Objects](data-model.md)**
:   Dunder methods, `__new__` vs `__init__`, pythonic objects, `@dataclass`

:material-card-bulleted-outline: **[Dataclasses](dataclasses.md)**
:   `@dataclass` cheat sheet: decorator parameters, `field()`, `__post_init__`, `InitVar`, helpers, inheritance

:material-text-box-outline: **[Exceptions](exceptions.md)**
:   Exception hierarchy, EAFP, raising/chaining, custom exceptions, best practices

:material-text-box-outline: **[`__hash__` — Making Objects Hashable](hash.md)**
:   `__hash__`: hash contract, `__eq__` coupling, mutability, dataclasses

:material-text-box-outline: **[Mutation of function arguments](mutation.md)**
:   Rebind vs mutate: when function argument changes are visible to the caller

:material-text-box-outline: **[Float Comparison](numbers.md)**
:   Float comparison: `math.isclose`, `rel_tol`/`abs_tol`, `pytest.approx`, `np.isclose`

:material-text-box-outline: **[Classes: Inheritance and ABCs](oop.md)**
:   Inheritance, MRO, composition over inheritance, ABCs

:material-text-box-outline: **[Repository Pattern + Dependency Injection](repository-di.md)**
:   Repository pattern + dependency injection: Protocol interface, in-memory fake, testable services

:material-text-box-outline: **[Sets](sets.md)**
:   `set` and `frozenset`: creation, mutation, set operations, O(1) membership, gotchas

:material-text-box-outline: **[Warnings](warnings.md)**
:   `warnings.warn()`, stacklevel, filters, converting exceptions to warnings
