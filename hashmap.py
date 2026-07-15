"""HashMap: separate-chaining hash table with automatic resizing.

O(1) average-case put/get/remove/contains. Keys must be hashable
(strings, ints, tuples of hashable values, etc -- exactly what the
library service needs: ISBNs, user IDs, and (isbn, user_id) pairs).
"""

_LOAD_FACTOR_THRESHOLD = 0.75


class HashMap:
    def __init__(self, capacity: int = 16):
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._size = 0
        self._buckets = [[] for _ in range(capacity)]

    def _hash(self, key) -> int:
        return hash(key) % self._capacity

    def put(self, key, value) -> None:
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self._size += 1
        if self._size / self._capacity > _LOAD_FACTOR_THRESHOLD:
            self._resize()

    def get(self, key, default=None):
        idx = self._hash(key)
        for k, v in self._buckets[idx]:
            if k == key:
                return v
        return default

    def contains(self, key) -> bool:
        idx = self._hash(key)
        return any(k == key for k, _ in self._buckets[idx])

    def remove(self, key) -> bool:
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                del bucket[i]
                self._size -= 1
                return True
        return False

    def keys(self):
        return [k for bucket in self._buckets for k, _ in bucket]

    def values(self):
        return [v for bucket in self._buckets for _, v in bucket]

    def items(self):
        return [(k, v) for bucket in self._buckets for k, v in bucket]

    def _resize(self) -> None:
        old_items = self.items()
        self._capacity *= 2
        self._buckets = [[] for _ in range(self._capacity)]
        self._size = 0
        for k, v in old_items:
            self.put(k, v)

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key) -> bool:
        return self.contains(key)

    def __repr__(self) -> str:
        return f"HashMap({dict(self.items())!r})"
