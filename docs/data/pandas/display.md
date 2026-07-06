# Pandas — Display Formatting

Two axes: **display options** (how many rows/columns, float precision) and **value formatters** (per-column string conversion).

## Global options — `pd.set_option`

```python
pd.set_option("display.max_rows", 100)         # None = all
pd.set_option("display.max_columns", None)
pd.set_option("display.float_format", "{:,.2f}".format)  # all floats
pd.set_option("display.max_colwidth", None)    # don't truncate cells
```

Use `pd.option_context` for a temporary change that auto-restores:

```python
with pd.option_context("display.max_rows", None, "display.precision", 6):
    print(df)
```

Common options:

| Option | Effect |
|--------|--------|
| `display.max_rows` | rows before truncation (`None` = all) |
| `display.max_columns` | columns before truncation (`None` = all) |
| `display.width` | terminal width before line-wrap |
| `display.max_colwidth` | chars per cell (default 50) |
| `display.precision` | float decimal places |
| `display.float_format` | callable `float → str` applied to all floats |

## Per-column formatters — `df.to_string()`

`formatters` takes a dict of `{column: callable}`:

```python
print(df.to_string(
    index=False,
    formatters={
        "price":  "{:,.2f}".format,    # 1,234.56
        "return": "{:+.2%}".format,    # +1.23%
        "volume": "{:,.0f}".format,    # 1,234,567
    }
))
```

Other useful `to_string` kwargs: `float_format`, `col_space` (min column width), `max_rows`, `max_cols`.

## Jupyter — `df.style`

`Styler` is for HTML/notebook output only; has no effect on `print()`.

```python
df.style \
  .format({"price": "{:,.2f}", "return": "{:.1%}"}) \
  .highlight_max(subset=["price"])
```

`format()` accepts a string, a dict, a callable, or `na_rep` for NaN replacement.

!!! tip "80% solution for financial data"
    `pd.set_option("display.float_format", "{:,.2f}".format)` at the top of the notebook formats every float with commas and 2 dp — no per-column work needed.

!!! note "option_context vs set_option"
    Prefer `option_context` in scripts or functions so options don't leak to other output. Use `set_option` only at the notebook/session level where persistence is intended.
