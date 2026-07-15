"""Trie: prefix tree for O(k) autocomplete, where k = len(prefix).

Each terminal path can carry multiple values (e.g. several books share
an author, so the same trie path accumulates several ISBNs). Matching
is case-insensitive since users don't reliably type exact case.
"""


class _TrieNode:
    __slots__ = ("children", "values")

    def __init__(self):
        self.children = {}
        self.values = set()


class Trie:
    def __init__(self):
        self.root = _TrieNode()

    def insert(self, text: str, value) -> None:
        node = self.root
        for ch in text.lower():
            node = node.children.setdefault(ch, _TrieNode())
        node.values.add(value)

    def remove(self, text: str, value) -> bool:
        """Remove `value` from the node at the end of `text`'s path.
        Leaves the (now possibly empty) path nodes in place -- pruning
        empty branches isn't needed for correctness at this scale."""
        node = self.root
        for ch in text.lower():
            node = node.children.get(ch)
            if node is None:
                return False
        if value in node.values:
            node.values.discard(value)
            return True
        return False

    def starts_with(self, prefix: str, limit: int = 10) -> list:
        node = self.root
        for ch in prefix.lower():
            node = node.children.get(ch)
            if node is None:
                return []
        results: list = []
        seen = set()
        self._collect(node, results, seen, limit)
        return results

    def _collect(self, node, results, seen, limit) -> None:
        if len(results) >= limit:
            return
        for v in node.values:
            if v not in seen:
                seen.add(v)
                results.append(v)
                if len(results) >= limit:
                    return
        for child in node.children.values():
            self._collect(child, results, seen, limit)
            if len(results) >= limit:
                return
