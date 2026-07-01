# Mutation of function arguments

Python passes object references. Both the caller's variable and the function's parameter point to the **same object**. What happens outside the function depends on what you do with it.

- **Rebind the local name** (`x = ...`) → caller sees no change.
- **Mutate the object in-place** (`.append`, `[key] =`, `obj.attr =`) → caller IS affected.

## Rebinding — caller unaffected

```python
def replace(data):
    data = [999]        # rebinds local name; caller's list untouched

prices = [1, 2, 3]
replace(prices)
print(prices)           # [1, 2, 3]
```

## In-place mutation — caller IS affected

```python
def add_price(data, value):
    data.append(value)  # modifies the shared object

prices = [1, 2, 3]
add_price(prices, 99)
print(prices)           # [1, 2, 3, 99]
```

Same for dicts (`trade["status"] = "filled"`) and objects (`order.status = "filled"`).

## Immutable types are always safe

`int`, `float`, `str`, `tuple` cannot be mutated — any "change" creates a new object and rebinds the local name. The caller always sees the original value.

```python
def increment(n):
    n += 1        # creates a new int, rebinds local n

x = 5
increment(x)
print(x)          # 5
```

## Mutable types — rebind vs mutate

```python
data += [99]      # list: in-place (__iadd__) — caller IS affected
data = data + [99] # rebind — caller unaffected
data.append(99)   # in-place — caller IS affected
```

!!! warning "list += is in-place; int += is a rebind"
    `+=` calls `__iadd__` on mutable types (mutates in place) but creates a new object for immutable types. The caller is affected for lists but not for ints — an easy source of confusion.

## Defensive copy

If a function should not touch the caller's data:

```python
def normalise(prices: list[float]) -> list[float]:
    prices = list(prices)   # shallow copy — now we own it
    prices.sort()
    return prices
```

Use `copy.deepcopy()` when the list contains mutable objects.

## Mental test

> Does this operation replace what the name points to, or modify what it points to?

| Operation | Effect |
|---|---|
| `x = new_value` | rebind — caller unaffected |
| `x.append(...)` | mutate — caller affected |
| `x[key] = val` | mutate — caller affected |
| `x.attr = val` | mutate — caller affected |
| any op on `int`/`str`/`tuple` | always rebind — caller unaffected |
