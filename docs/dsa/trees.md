# Binary Trees

## TreeNode

```python
from __future__ import annotations
from typing import Optional

class TreeNode:
    def __init__(self, val: int = 0,
                 left: Optional[TreeNode] = None,
                 right: Optional[TreeNode] = None):
        self.val   = val
        self.left  = left
        self.right = right
```

## Traversal orders

```
        4
       / \
      2   6       inorder   (L → root → R):  1 2 3 4 5 6 7
     / \ / \      preorder  (root → L → R):  4 2 1 3 6 5 7
    1  3 5  7     postorder (L → R → root):  1 3 2 5 7 6 4
```

| Order | When root is visited | Use for |
|-------|----------------------|---------|
| Inorder | between subtrees | sorted output on BST, kth smallest |
| Preorder | before subtrees | serialisation, copying |
| Postorder | after subtrees | deletion, expression tree eval |

---

## Inorder — recursive

```python
def inorder(node: Optional[TreeNode], result: list[int] | None = None) -> list[int]:
    if result is None:
        result = []
    if node:
        inorder(node.left, result)
        result.append(node.val)
        inorder(node.right, result)
    return result
```

## Inorder — iterative with explicit stack

The form asked for in interviews. Push nodes leftward; pop when left is exhausted; then go right.

```python
def inorder_iterative(root: Optional[TreeNode]) -> list[int]:
    result, stack = [], []
    curr = root
    while curr or stack:
        while curr:              # descend left, stacking every node
            stack.append(curr)
            curr = curr.left
        curr = stack.pop()       # left exhausted — visit this node
        result.append(curr.val)
        curr = curr.right        # move to right subtree
    return result
```

!!! tip "Loop invariant"
    At the top of the outer `while`, `curr` is either an unvisited node or `None` (left branch just finished). The inner `while` pushes the whole left spine; then we process the top and descend right.

---

## Preorder — recursive and iterative

```python
def preorder(node, result=None):
    if result is None: result = []
    if node:
        result.append(node.val)
        preorder(node.left, result)
        preorder(node.right, result)
    return result

def preorder_iterative(root):
    if not root: return []
    result, stack = [], [root]
    while stack:
        node = stack.pop()
        result.append(node.val)
        if node.right: stack.append(node.right)  # right first — popped second
        if node.left:  stack.append(node.left)   # left second — popped first
    return result
```

## Postorder — recursive and iterative

```python
def postorder(node, result=None):
    if result is None: result = []
    if node:
        postorder(node.left, result)
        postorder(node.right, result)
        result.append(node.val)
    return result

def postorder_iterative(root):
    if not root: return []
    result, stack = [], [root]
    while stack:
        node = stack.pop()
        result.append(node.val)
        if node.left:  stack.append(node.left)
        if node.right: stack.append(node.right)
    return result[::-1]          # collected root→right→left; reverse gives L→R→root
```

---

## BST validation

Inorder of a valid BST is always sorted. Validate by threading a valid range through recursion:

```python
def is_valid_bst(node, lo=float('-inf'), hi=float('inf')) -> bool:
    if not node:
        return True
    if not (lo < node.val < hi):
        return False
    return (is_valid_bst(node.left,  lo,       node.val) and
            is_valid_bst(node.right, node.val, hi))
```

---

## Problem → traversal map

| Problem | Approach |
|---------|---------|
| BST values in sorted order | Inorder |
| kth smallest in BST | Inorder, stop at kth |
| Validate BST | Recursive range check (above) |
| Copy / serialise tree | Preorder |
| Subtree height / size | Postorder |
| Delete tree | Postorder |
| Evaluate expression tree | Postorder |
| Level-order / BFS | `collections.deque`, not DFS |

## See also

- [queues.md](queues.md) — `deque` for BFS; `heapq` for priority-queue tree problems
- [complexity.md](complexity.md) — traversal is O(n) time, O(h) space (h = tree height)
