---
tags:
  - testing
quiz: detail
---

# Python — Numbers

## Integers

`int` is **arbitrary precision** — no `int32`/`int64`, no overflow, no wraparound. It grows until memory runs out. (`sys.maxsize` is the largest container index, not an integer limit.) Everything below follows from that: exact arithmetic always, at the cost of speed beyond one machine word.

### Division

```python
import math    # used throughout below

7 / 2          # 3.5  — true division, ALWAYS a float (even 4 / 2 → 2.0)
7 // 2         # 3    — floor division, int // int → int
7 % 2          # 1    — remainder
divmod(7, 2)   # (3, 1)
```

- Python **floors toward −∞**; C truncates toward zero: `-7 // 2 == -4`, `-7 % 2 == 1`.
- `%` takes the **sign of the divisor**; the invariant `a == (a // b) * b + a % b` always holds. This is why `i % n` on a negative `i` is a valid list index.
- `math.fmod(a, b)` for the C sign convention; `int(-3.7)` truncates to `-3` while `math.floor(-3.7)` is `-4`.

!!! warning "`int(a / b)` is not `a // b`"
    `a / b` routes through a float, so it truncates toward zero *and* loses precision above 2⁵³ — `int(10**18 / 3)` is silently wrong. Use `//`.

### Powers and bitwise

```python
2 ** 10         # 1024 — int
2 ** -1         # 0.5  — negative exponent returns a float
pow(2, 10, 7)   # 2    — modular exponentiation, no huge intermediate
pow(3, -1, 7)   # 5    — modular inverse (3.8+)

a & b, a | b, a ^ b, ~a, a << n, a >> n
x.bit_length()  # bits needed, sign ignored
x.bit_count()   # population count (3.10+)
```

- Bitwise ops use infinite two's complement: `~x == -x - 1`, and `>>` floors (`-1 >> 1 == -1`).
- `x << n` is exactly `x * 2**n` — not faster in CPython, so write whichever reads better.

### Literals, bases, and conversion

```python
1_000_000                 # underscores are visual separators
0b1010, 0o17, 0xff        # binary / octal / hex literals
int("ff", 16)             # 255 — parse in a base
int("0b1010", 0)          # 10  — base 0 infers from the prefix
bin(10), hex(255)         # '0b1010', '0xff'
f"{255:b}", f"{255:#x}"   # '11111111', '0xff'
```

`int("3.0")` raises `ValueError` — go through `int(float("3.0"))`. Since 3.11, `int` ↔ `str` conversion above 4300 digits raises `ValueError` (the conversion is quadratic; a denial-of-service hardening measure). Arithmetic is unaffected; lift the cap with `sys.set_int_max_str_digits(n)`.

### Integer-exact helpers

```python
math.isqrt(n)                # exact integer square root — int(math.sqrt(n)) can be off by one
math.gcd(a, b), math.lcm(a, b)
math.comb(n, k), math.perm(n, k), math.factorial(n)
```

### Rounding

`round()` uses **banker's rounding** (half-to-even), not the schoolbook rule:

```python
round(0.5), round(1.5), round(2.5)   # 0, 2, 2
round(1234, -2)                      # 1200 — negative ndigits rounds left of the point
```

!!! note "`bool` is a subclass of `int`"
    `True == 1`, `True + True == 2`, and `isinstance(True, int)` is `True`. So `sum([True, False, True])` counting truths is idiomatic — but an `isinstance(x, int)` guard will happily accept a bool. Separately, small integers (−5 to 256) are cached, so `256 is 256` is `True` while `1000 is 1000` may not be: never compare numbers with `is`.

Integers that fit one 30-bit digit are fast; beyond that arithmetic cost grows with size. For tight loops over bounded values, NumPy's [fixed-width integer dtypes](../../../data/numpy/dtypes.md) are far faster — but they overflow silently. Exactness vs. speed is the whole difference between `int` and `np.int64`.

## Float comparison

### Why `==` fails

Floats are IEEE 754 binary — many decimals can't be represented exactly:

```python
0.1 + 0.2 == 0.3   # False
```

### `math.isclose` — standard library

```python
math.isclose(a, b, rel_tol=1e-9, abs_tol=0.0)
# True if |a-b| <= max(rel_tol * max(|a|, |b|), abs_tol)
```

- `rel_tol` scales with magnitude — good for non-zero values
- `abs_tol` is a fixed floor — **required near zero** (relative tolerance of ~0 is ~0)

```python
math.isclose(1000.0, 1000.001, rel_tol=1e-3)  # True
math.isclose(0.0, 1e-10, abs_tol=1e-9)        # True
math.isclose(0.0, 1e-10)                       # False — rel_tol alone fails near zero
```

!!! warning "Near-zero comparisons need abs_tol"
    `rel_tol * max(|a|, |b|)` collapses to nearly zero when both values are tiny, so `isclose(0.0, 1e-15)` returns `False` with only the default `rel_tol`. Always pass `abs_tol` when either value can be near zero.

### pytest

```python
import pytest

assert 0.1 + 0.2 == pytest.approx(0.3)              # scalar
assert [0.1, 0.2] == pytest.approx([0.1, 0.2])      # sequence
assert {'v': 0.1} == pytest.approx({'v': 0.1})      # dict
# defaults: rel=1e-6, abs=1e-12; override with pytest.approx(x, rel=1e-3)
```

### NumPy arrays

```python
import numpy as np

np.isclose(a, b, rtol=1e-5, atol=1e-8)   # element-wise → bool array
np.allclose(a, b, rtol=1e-5, atol=1e-8)  # True if all close
# formula: |a-b| <= atol + rtol*|b|
```

### Quick reference

| Context | Tool |
|---------|------|
| General code | `math.isclose(a, b, rel_tol=…, abs_tol=…)` |
| Simple fixed scale | `abs(a - b) < tol` |
| Tests | `pytest.approx` |
| Arrays | `np.isclose` / `np.allclose` |
