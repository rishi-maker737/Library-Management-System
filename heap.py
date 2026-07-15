"""MinHeap: binary heap keyed by an explicit priority.

Wraps heapq with a monotonically increasing tie-breaker so items that
aren't mutually comparable (e.g. two Book objects, or two (isbn, uid)
tuples with an identical priority) never get compared directly by
heapq when priorities tie.

For a max-heap (e.g. "most borrowed"), callers push the negated
priority -- that's a deliberate, standard trick, not something this
class needs to special-case.
"""

import heapq
import itertools


class MinHeap:
    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, priority, item) -> None:
        heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self):
        """Remove and return the (priority, item) pair with the smallest priority."""
        priority, _, item = heapq.heappop(self._heap)
        return priority, item

    def peek(self):
        if not self._heap:
            return None
        priority, _, item = self._heap[0]
        return priority, item

    def to_sorted_list(self) -> list:
        """Non-destructive: returns all (priority, item) pairs sorted
        ascending by priority, without mutating the heap."""
        return [(priority, item) for priority, _, item in sorted(self._heap)]

    def __len__(self) -> int:
        return len(self._heap)
