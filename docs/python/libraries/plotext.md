---
tags:
  - cli
---

# plotext

Plots charts as coloured text in the terminal — no GUI, no image file, no browser, and no
required dependencies. Useful over SSH, in containers, in CI logs, and for `--plot` flags on
your own CLI tools. Think diagnostic instrument, not figure generator: the resolution ceiling
is the terminal window.

```
pip install plotext
```

!!! warning "Version 6 is a rewrite — most examples online are version 5"
    Up to `5.3.2` plotext mimicked matplotlib: `plt.scatter(y)`, `plt.plot(y)`, `plt.show()`
    on the module itself. Version `6.0.0` removed all of it — the module has no `plot`,
    `scatter`, or `show` any more. Everything goes through `plt.figure`. This note covers
    6.x (current: `6.1.0`).

## The model

Three nouns: the **figure** (`plt.figure`, a singleton), **signals** (objects representing
one drawable series), and **`draw()`** (attaches a signal to the figure).

```python
import plotext as plt

f = plt.figure
f.draw(f.signal([1, 4, 9, 16, 25]))
f.show()
```

`f.signal(...)` *constructs and returns* a signal — it does not add it to the plot.
Forgetting `draw()` gives you an empty plot box with no error.

Signals and figure methods are chainable, each returning itself:

```python
f.draw(f.signal(x, y, marker="braille").lines().label("throughput"))
```

There is no `scatter` vs `plot` split any more: a signal is a set of points, and `.lines()`
decides whether they get connected. Scatter is the default.

## Worked example

```python
import plotext as plt

f = plt.figure
f.plot_size(70, 20)                 # character cells; omit to fill the terminal
f.theme("dark")

f.draw(f.signal(plt.sin(periods=2, length=200), marker="braille").lines().label("sin"))
f.draw(f.signal(plt.noise(length=50), marker="dot").label("noise"))

f.title("Signals")
f.label("time", axis="x")
f.label("amplitude", axis="y")
f.legend()
f.show()
```

```
                                Signals
    ┌────────────────────────────────────────────────────────────────┐
 1.9┤┌─────────┐                                                     │
    ││ ⢕ sin   │                          ⢀⡤⠤⠤⣄                      │
 0.9┤│ • noise │⠑⢤  •                   ⣠⠚⠁    ⠉⠲⣀                   │
    │└─────────┘•• ⠈⠣•               ⡔⠃            ⠑⣄                │
-0.1┤⠈   •           ⠱⢄            ⢀⠜               ⠈⢢             ⡰⠁│
    │     •       ••    ⠉⠦⡀    ⢀⡤⠊                      ⠓⣄⡀    ⣀⠔⠁   │
-1.2┤      •  •   •••     ⠈⠑⠒⠒⠚⠁                          ⠉⠒⠒⠒⠋⠁     │
    └┬──────────┬─────────┬──────────┬─────────┬─────────┬──────────┬┘
     1.0       34.2      67.3      100.5     133.7     166.8    200.0
amplitude                         time
```

## Signal types

| Constructor | Draws |
|---|---|
| `f.signal(*args, marker=…)` | points, optionally connected — the workhorse |
| `f.bar(labels, values)` | bars; `orientation`, `stacked`, `fill` |
| `f.hist(data, bins=10)` | histogram |
| `f.box(*args)` | box-and-whisker |
| `f.heatmap(data, map="gray")` | 2D grid of coloured cells (values or `(r, g, b)`) |
| `f.candlestick(data)` | Open-High-Low-Close (OHLC) financial candles |
| `f.error(*args)` | error bars |
| `f.line(position, orientation=0)` | a straight reference line |
| `f.text(x, y, label)` | free text annotation |
| `f.image(path)` | an image as coloured cells |

!!! warning "`f.line()` is a reference line, not a line plot"
    A line plot is `f.signal(...).lines()`. `f.line(3)` draws a single straight rule across
    the plot at position 3.

### Signal methods

All chainable:

