---
tags:
  - performance
quiz: core
---

# Complexity and Data Structure Choice

Big-O describes how work *scales* with input size — not raw speed. The question: **if I double n, what happens to the work?**

## The four complexities you need

| | Doubles n → | Intuition |
|---|---|---|
| O(1) | no change | direct lookup — no searching |
| O(log n) | +1 step | binary search — halve possibilities each step |
| O(n) | doubles | must touch every element once |
| O(n²) | quadruples | every pair — a loop inside a loop |

```python
d["key"]        # O(1) — hash → slot → done
x in my_set     # O(1) — set is a hash table
bisect.bisect_left(sorted_lst, x)  # O(log n)
max(lst)        # O(n) — must check every element
x in lst        # O(n) — linear scan
for i in lst:
    if i in other_lst:  # O(n) inside O(n) loop → O(n²) total
        ...
# fix: convert other_lst to a set first → O(n) total
```

!!! warning "The O(n²) trap"
    `x in list` inside a loop is the most common performance mistake. Each `in` is O(n); n of them is O(n²). Convert the list to a set before the loop: O(n) build + O(1) per lookup = O(n) total.

## Python dict: open-addressing hash table

`dict` and `set` are hash tables: `hash(key) % table_size` maps directly to a slot. No scan needed — that's why lookup is O(1).

- **Amortised O(1)**: occasional resize copies all entries (O(n)) but spread across n inserts, the per-insert average is still O(1).
- **Worst case O(n)**: if every key collides (same hash slot), every lookup must probe all n entries. CPython's hash randomisation (since 3.3) makes this vanishingly rare.

## When to use which structure

| Need | Structure | Build | Lookup |
|------|-----------|-------|--------|
| Key → value | `dict` | O(n) | O(1) |
| Count occurrences | `Counter` | O(n) | O(1) |
| Group by key | `defaultdict(list)` | O(n) | O(1) |
| Membership / dedup | `set` | O(n) | O(1) |
| Fast both-end insert | `deque` | O(n) | O(n) |
| Repeated min/max | `heapq` | O(n) | O(log n) per pop |
| Search sorted data | sorted list + `bisect` | O(n log n) once | O(log n) |

```python
from collections import Counter, defaultdict

# Counter — counting
c = Counter(["a", "b", "a"])   # O(n) build
c["a"]                          # O(1) → 2
c.most_common(3)                # O(k log n)

# defaultdict — grouping without KeyError
groups = defaultdict(list)
for item, key in data:
    groups[key].append(item)    # O(1) per append, O(n) total

# set — dedup and fast membership
seen = set()
unique = [x for x in lst if not (x in seen or seen.add(x))]  # O(n)
```

## Common operations: complexity table

### list

| Operation | Complexity | Note |
|-----------|-----------|------|
| `lst[i]` | O(1) | direct index |
| `lst.append(x)` | O(1) amortised | |
| `lst.pop()` | O(1) | from end |
| `lst.pop(0)` / `lst.insert(0, x)` | O(n) | shifts all elements — use `deque` |
| `x in lst` | O(n) | linear scan |
| `lst.sort()` / `sorted()` | O(n log n) | Timsort |
| `lst[a:b]` | O(b − a) | copy |

### dict / set

| Operation | Average | Worst |
|-----------|---------|-------|
| `d[k]`, `d[k] = v`, `k in d` | O(1) | O(n) |
| `del d[k]` | O(1) | O(n) |
| `s & t` (intersection) | O(min(s, t)) | — |

### deque and heapq

| Structure | Operation | Complexity |
|-----------|-----------|-----------|
| `deque` | `append` / `appendleft` / `pop` / `popleft` | O(1) |
| `deque` | `d[i]` (random access) | O(n) |
| `heapq` | `heappush` / `heappop` | O(log n) |
| `heapq` | `heapify` | O(n) |

## Interview reflexes

- **"Find duplicates"** → `set`, O(n)
- **"Count occurrences"** → `Counter`, O(n) build + O(1) lookup
- **"Group by key"** → `defaultdict(list)`, O(n)
- **"Is X in collection?"** → `set` or dict key, O(1)
- **"Repeated minimum"** → `heapq`, O(log n) per pop
- **"Search in sorted data"** → `bisect`, O(log n)

!!! tip "The one reflex that covers most interview questions"
    If you see `x in list` inside a loop, replace the list with a set. That single change drops O(n²) to O(n) and answers "can you improve this?" in every case.

## See also

- [sets.md](../../python/language/objects/sets.md) — set operations and O(1) membership in detail
- [hash.md](../../python/language/objects/hash.md) — `__hash__` contract, why mutability breaks dicts
- [queues.md](queues.md) — deque and heapq API in full
