# Format Spec Mini-Language

The `[fill][align][sign][#][0][width][,][.precision][type]` syntax inside a `{}` — shared by f-strings, `str.format()`, and `format()`. See [string-formatting.md](string-formatting.md) for the interpolation methods that embed a spec.

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