- `.lines(active=True)` — connect consecutive points; `.line(index)` connects one segment.
- `.label("name")` — legend entry.
- `.fillx()` / `.filly()` — area fill to the x or y axis; `.fill(other)` fills between two signals.
- `.density("simple" | "full")` — `simple` is fast but leaves gaps on steep segments, `full`
  paints every crossed cell.
- `.log()` — logarithmic scaling.

## Markers

`marker=` takes a character (`"*"`), a code (`"braille"`, `"dot"`, `"hd"`, `"sd"`, `"fhd"`),
a `plt.marker()` object, or a **list** — one per point, which is how you colour points
individually. `plt.markers()` prints the full table.

Resolution, low to high: plain ASCII (1 dot per cell) → `sd` (2×2) → `hd` (2×3, the default)
→ `fhd` (2×4 blocks) → `braille` (2×4 dots).

!!! tip "Braille buys resolution, not colour"
    A Braille glyph has one foreground colour per cell, so overlapping series can't both keep
    their colour there. Use `braille` for a dense single curve, block markers when several
    series overlap.

## Axes and appearance

```python
f.plot_size(width, height)
f.title("…")
f.label("time", axis="x")      # axis="x"|"y", side="lower"/"upper"/"left"/"right"
f.legend()                     # position with x=, y=, ha=, va=
f.theme("dark")
f.axes(active=False)           # hide the frame
f.canvas(background="black")
f.ruler(axis="x")              # tick and limit control
f.log()
```

Every signal takes `xside=` (`"lower"`/`"upper"`) and `yside=` (`"left"`/`"right"`) — draw one
series on each side to get a secondary axis with its own tick scale.

Themes: `default`, `dark`, `colorless`, `simple`, `windows`, `matrix`, `retro`, `dreamland`,
`dusk`, `garden`, `sand`, `wine`. Add your own with `plt.add_theme(...)`. `plt.themes()`,
`plt.colors()`, `plt.styles()` print live reference tables.

!!! warning "Unknown theme names fail silently"
    `f.theme("nonexistent")` doesn't raise — it just keeps the previous theme. Check
    `plt.themes()` if a theme change appears to do nothing.

## Subplots

`f.subplots(rows, cols)` declares the grid; `f.subplot(row, col)` (1-indexed) returns an
object with the same method set as the figure:

```python
f.subplots(1, 2)

a = f.subplot(1, 1)
a.draw(a.bar(["a", "b", "c"], [3, 7, 5]))
a.title("bar")

b = f.subplot(1, 2)
b.draw(b.hist(plt.noise(length=500), bins=15))
b.title("hist")

f.show()
```

`show()` stays on the parent figure; a per-subplot `plot_size` sets that panel's share.

## Dates

Opt in per axis, and declare the format — the default is `%d/%m/%Y`, so ISO dates fail with a
confusing `KeyError` if you forget:

```python
f.date(axis="x").activate(form="%Y-%m-%d")
f.draw(f.signal(["2026-01-01", "2026-01-02"], [3, 5]).lines())
```

That axis then accepts date strings, UNIX timestamps, or `datetime` / [pandas
`Timestamp`](../../data/pandas/datetimes.md) objects. Helpers: `f.date().today()`,
`f.date().convert(t, output="timestamp")`.

!!! warning "`f.clear()` deactivates the date axis"
    `activate()` doesn't survive a clear, so a streaming plot must re-activate dates on every
    frame. Miss it and the first frame renders fine while the second dies with
    `TypeError: must be real number, not Timestamp`.

## pandas

There is no integration layer — no `.plot.plotext()` accessor, no `data=`/`x=`/`y=` column
arguments. plotext is duck-typed: anything that iterates into numbers plots, and `Series`,
`Index`, and NumPy arrays all qualify. So you pass **columns, never the frame**.

```python
import pandas as pd
import plotext as plt

f = plt.figure
f.draw(f.signal(df["t"], df["v"], marker="braille").lines())
f.show()
```

