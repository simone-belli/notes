# deque and heapq

Two stdlib data structures for cases where `list` is the wrong tool.

## deque — double-ended queue

`collections.deque` gives O(1) appends and pops at *both* ends. `list.pop(0)` and `list.insert(0, x)` are O(n) because they shift every element; deque avoids that.

```python
from collections import deque

d = deque([1, 2, 3])
d.append(4)         # right end  → deque([1, 2, 3, 4])
d.appendleft(0)     # left end   → deque([0, 1, 2, 3, 4])
d.pop()             # right      → 4
d.popleft()         # left       → 0
```

**Bounded buffer** — `maxlen` silently drops from the opposite end when full:

```python
last_5 = deque(maxlen=5)
for x in range(10):
    last_5.append(x)
# last_5 → deque([5, 6, 7, 8, 9], maxlen=5)
```

Useful for: sliding windows, BFS queues, keeping the last N items.

!!! warning "deque is not random-access"
    `d[i]` is O(n) — deque is a doubly-linked list of fixed-size blocks, not a contiguous array. Use list when you need fast indexing; use deque when you need fast both-end mutation.

**Use deque when:** you need a FIFO queue (`append` + `popleft`) or sliding window. `list.pop(0)` in a loop is the code smell to replace.

---

## heapq — min-heap / priority queue

`heapq` turns a regular list into a **min-heap**: the smallest element is always at index 0, accessible in O(1). Push and pop maintain the heap invariant in O(log n).

```python
import heapq

h = []
heapq.heappush(h, 3)
heapq.heappush(h, 1)
heapq.heappush(h, 2)

heapq.heappop(h)    # → 1  (always the minimum)
heapq.heappop(h)    # → 2
h[0]                # peek at minimum without popping — O(1)
```

**heapify** — convert an existing list in-place in O(n):

```python
lst = [5, 3, 8, 1, 2]
heapq.heapify(lst)   # lst is now a valid heap in-place
```

**nlargest / nsmallest** — more efficient than full sort when k << n:

```python
heapq.nlargest(3, lst)    # O(n log k) — faster than sorted()[-3:] when k is small
heapq.nsmallest(3, lst)
```

Use `key=` to rank objects by an attribute:

```python
from operator import attrgetter

top3 = heapq.nlargest(3, trades, key=attrgetter("notional"))
# equivalent: key=lambda t: t.notional
```

`attrgetter` is a compiled accessor — faster than lambda on large inputs and reads more clearly. Prefer it over `lambda` when selecting a single attribute.

Why `nlargest` beats `sorted()` when k is small: `sorted()` is O(n log n);
`nlargest(k, ...)` maintains a min-heap of size k while scanning → O(n log k).
At n=1,000,000 and k=3 that's ~3M comparisons vs ~20M. Breakeven is roughly k > n/log(n); below that, always prefer `nlargest`/`nsmallest`.

### Priority queue pattern

Tuples are compared element by element, so put priority first:

```python
tasks = []
heapq.heappush(tasks, (2, "medium task"))
heapq.heappush(tasks, (1, "urgent task"))
heapq.heappush(tasks, (3, "low task"))

priority, task = heapq.heappop(tasks)   # → (1, "urgent task")
```

**Max-heap workaround** — negate priorities (heapq only provides min-heap):

```python
heapq.heappush(h, -value)
max_val = -heapq.heappop(h)
```

**Use heapq when:** you need the minimum (or maximum) repeatedly and the collection is changing — e.g. Dijkstra's algorithm, task schedulers, merge of sorted streams. For a one-time min/max, `min()` / `max()` (O(n)) is simpler.

---

## Complexity summary

| Structure | Operation | Complexity |
|-----------|-----------|-----------|
| `deque` | `append` / `appendleft` / `pop` / `popleft` | O(1) |
| `deque` | `d[i]` (index) | O(n) |
| `heapq` | `heappush` / `heappop` | O(log n) |
| `heapq` | `heapify` | O(n) |
| `heapq` | `h[0]` (peek min) | O(1) |

## See also

- [complexity.md](complexity.md) — full Big-O table for all built-in structures
- [trees.md](trees.md) — `deque` for BFS; `heapq` for tree-path problems
- [sets.md](../python/language/objects/sets.md) — O(1) membership, set operations
