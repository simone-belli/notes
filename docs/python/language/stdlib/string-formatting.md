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

## String-specific format specs

```
{value:[fill][align][.precision]}
```

Strings default to **left-aligned**; numbers default to right-aligned.

```python
f"{'text':<20}"      # 'text                '  — left-aligned (explicit)
f"{'text':>20}"      # '                text'  — right-aligned
f"{'text':^20}"      # '        text        '  — centred
f"{'text':*^20}"     # '********text********'  — fill char before align
```

**Truncation** — `.precision` on a string means max character count:

```python
f"{'hello world':.5}"      # 'hello'
f"{'hello world':<20.5}"   # 'hello               '  — truncate then pad
```

Fixed-width table columns that never overflow:

```python
for name, value in rows:
    print(f"{name:<20.20} {value:>10.2f}")
```

---

## Number format specs

See the type codes, precision, sign, and separator options in the section below —
they apply inside any `{}`, whether an f-string, `.format()`, or `format()` call.

### Type codes

| Code | Output | Example |
|------|--------|---------|
| `f`  | Fixed-point | `f"{3.14:.2f}"` → `'3.14'` |
| `e`/`E` | Scientific | `f"{12345:.2e}"` → `'1.23e+04'` |
| `g`  | Fixed or scientific, shorter | `f"{3.14159:.4g}"` → `'3.142'` |
| `%`  | Percent (×100) | `f"{0.173:.1%}"` → `'17.3%'` |
| `d`  | Integer decimal | `f"{42:d}"` → `'42'` |
| `b`/`x`/`X`/`o` | Binary / hex / HEX / octal | `f"{255:x}"` → `'ff'` |

### Precision

`.precision` = **decimal places** for `f`/`e`/`%`; **significant figures** for `g`:

```python
f"{3.14159:.2f}"   # '3.14'
f"{3.14159:.4g}"   # '3.142'
```

### Width, alignment, padding

```python
f"{3.14:10.2f}"    # '      3.14'  — right-aligned in 10 (default for numbers)
f"{3.14:<10.2f}"   # '3.14      '  — left-aligned
f"{3.14:^10.2f}"   # '   3.14   '  — centred
f"{3.14:010.2f}"   # '0000003.14'  — zero-padded
```

### Sign

```python
f"{3.14:+.2f}"    # '+3.14'
f"{3.14: .2f}"    # ' 3.14'  — space for positive
```

### Separators

```python
f"{1234567:,.2f}"   # '1,234,567.00'
f"{1234567:_.2f}"   # '1_234_567.00'
```

### Alternate form

```python
f"{255:#x}"    # '0xff'
f"{255:#010x}" # '0x000000ff'
f"{10:#b}"     # '0b1010'
```

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

---

## Custom __format__

Any class can define how it responds to a format spec:

```python
class Money:
    def __format__(self, spec):
        if spec == "short":
            return f"${self.amount:,.0f}"
        return f"${self.amount:{spec}}"

f"{Money(1234.5):.2f}"    # '$1234.50'
f"{Money(1234.5):short}"  # '$1,235'
```