| Input | Result |
|---|---|
| `f.signal(df["v"])` | Series as y |
| `f.signal(df["t"], df["v"])` | Series as x and y |
| `f.signal(df.index, df["v"])` | `Index` works as x |
| `f.bar(g.index, g.values)` | e.g. a `groupby().sum()` result |
| `f.hist(df["v"], bins=20)` | fine |
| `f.signal(df)` | **`ArgumentError: must be real number, not str`** |

Multiple columns are an explicit loop, which is also how each series gets a legend label:

```python
for col in df.columns:
    f.draw(f.signal(df.index, df[col], marker="braille").lines().label(col))
f.legend()
```

A [`DatetimeIndex`](../../data/pandas/datetimes.md) needs `f.date(axis="x").activate(form=…)`
first — without it, `TypeError: must be real number, not Timestamp`.

!!! warning "`pd.NA` raises; `np.nan` doesn't"
    Float `NaN` is skipped and leaves a gap in the connecting line. pandas **nullable** dtypes
    (`Float64`, `boolean`) carry `pd.NA` instead and blow up with `TypeError: must be real
    number, not NAType`. Convert first: `f.signal(s.astype("float64"))`. Nullable dtypes
    arrive silently from `convert_dtypes()`, Arrow-backed frames, and
    `read_csv(dtype_backend="numpy_nullable")`.

`f.candlestick()` wants **lowercase** keys — `date`, `open`, `high`, `low`, `close` — while
market data conventionally capitalises them, giving a bare `KeyError: 'open'`:

```python
f.date(axis="x").activate(form="%Y-%m-%d")
f.draw(f.candlestick({"date": ohlc.index, **ohlc.rename(columns=str.lower).to_dict("list")}))
```

The escape hatch is the matplotlib bridge — `df.plot()` returns matplotlib axes, so you can
build the plot the pandas way and render it in the terminal, at the cost of a matplotlib
dependency:

```python
ax = df.plot(x="t", y="v")
plt.matplotlib(ax.get_figure())
f.show()
```

## Streaming

Clear → draw → show → sleep:

```python
while True:
    f.clear()
    f.draw(f.signal(read_latest_window()).lines())
    f.show()
    plt.sleep(0.1)
```

Use `plt.sleep()` rather than `time.sleep()` — it's the hook plotext uses to reduce flicker.
`f.interactive(True)` makes every mutating call reprint the figure immediately, so `show()`
is never needed: handy in a REPL, wasteful in a loop.

`f.build()` returns the rendered figure as an object instead of printing it — that's how you
embed a plot in something else, such as a [rich](terminal-tables.md) panel.
`f.show(colorless=True)` strips the ANSI codes, which is what you want for a file or CI log.

## Beyond charts

- `plt.image(path)`, `plt.gif(path)`, `plt.video(path)` — render images, GIFs, and video
  (file, URL, or YouTube URL) as terminal cells; `q` exits.
- `plt.matplotlib(fig)` — converts an existing matplotlib `Figure` into the plotext figure.
  matplotlib is imported only inside this call, so it stays optional.
- `plt.sin()`, `plt.square()`, `plt.noise()`, `plt.sample()` — synthetic data for experiments.

## The CLI

Installing plotext puts a `plotext` executable on `PATH` that mirrors the Python API: each
`--METHOD` is one call, and the words after it are its arguments.

```console
$ plotext --figure --plot_size 70 12 --signal '[1,4,9,16,25,12,6]' marker=braille \
      --lines --draw --title demo --show
```

- `'[1,2,3]'` → list (quote it, or the shell globs it)
- `key=value` → keyword argument
- `-` → read from a pipe: `echo '1 2 3' | plotext --figure --signal - --draw --show`
- `@path:data.csv:2` → column 2 of a CSV; `@sample:pizzas` → a bundled dataset

`plotext --doc` opens an interactive doc browser and `plotext --signal --doc` prints one
docstring. The same text is available as `help(plt.figure.signal)`, and it lists types,
defaults, and return values for every parameter. Given how much the API changed in 6.0, the
shipped docs are more reliable than search results.

## Related

- [Printing Tables in the Terminal](terminal-tables.md)
