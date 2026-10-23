# Python — Language / Objects / Classes

How the class and instance machinery works underneath — the protocols your own classes implement.

:material-text-box-outline: **[Class attributes](class-attributes.md){ .lvl-basic }**
:   Values shared by every instance: class vs instance attributes, shadowing, `ClassVar`/`Final`, mutable-default trap

:material-text-box-outline: **[Classes: Inheritance and ABCs](oop.md){ .lvl-basic }**
:   Inheritance, MRO, composition over inheritance, ABCs

---

:material-text-box-outline: **[The Data Model and Pythonic Objects](data-model.md){ .lvl-intermediate }**
:   Dunder methods, `__new__` vs `__init__`, pythonic objects, instance/class/static methods, `@dataclass`

:material-text-box-outline: **[`__hash__` — Making Objects Hashable](hash.md){ .lvl-intermediate }**
:   `__hash__`: hash contract, `__eq__` coupling, mutability, dataclasses

:material-text-box-outline: **[Class introspection](introspection.md){ .lvl-intermediate }**
:   Checking whether a class has a member: `hasattr` pitfalls, `inspect.getattr_static`, own `__dict__` vs MRO, and `ast` for "does it call X?"

:material-text-box-outline: **[Slicing](slicing.md){ .lvl-intermediate }**
:   The `slice` object behind `obj[a:b:c]`, `.indices()`, tuple and `Ellipsis` keys, and a generic `__getitem__` that dispatches int vs slice

:material-text-box-outline: **[Subclassing](subclassing.md){ .lvl-intermediate }**
:   Overriding and extending: `super()` and the MRO, C3 linearisation, cooperative multiple inheritance, mixins, the built-in-type trap, LSP and `@override`

---

:material-text-box-outline: **[Attribute lookup protocol](attribute-lookup.md){ .lvl-advanced }**
:   `obj.x` lookup order: descriptors, `__getattr__` vs `__getattribute__`, `__slots__`

:material-text-box-outline: **[Class body execution and class creation](class-creation.md){ .lvl-advanced }**
:   Classes vs. metaclasses, class body execution order, `__init_subclass__`
