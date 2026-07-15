"""AVLTree: self-balancing BST kept in strict height balance via rotations.

Guarantees O(log n) insert/delete and an O(n) in-order traversal that
yields (key, value) pairs in ascending key order -- used by the library
service to browse the catalog sorted by (title, isbn).
"""


class _AVLNode:
    __slots__ = ("key", "value", "left", "right", "height")

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None
        self.right = None
        self.height = 1


class AVLTree:
    def __init__(self):
        self.root = None
        self._size = 0

    # ---------------- internal helpers ----------------
    def _height(self, node) -> int:
        return node.height if node else 0

    def _update_height(self, node) -> None:
        node.height = 1 + max(self._height(node.left), self._height(node.right))

    def _balance_factor(self, node) -> int:
        return self._height(node.left) - self._height(node.right) if node else 0

    def _rotate_right(self, y):
        x = y.left
        t2 = x.right
        x.right = y
        y.left = t2
        self._update_height(y)
        self._update_height(x)
        return x

    def _rotate_left(self, x):
        y = x.right
        t2 = y.left
        y.left = x
        x.right = t2
        self._update_height(x)
        self._update_height(y)
        return y

    def _rebalance(self, node):
        self._update_height(node)
        balance = self._balance_factor(node)

        if balance > 1 and self._balance_factor(node.left) >= 0:
            return self._rotate_right(node)
        if balance > 1 and self._balance_factor(node.left) < 0:
            node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        if balance < -1 and self._balance_factor(node.right) <= 0:
            return self._rotate_left(node)
        if balance < -1 and self._balance_factor(node.right) > 0:
            node.right = self._rotate_right(node.right)
            return self._rotate_left(node)
        return node

    # ---------------- public API ----------------
    def insert(self, key, value) -> None:
        self.root, inserted = self._insert(self.root, key, value)
        if inserted:
            self._size += 1

    def _insert(self, node, key, value):
        if node is None:
            return _AVLNode(key, value), True
        if key < node.key:
            node.left, inserted = self._insert(node.left, key, value)
        elif key > node.key:
            node.right, inserted = self._insert(node.right, key, value)
        else:
            node.value = value
            return node, False
        return self._rebalance(node), inserted

    def delete(self, key) -> bool:
        self.root, deleted = self._delete(self.root, key)
        if deleted:
            self._size -= 1
        return deleted

    def _delete(self, node, key):
        if node is None:
            return None, False
        if key < node.key:
            node.left, deleted = self._delete(node.left, key)
        elif key > node.key:
            node.right, deleted = self._delete(node.right, key)
        else:
            deleted = True
            if node.left is None:
                return node.right, deleted
            if node.right is None:
                return node.left, deleted
            successor = self._min_node(node.right)
            node.key, node.value = successor.key, successor.value
            node.right, _ = self._delete(node.right, successor.key)
        return self._rebalance(node), deleted

    def _min_node(self, node):
        while node.left:
            node = node.left
        return node

    def get(self, key):
        node = self.root
        while node:
            if key == node.key:
                return node.value
            node = node.left if key < node.key else node.right
        return None

    def in_order(self):
        """Ascending-key traversal -> list of (key, value) pairs."""
        result = []
        self._in_order(self.root, result)
        return result

    def _in_order(self, node, result) -> None:
        if node is None:
            return
        self._in_order(node.left, result)
        result.append((node.key, node.value))
        self._in_order(node.right, result)

    def __len__(self) -> int:
        return self._size
