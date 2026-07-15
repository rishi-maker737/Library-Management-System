"""merge_sort: O(n log n) stable sort.
binary_search: O(log n) lookup in a list already sorted by the same key.

Both take an optional `key` function so they work directly on Book
objects (sorting/searching by .title) as well as plain values.
"""


def merge_sort(items: list, key=lambda x: x) -> list:
    if len(items) <= 1:
        return list(items)
    mid = len(items) // 2
    left = merge_sort(items[:mid], key)
    right = merge_sort(items[mid:], key)
    return _merge(left, right, key)


def _merge(left: list, right: list, key) -> list:
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


def binary_search(sorted_items: list, target, key=lambda x: x) -> int:
    """Returns the index of the first item whose key == target, or -1."""
    lo, hi = 0, len(sorted_items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        val = key(sorted_items[mid])
        if val == target:
            return mid
        elif val < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
