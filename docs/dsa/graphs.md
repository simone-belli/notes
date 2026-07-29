---
quiz: core
---

# Graphs

A graph G = (V, E) is a set of vertices V connected by edges E. Unlike trees, graphs can have cycles and disconnected components.

## Representations

### Adjacency list — `dict[int, list[int]]`

```python
graph = {
    0: [1, 2],
    1: [0, 3],
    2: [0],
    3: [1],
}
```

- Storage: O(V + E) — only existing edges stored.
- Edge lookup: O(degree(v)).
- **Use for sparse graphs** (default choice).

### Adjacency matrix — `list[list[int]]`

```python
matrix = [
    [0, 1, 1, 0],
    [1, 0, 0, 1],
    [1, 0, 0, 0],
    [0, 1, 0, 0],
]
```

- Storage: O(V²) — all pairs, regardless of edge count.
- Edge lookup: O(1) — `matrix[u][v]`.
- **Use for dense graphs** or when O(1) edge checks are needed (e.g. Floyd-Warshall).

---

## BFS — Breadth-First Search

Explores level by level. Uses a `deque` as a FIFO (First In, First Out) queue. Natural for **shortest path** in unweighted graphs.

```python
from collections import deque

def bfs(graph: dict[int, list[int]], start: int) -> list[int]:
    visited = {start}       # mark before enqueuing to prevent duplicates
    queue = deque([start])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nbr in graph[node]:
            if nbr not in visited:
                visited.add(nbr)
                queue.append(nbr)
    return order
```

Shortest path variant — carry distance in the queue:

```python
def bfs_shortest(graph, start, end):
    visited = {start}
    queue = deque([(start, 0)])
    while queue:
        node, dist = queue.popleft()
        if node == end:
            return dist
        for nbr in graph[node]:
            if nbr not in visited:
                visited.add(nbr)
                queue.append((nbr, dist + 1))
    return -1
```

---

## DFS — Depth-First Search

Explores one path fully before backtracking. Natural for **connected components, cycle detection, topological sort**.

### Iterative (explicit stack)

```python
def dfs(graph: dict[int, list[int]], start: int) -> list[int]:
    visited = set()
    stack = [start]
    order = []
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        order.append(node)
        for nbr in graph[node]:
            if nbr not in visited:
                stack.append(nbr)
    return order
```

!!! warning "Mark visited after popping, not before pushing"
    A node can appear in the stack multiple times before being processed. The `if node in visited: continue` guard handles this. BFS marks before enqueuing (safe because each node appears at most once per level); iterative DFS marks after popping.

### Topological sort

A **topological sort** orders the vertices of a directed acyclic graph (DAG) so that every edge `u -> v` has `u` before `v` — e.g. course prerequisites, build/package dependencies, spreadsheet recalculation order. It only exists for DAGs: a cycle would force some node to come both before and after another, which is impossible. The order is generally not unique.

**DFS post-order** — a node is appended *after* all its descendants are processed; reversing gives dependency order.

```python
def topo_sort_dfs(graph: dict[int, list[int]]) -> list[int]:
    visited, order = set(), []
    def dfs(node):
        visited.add(node)
        for nbr in graph[node]:
            if nbr not in visited:
                dfs(nbr)
        order.append(node)          # post-order: after all descendants
    for node in graph:
        if node not in visited:
            dfs(node)
    return order[::-1]              # reverse post-order = topological order
```

!!! warning "This DFS version doesn't detect cycles"
    With a plain `visited` set, a cyclic input still terminates but silently returns a wrong order. Detecting cycles needs three-state marking (white/gray/black) so a "back edge" to a node still on the recursion stack (gray) raises an error — see [complexity.md](complexity.md) for time/space tradeoffs of extra bookkeeping like this.

**Kahn's algorithm** (BFS-based) — repeatedly remove nodes with in-degree 0 (no remaining unprocessed prerequisites), decrementing the in-degree of their neighbors as they go:

```python
from collections import deque

def topo_sort_kahn(graph: dict[int, list[int]]) -> list[int]:
    in_degree = {node: 0 for node in graph}
    for node in graph:
        for nbr in graph[node]:
            in_degree[nbr] += 1

    queue = deque(n for n, deg in in_degree.items() if deg == 0)
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nbr in graph[node]:
            in_degree[nbr] -= 1
            if in_degree[nbr] == 0:
                queue.append(nbr)

    if len(order) != len(graph):
        raise ValueError("cycle detected")   # some nodes never reached in-degree 0
    return order
```

!!! tip "Kahn's gives cycle detection for free"
    Any node stuck in a cycle always has an unsatisfied prerequisite, so its in-degree never reaches 0 and it never gets enqueued. If `len(order) < len(graph)`, whatever's missing is in (or downstream of) a cycle — no extra state needed, unlike the DFS version above.

Both run in O(V + E). Pick DFS post-order if a DFS traversal already exists in the codebase; pick Kahn's for incremental/streaming scheduling (it naturally processes "ready" nodes in dependency-release order, useful for identifying batches that could run in parallel).

---

## Connected components

```python
def connected_components(graph: dict[int, list[int]]) -> list[list[int]]:
    visited, components = set(), []
    for node in graph:
        if node not in visited:
            component = bfs(graph, node)
            visited.update(component)
            components.append(component)
    return components
```

---

## BFS vs DFS

| | BFS | DFS |
|--|-----|-----|
| Data structure | `deque` (FIFO) | stack / recursion (LIFO) |
| Explores | level by level | one full path first |
| Shortest path (unweighted) | ✓ | ✗ |
| Topological sort | Kahn's algo (above) | post-order (above) |
| Space worst case | O(V) wide level | O(V) deep path |

## Complexity

| | Adjacency list | Adjacency matrix |
|--|---------------|-----------------|
| Storage | O(V + E) | O(V²) |
| BFS / DFS | O(V + E) | O(V²) |
| Edge exists? | O(degree) | O(1) |

## See also

- [queues.md](queues.md) — `deque` mechanics underlying BFS
- [trees.md](trees.md) — trees are acyclic connected graphs; DFS traversal patterns carry over
- [complexity.md](complexity.md) — storage and traversal costs
