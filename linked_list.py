"""Queue, Stack, and LRUList -- all backed by one internal doubly linked
list so every core operation (push/pop either end, and LRU eviction) is
O(1) with no shifting of other elements.
"""


class _Node:
    __slots__ = ("value", "prev", "next")

    def __init__(self, value):
        self.value = value
        self.prev = None
        self.next = None


class _DoublyLinkedList:
    def __init__(self):
        self.head = None  # front
        self.tail = None  # back
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def push_back(self, value) -> _Node:
        node = _Node(value)
        if self.tail is None:
            self.head = self.tail = node
        else:
            node.prev = self.tail
            self.tail.next = node
            self.tail = node
        self._size += 1
        return node

    def push_front(self, value) -> _Node:
        node = _Node(value)
        if self.head is None:
            self.head = self.tail = node
        else:
            node.next = self.head
            self.head.prev = node
            self.head = node
        self._size += 1
        return node

    def pop_front(self):
        if self.head is None:
            raise IndexError("pop from empty list")
        node = self.head
        self.remove_node(node)
        return node.value

    def pop_back(self):
        if self.tail is None:
            raise IndexError("pop from empty list")
        node = self.tail
        self.remove_node(node)
        return node.value

    def remove_node(self, node: _Node) -> None:
        if node.prev:
            node.prev.next = node.next
        else:
            self.head = node.next
        if node.next:
            node.next.prev = node.prev
        else:
            self.tail = node.prev
        node.prev = node.next = None
        self._size -= 1

    def to_list(self) -> list:
        out = []
        cur = self.head
        while cur:
            out.append(cur.value)
            cur = cur.next
        return out


class Queue:
    """FIFO. enqueue() appends at the back, dequeue() removes from the front."""

    def __init__(self):
        self._dll = _DoublyLinkedList()

    def enqueue(self, value) -> None:
        self._dll.push_back(value)

    def dequeue(self):
        return self._dll.pop_front()

    def to_list(self) -> list:
        return self._dll.to_list()

    def __len__(self) -> int:
        return len(self._dll)


class Stack:
    """LIFO. push()/pop() both operate on the same (back) end."""

    def __init__(self):
        self._dll = _DoublyLinkedList()

    def push(self, value) -> None:
        self._dll.push_back(value)

    def pop(self):
        return self._dll.pop_back()

    def is_empty(self) -> bool:
        return len(self._dll) == 0

    def to_list(self) -> list:
        return self._dll.to_list()

    def __len__(self) -> int:
        return len(self._dll)


class LRUList:
    """Fixed-capacity most-recently-used list. add_front() both records a
    fresh view and moves an already-present value back to the front, in
    O(1), via a value->node index. Oldest entries are evicted from the
    back once capacity is exceeded."""

    def __init__(self, capacity: int = 5):
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._dll = _DoublyLinkedList()
        self._node_map: dict = {}

    def add_front(self, value) -> None:
        existing = self._node_map.get(value)
        if existing is not None:
            self._dll.remove_node(existing)
            del self._node_map[value]

        new_node = self._dll.push_front(value)
        self._node_map[value] = new_node

        while len(self._dll) > self.capacity:
            evicted = self._dll.tail
            self._dll.remove_node(evicted)
            self._node_map.pop(evicted.value, None)

    def to_list(self) -> list:
        return self._dll.to_list()

    def __len__(self) -> int:
        return len(self._dll)
