---
quiz: core
---

# Pandas — Indexing, Views and Copies

## SettingWithCopyWarning

Triggered by **chained indexing used for assignment**: two `[]` operations where the first may return a copy.

```python
df[df['age'] > 18]['name'] = 'adult'   # WARNING — assignment likely lost
```

Step 1 (`df[df['age'] > 18]`) returns a new object (view or copy — not guaranteed). Step 2 writes to that object. If it's a copy, `df` is unchanged.

**Why view vs copy is unpredictable:** [NumPy returns a view](../numpy/indexing.md) for contiguous slices, a copy for boolean masks and fancy integer indexing. Pandas can't tell you which you got.

### The fix: `.loc` for any write

`.loc[row_mask, col]` is a single operation directly on the original — no intermediate object.

```python
df.loc[df['age'] > 18, 'name'] = 'adult'   # correct
```

!!! warning "Reading can chain; writing must use .loc on the original"
    `df[mask]['col'] = v` is two separate operations. The first may return a copy, and the write lands on that copy — `df` is silently unchanged. `.loc[mask, 'col'] = v` is one operation and always modifies `df` directly. This applies under both old pandas and Copy-on-Write semantics.

### Explicit `.copy()` for an independent subset

```python
subset = df[df['age'] > 18].copy()   # explicit intent: separate object
subset['name'] = 'adult'             # safe, no warning
```

### Decision table

| Intent | Pattern | Correct? |
|--------|---------|----------|
| Read from subset | `df[mask]['col'].mean()` | Yes |
| Modify original | `df.loc[mask, 'col'] = v` | Yes |
| Work with a separate copy | `sub = df[mask].copy(); sub['col'] = v` | Yes |
| Modify original (wrong way) | `df[mask]['col'] = v` | No — warning |

### Pandas 2.0+ Copy-on-Write (CoW)

CoW (default in pandas 3.0) makes every indexing result a copy — view-mutation is gone, the warning disappears. Code that wrote to a slice expecting to modify the original silently breaks. Fix: `.loc` on the original, which is correct under both old and CoW semantics.
