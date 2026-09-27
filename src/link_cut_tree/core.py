"""Splay-tree-based link-cut forest.

Implements the data structure of Sleator and Tarjan (1985), "Self-adjusting
binary search trees", as specialised for dynamic-tree problems. Each node in
the represented forest lives in a splay tree representing one *preferred path*
of the forest; auxiliary splay trees are joined by *path-parent* pointers to
cover the whole forest.

Design decisions
----------------

* **Monoid-valued paths.** Each node carries a user value; the forest reports
  the sum of values along a path. Sum is chosen because it is associative,
  commutative, and has an obvious identity (0), which keeps the aggregation
  logic in ``_pull`` trivial and correct. A general monoid would be more
  flexible but would complicate the API and the tests for little gain here.

* **No automatic root tracking.** ``link(child, parent)`` requires the caller
  to guarantee that ``child`` is currently a root of its represented tree; the
  method checks this and raises ``ValueError`` otherwise. Tracking roots
  implicitly would mean hiding a real error (a cycle) behind a silent fixup.

* **Single value per node.** Values are set at construction and updated via
  ``set_value``. There is no separate edge-weight concept: in a link-cut tree
  the natural unit of aggregation is the node, and modelling edges as separate
  objects doubles the state for no extra power.
"""

from __future__ import annotations


class _Node:
    """A node in the represented forest, doubled as a node in a splay tree.

    Splay-tree roles:
      * ``parent`` is the splay-tree parent (or the path-parent if the node is
        a splay-tree root — we use one field and disambiguate via ``_is_root``).
      * ``left`` / ``right`` are the splay-tree children. In-order order of the
        splay tree corresponds to depth order in the represented path, so
        ``left`` is the shallower end and ``right`` the deeper end.
    """

    __slots__ = (
        "id",
        "value",
        "sum",
        "parent",
        "left",
        "right",
        "rev",
    )

    def __init__(self, node_id, value):
        self.id = node_id
        self.value = value
        # Subtree sum in the splay tree, including this node.
        self.sum = value
        self.parent = None
        self.left = None
        self.right = None
        # Lazy reversal flag for the preferred path.
        self.rev = False


