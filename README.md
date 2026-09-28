# link_cut_tree

A pure-Python link-cut tree: a forest of rooted trees supporting `link`, `cut`, and path-sum queries in O(log n) amortised time per operation.

## Usage

```python
from link_cut_tree import LinkCutForest

f = LinkCutForest()
a = f.make_node(1)
b = f.make_node(2)
c = f.make_node(3)
f.link(b, a)   # b becomes a child of a
f.link(c, b)   # c becomes a child of b
f.path_sum(a, c)  # 6
f.cut(b)           # detach b (and its subtree) from a
f.connected(a, c)  # False
```

## Why

The problem is maintaining aggregate information (here, the sum of node values) over paths in a forest that is being edited — links added, edges cut — between queries. A static tree lets you precompute with a DFS; a dynamic tree does not. Link-cut trees handle arbitrary sequences of link/cut/query without rebuilding.

The trade-off is implementation complexity versus a simpler structure like a heavy-light decomposition. HLD is easier to write but must rebuild on structural change; link-cut trees pay a constant factor in code length to stay fast under edits.

## Edge cases

`link(child, parent)` requires `child` to be a root of its current tree; the method raises `ValueError` otherwise rather than silently rerooting. `cut(child)` likewise requires `child` to have a parent. `path_sum` on two nodes in different trees raises `ValueError`. The sum over a single node is that node's own value.

## Exports

- `LinkCutForest` — the forest class.
  - `make_node(value=0) -> int`
  - `get_value(node_id) -> int`
  - `set_value(node_id, value) -> None`
  - `find_root(node_id) -> int`
  - `link(child_id, parent_id) -> None`
  - `cut(child_id) -> None`
  - `connected(a_id, b_id) -> bool`
  - `path_sum(a_id, b_id) -> int`
