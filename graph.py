"""Graph: undirected, weighted adjacency-map graph.

Used to model which books get co-borrowed together. Every time a user
borrows book B having previously borrowed book A in the same history,
add_edge(A, B) is called, incrementing the edge weight -- so weight is
literally "how many users have borrowed both."

recommend() does a weighted BFS outward from a book: direct co-borrows
score highest, and each additional hop is discounted, so second-degree
connections ("people who borrowed what people who borrowed this also
borrowed") can still surface recommendations when direct co-borrow data
is sparse.
"""

from collections import deque


class Graph:
    def __init__(self):
        self._adj: dict = {}

    def add_node(self, node) -> None:
        self._adj.setdefault(node, {})

    def add_edge(self, a, b, weight: int = 1) -> None:
        self.add_node(a)
        self.add_node(b)
        if a == b:
            return
        self._adj[a][b] = self._adj[a].get(b, 0) + weight
        self._adj[b][a] = self._adj[b].get(a, 0) + weight

    def neighbors(self, node) -> dict:
        return dict(self._adj.get(node, {}))

    def recommend(self, node, top_n: int = 5, decay: float = 0.5) -> list:
        """Weighted BFS from `node`. Returns up to top_n (neighbor, score)
        pairs sorted by score descending. Direct co-borrows use their raw
        edge weight; each further hop is multiplied by `decay`."""
        if node not in self._adj:
            return []

        visited = {node}
        scores: dict = {}
        queue = deque([(node, 1.0)])  # (current_node, decay_multiplier_for_its_edges)

        while queue:
            current, multiplier = queue.popleft()
            for neighbor, weight in self._adj[current].items():
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                scores[neighbor] = weight * multiplier
                queue.append((neighbor, multiplier * decay))

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[:top_n]

    def __len__(self) -> int:
        return len(self._adj)