class LinkCutForest:
    """A forest of rooted trees with dynamic link, cut, and path queries.

    Nodes are identified by integer IDs assigned at insertion time. Each node
    carries an integer value (default 0); ``path_sum`` returns the sum of
    values along the unique path between two nodes, or 0 if the nodes are the
    same.

    Example
    -------
    >>> f = LinkCutForest()
    >>> a = f.make_node(10)
    >>> b = f.make_node(20)
    >>> f.link(b, a)
    >>> f.path_sum(a, b)
    30
    """

    def __init__(self):
        self._nodes = {}

    # --- node construction ------------------------------------------------

    def make_node(self, value=0):
        """Create a new isolated node and return its integer ID.

        ``value`` must be an integer (or anything that supports addition with
        itself and with 0). The ID is ``len(nodes)``, so IDs are dense and
        stable for the life of the forest.
        """
        node_id = len(self._nodes)
        self._nodes[node_id] = _Node(node_id, value)
        return node_id

    # --- accessors --------------------------------------------------------

    def get_value(self, node_id):
        """Return the value stored at ``node_id``."""
        return self._nodes[node_id].value

    def set_value(self, node_id, value):
        """Set the value at ``node_id`` and propagate the change into path sums."""
        node = self._nodes[node_id]
        node.value = value
        # Re-splay this node to the root of its auxiliary tree so the new
        # value flows up through _pull correctly.
        self._splay(node)

    # --- splay-tree internals ---------------------------------------------

    @staticmethod
    def _is_root(node):
        # A splay-tree root either has no parent or its parent points back to
        # it via a path-parent edge (recognised by the parent not having this
        # node as a splay child).
        p = node.parent
        if p is None:
            return True
        return p.left is not node and p.right is not node

    @staticmethod
    def _pull(node):
        if node is None:
            return
        s = node.value
        if node.left is not None:
            s += node.left.sum
        if node.right is not None:
            s += node.right.sum
        node.sum = s

    @staticmethod
    def _push(node):
        if node is None or not node.rev:
            return
        node.left, node.right = node.right, node.left
        if node.left is not None:
            node.left.rev ^= True
        if node.right is not None:
            node.right.rev ^= True
        node.rev = False

    def _rotate(self, node):
        parent = node.parent
        gparent = parent.parent
        # Push down before rewiring so lazy flags are settled on the path.
        self._push(parent)
        self._push(node)
        if parent.left is node:
            # Right rotation: node comes up, parent goes down to the right.
            parent.left = node.right
            if node.right is not None:
                node.right.parent = parent
            node.right = parent
        else:
            parent.right = node.left
            if node.left is not None:
                node.left.parent = parent
            node.left = parent
        parent.parent = node
        # Reattach to gparent. If parent was a splay root, the gparent link is
        # actually a path-parent pointer and we keep it on node.
        node.parent = gparent
        if gparent is not None and not LinkCutForest._is_root(parent):
            if gparent.left is parent:
                gparent.left = node
            else:
                gparent.right = node
        self._pull(parent)
        self._pull(node)

    def _splay(self, node):
        # Standard zig/zig-zag splay, but we must push down ancestors first so
        # lazy reversals are applied along the whole access path.
        # Collect ancestors to push them top-down.
        stack = [node]
        cur = node
        while not self._is_root(cur):
            cur = cur.parent
            stack.append(cur)
        while stack:
            self._push(stack.pop())

        while not self._is_root(node):
            parent = node.parent
            gparent = parent.parent
            if not self._is_root(parent):
                # zig-zig or zig-zag
                if (gparent.left is parent) == (parent.left is node):
                    # zig-zig: rotate parent first
                    self._rotate(parent)
                else:
                    self._rotate(node)
                self._rotate(node)
            else:
                # zig
                self._rotate(node)

    # --- link-cut operations ----------------------------------------------

    def _access(self, node):
        """Make ``node`` the deep end of its preferred path and splay it to root.

        After ``_access(node)``, the splay tree rooted at ``node`` represents
        the path from the root of ``node``'s represented tree down to ``node``.
        Returns the previous shallow-end splay root (for ``lca`` use).
        """
        self._splay(node)
        # Detach the deeper subtree: it becomes its own preferred path.
        if node.right is not None:
            node.right.parent = node  # becomes path-parent
            node.right = None
            self._pull(node)
        last = None
        cur = node
        while cur.parent is not None:
            # cur is a splay root; cur.parent is a path-parent pointer.
            nxt = cur.parent
            self._splay(nxt)
            if nxt.right is not None:
                nxt.right.parent = nxt
            nxt.right = cur
            self._pull(nxt)
            cur.parent = nxt
            last = nxt
            cur = nxt
        self._splay(node)
        return last

    def _make_root(self, node):
        """Reroot the represented tree so that ``node`` is its root."""
        self._access(node)
        # The path from old root to node is now in one splay tree with node at
        # the deep end; reversing the splay tree makes node the shallow end,
        # i.e. the root of the represented tree.
        node.rev ^= True
        self._push(node)

    def find_root(self, node_id):
        """Return the ID of the root of ``node_id``'s represented tree."""
        node = self._nodes[node_id]
        self._access(node)
        # Walk down the left spine (shallow end) to find the represented root.
        cur = node
        while True:
            self._push(cur)
            if cur.left is None:
                break
            cur = cur.left
        self._splay(cur)
        return cur.id

    def link(self, child_id, parent_id):
        """Attach ``child_id`` as a child of ``parent_id``.

        Raises ``ValueError`` if ``child_id`` is not currently a root of its
        tree, or if the two nodes are already in the same tree (which would
        create a cycle).
        """
        if child_id == parent_id:
            raise ValueError("cannot link a node to itself")
        child = self._nodes[child_id]
        parent = self._nodes[parent_id]
        self._make_root(child)
        # After make_root, child is a root of its represented tree iff its
        # splay tree has no left child (no shallower node on its path).
        if child.left is not None:
            raise ValueError("child is not a root of its tree")
        # Detect a would-be cycle: if parent is reachable from child, linking
        # would create a cycle.
        if self.find_root(parent_id) == child_id:
            raise ValueError("link would create a cycle")
        # Attach child's preferred path below parent. The path-parent pointer
        # is represented by setting child.parent = parent while child remains
        # a splay root (no parent/child splay edge).
        child.parent = parent

    def cut(self, child_id):
        """Detach ``child_id`` from its parent, making it a root.

        Raises ``ValueError`` if ``child_id`` is already a root.
        """
        child = self._nodes[child_id]
        self._make_root(child)
        # After make_root, child is the represented root. If it has a parent
        # in the represented tree, that parent is the right child in the splay
        # tree (deeper end). If there is no right child, child was a root.
        if child.right is None:
            raise ValueError("node is already a root")
        # Detach the right subtree (the rest of the tree below child).
        right = child.right
        child.right = None
        right.parent = None
        self._pull(child)

    def connected(self, a_id, b_id):
        """Return True iff ``a_id`` and ``b_id`` are in the same represented tree."""
        if a_id == b_id:
            return True
        return self.find_root(a_id) == self.find_root(b_id)

    def path_sum(self, a_id, b_id):
        """Return the sum of node values along the path between ``a_id`` and ``b_id``.

        Both endpoints must be in the same tree. The sum includes both
        endpoints. Returns 0 if ``a_id == b_id`` and the node's value is 0
        (i.e. the sum of a single node is its own value).
        """
        if a_id == b_id:
            return self._nodes[a_id].value
        if not self.connected(a_id, b_id):
            raise ValueError("nodes are not connected")
        a = self._nodes[a_id]
        b = self._nodes[b_id]
        self._make_root(a)
        self._access(b)
        # Now b's splay tree is the path a..b, and b is the splay root, so
        # b.sum is the path sum.
        return b.sum
