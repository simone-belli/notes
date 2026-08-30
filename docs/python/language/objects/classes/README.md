# Python — Language / Objects / Classes

How the class and instance machinery works underneath — the protocols your own classes implement.

:material-text-box-outline: **[Attribute lookup protocol](attribute-lookup.md){ .lvl-advanced }**
:   `obj.x` lookup order: descriptors, `__getattr__` vs `__getattribute__`, `__slots__`

:material-text-box-outline: **[Class body execution and class creation](class-creation.md){ .lvl-advanced }**
:   Classes vs. metaclasses, class body execution order, `__init_subclass__`

:material-text-box-outline: **[The Data Model and Pythonic Objects](data-model.md){ .lvl-intermediate }**
:   Dunder methods, `__new__` vs `__init__`, pythonic objects, `@dataclass`

:material-text-box-outline: **[`__hash__` — Making Objects Hashable](hash.md){ .lvl-intermediate }**
:   `__hash__`: hash contract, `__eq__` coupling, mutability, dataclasses

:material-text-box-outline: **[Classes: Inheritance and ABCs](oop.md){ .lvl-basic }**
:   Inheritance, MRO, composition over inheritance, ABCs
