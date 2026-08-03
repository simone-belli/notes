# String Formatting in Python

Four ways to embed values into strings. f-strings are the modern default.

| Situation | Use |
|-----------|-----|
| Normal case | f-string |
| Template stored in a variable / config | `str.format()` |
| Logging calls | `%`-style (deferred evaluation) |
| Template from untrusted user input | `string.Template` |

---

## f-strings (Python 3.6+)

Prefix a string literal with `f`. Any `{expression}` is evaluated at runtime:

```python
name, age = "Alice", 30
f"Hello, {name}! You are {age}."     # arbitrary expressions: attr, index, calls, ternary
f"{price * 1.2:.2f}"                 # format spec after colon
f"{'yes' if flag else 'no'}"
```

### Debug shorthand

`f"{expr=}"` prints the source text and the value — useful for quick inspection:

```python
x = 42
f"{x=}"           # 'x=42'
f"{x * 2 + 1=}"   # 'x * 2 + 1=85'
f"{x=:.2f}"       # 'x=42.00'
```

### Dynamic spec

The spec field can itself be an expression:

```python
f"{value:{width}.{precision}f}"   # width and precision from variables
```

### Raw f-strings

```python
rf"C:\users\{path}\file.txt"   # backslashes literal; braces still interpolate
```

---

## str.format()

Useful when the template is a variable (can't do that with an f-string literal):

```python
"{} is {}".format("Alice", 30)          # positional
"{0} and {0}".format("echo")            # reuse by index
"{name}".format(name="Alice")           # keyword

TEMPLATE = "Dear {name}, order #{id} shipped."
TEMPLATE.format(**order_dict)           # fill from dict
```

Format specs work identically to f-strings: `"{:.2f}".format(3.14)`.

---

## %-formatting — legacy

!!! tip "Use %-style in logging calls — the string is only built if the message is emitted"
    `log.debug(f"parsed {n} records")` always builds the string, even if DEBUG is disabled. `log.debug("parsed %d records", n)` skips string construction entirely when the level is filtered out. In hot paths or tight loops, this difference matters.

Avoid in new code. Still conventional in `logging` because formatting is deferred until the message is actually emitted:

```python
logger.debug("processing %s items", len(items))   # string not built if DEBUG is off
```

---

## string.Template — for untrusted input

No expressions, no arbitrary Python — safe when the template comes from user input or config:

```python
from string import Template
Template("Hello, $name!").substitute(name="Alice")
Template("Hi $name").safe_substitute()   # leaves unknown $vars intact instead of raising
```

---

Format specs — alignment, width, precision, type codes — are their own reference: see [format-spec.md](format-spec.md).

---

## Splitting strings

```python
"a,b,c".split(",")           # ['a', 'b', 'c']
"a, b, c".split(", ")        # ['a', 'b', 'c']

# Strip whitespace around each item after splitting
[s.strip() for s in "a , b , c".split(",")]   # ['a', 'b', 'c']

# Limit number of splits
"a,b,c,d".split(",", maxsplit=2)   # ['a', 'b', 'c,d']

# Reverse: join a list back into a string
",".join(["a", "b", "c"])    # 'a,b,c'
```

- `split()` with no argument splits on any whitespace and removes empty strings: `"a  b\tc".split()` → `['a', 'b', 'c']`.
- For CSV with quoted fields, use the [`csv`](https://docs.python.org/3/library/csv.html) module instead of `split`.
