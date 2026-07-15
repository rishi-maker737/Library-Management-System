# Library Management System

A small library management system built to showcase core data structures
implemented from scratch, wired up behind a service layer with a CLI on top.

## Structure

```
library_project/
├── cli.py                    # argparse-based CLI (main entry point)
├── demo.py                   # scripted walkthrough of every feature
├── core/
│   ├── hashmap.py             # separate-chaining hash table
│   ├── bst.py                 # AVL self-balancing BST (sorted catalog)
│   ├── trie.py                # prefix tree (autocomplete)
│   ├── heap.py                # binary min-heap (due dates, leaderboards)
│   ├── graph.py                # weighted graph + BFS (recommendations)
│   ├── linked_list.py         # Queue, Stack, LRUList (doubly linked list)
│   └── sorting.py             # merge_sort, binary_search
└── services/
    ├── models.py              # Book, User, BorrowRecord
    └── library_service.py     # orchestrates everything above
```

## Quick start

```bash
python3 demo.py          # scripted end-to-end walkthrough
python3 cli.py --help    # interactive usage
```

State is persisted to `library_data.json` between CLI invocations.

### CLI examples

```bash
python3 cli.py add-book 978-0 "Clean Code" "Robert C. Martin" --copies 2
python3 cli.py register u1 Asha
python3 cli.py borrow 978-0 u1
python3 cli.py browse
python3 cli.py search Clean
python3 cli.py recommend 978-1
python3 cli.py due
python3 cli.py top
python3 cli.py return 978-0 u1
python3 cli.py undo
```

## Bugs fixed in `library_service.py`

1. **Double-borrow inventory corruption** — `borrow_book` previously let a
   user borrow a copy of a book they already had checked out. Since
   `active_loans` is keyed by `(isbn, user_id)`, the second borrow silently
   overwrote the first record while `copies_available` was decremented
   twice — a copy could be permanently lost from inventory after a single
   `return_book()` call. Fixed with an explicit "already checked out" guard.

2. **Orphaned loans via undo** — `remove_book` (used internally to undo an
   `add_book`) deleted a book unconditionally, even if it had active loans
   or a waitlist, leaving `active_loans` / `due_heap` referencing an ISBN no
   longer in the catalog. It now applies the same safety checks as
   `delete_book`, and `undo_last_action` reports why the undo was refused
   instead of corrupting state.

3. **Reservation-queue leak** — `remove_book` never cleaned up
   `reservation_queues[isbn]`, unlike `delete_book`. Fixed.

4. **Undo-stack pollution from loading a save file** — `load_from_file`
   rebuilds the catalog by calling the real `add_book()`, which pushes an
   undo entry for every restored book. `undo_last_action()` right after a
   load would undo book #1 of the *restored* library rather than the last
   real admin action before the save. `load_from_file` now clears
   `undo_stack` once the rebuild is done.

All four are covered by regression checks in `demo.py` (sections 5b and 11b).
