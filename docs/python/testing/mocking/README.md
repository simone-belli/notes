# Testing — Mocking

Replacing a dependency with a controlled substitute: the fake object itself, the machinery that installs it in place of the real thing, and a worked example on HTTP calls.

:material-text-box-outline: **[Mock objects](mocks.md){ .lvl-intermediate }**
:   Mock vs MagicMock, the four configuration channels, `return_value` vs `side_effect`, `spec`/`autospec`, call inspection, AsyncMock

:material-text-box-outline: **[patch](patch.md){ .lvl-intermediate }**
:   Installing the fake: patch-where-it's-used, patching classes, methods, properties and `__init__`-created attributes, every argument and variant, the four application forms

---

:material-text-box-outline: **[Network calls](network.md){ .lvl-advanced }**
:   Worked example: testing HTTP-calling functions — boundary patching, monkeypatch vs patch, side_effect sequences
