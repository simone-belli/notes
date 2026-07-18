---
tags:
  - cli
---

# Printing Tables in the Terminal

Three options in increasing power:

| Need | Tool |
|------|------|
| No dependencies, fixed schema | f-strings + format spec |
| Quick readable output | `tabulate` |
| Colours, borders, styles | `rich` |
| Already using pandas | `df.to_string()` or `tabulate(df, headers="keys")` |

---

## 1. f-strings (no deps)

Use the [format spec mini-language](../language/stdlib/format-spec.md) for alignment and width:

```python
rows = [("Apple", 1.25, 100), ("Dragonfruit", 4.99, 12)]

print(f"{'Name':<15} {'Price':>8} {'Qty':>5}")
print("-" * 30)
for name, price, qty in rows:
    print(f"{name:<15} {price:>8.2f} {qty:>5d}")
```

For dynamic widths, compute them first:
```python
all_rows = [headers] + rows
widths = [max(len(str(r[i])) for r in all_rows) for i in range(len(headers))]
fmt = "  ".join(f"{{:<{w}}}" for w in widths)
```

---

## 2. tabulate

```
pip install tabulate
```

```python
from tabulate import tabulate

rows = [["Apple", 1.25, 100], ["Dragonfruit", 4.99, 12]]
headers = ["Name", "Price", "Qty"]

print(tabulate(rows, headers=headers, tablefmt="simple", floatfmt=".2f"))
```

### Input formats

```python
tabulate(rows, headers=headers)                  # list of lists
tabulate(rows, headers="keys")                   # list of dicts or DataFrame
tabulate({"Name": [...], "Price": [...]}, headers="keys")  # dict of columns
```

### `tablefmt` options

| Value | Output |
|-------|--------|
| `"simple"` (default) | Dashes under header |
| `"grid"` | Full ASCII grid |
| `"pipe"` | Markdown `\|` table |
| `"html"` | `<table>` |
| `"latex"` | LaTeX tabular |

### Number formatting

```python
tabulate(rows, headers=headers, floatfmt=".2f", intfmt=",")
```

---

## 3. rich

```
pip install rich
```

```python
from rich.console import Console
from rich.table import Table

console = Console()
table = Table(title="Fruit Prices")

table.add_column("Name", style="cyan", no_wrap=True)
table.add_column("Price", justify="right", style="green")
table.add_column("Qty",   justify="right")

table.add_row("Apple",       "£1.25", "100")
table.add_row("Dragonfruit", "£4.99",  "12")

console.print(table)
```

### Key options

```python
table.add_column("Col",
    style="bold",        # cell style
    justify="right",     # "left" | "right" | "center"
    no_wrap=True,
    min_width=10,
)

Table(
    show_lines=True,          # horizontal lines between rows
    box=box.ROUNDED,          # border style
)
```

### Box styles

```python
from rich import box
Table(box=box.SIMPLE)     # minimal
Table(box=box.ROUNDED)    # rounded corners
Table(box=box.MARKDOWN)   # Markdown-compatible
Table(box=box.ASCII)      # safe for non-unicode terminals
```

### Conditional cell styling

```python
from rich.text import Text

for row in data:
    color = "red" if row["price"] > 3 else "green"
    table.add_row(row["name"], Text(f"{row['price']:.2f}", style=color))
```
