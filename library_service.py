import itertools
import json
import os
from datetime import date, timedelta
from typing import List, Optional

from core.hashmap import HashMap
from core.bst import AVLTree
from core.trie import Trie
from core.heap import MinHeap
from core.graph import Graph
from core.linked_list import Queue, Stack, LRUList
from core.sorting import merge_sort, binary_search

from services.models import Book, User, BorrowRecord

LOAN_PERIOD_DAYS = 14
FINE_PER_DAY = 5.0  # currency units


class LibraryService:
    def __init__(self):
        self.books_by_isbn = HashMap()       # isbn -> Book
        self.users_by_id = HashMap()         # user_id -> User
        self.catalog_by_title = AVLTree()    # title -> isbn  (sorted catalog)
        self.title_trie = Trie()             # title/author prefix -> isbn
        self.reservation_queues = HashMap()  # isbn -> Queue of user_id
        self.co_borrow_graph = Graph()       # isbn <-> isbn (weighted)
        self.due_heap = MinHeap()            # (due_date, (isbn, user_id))
        self.undo_stack = Stack()            # admin action log
        self.recently_viewed = HashMap()     # user_id -> LRUList
        self.borrow_history = HashMap()      # user_id -> [isbn, ...] (co-borrow tracking)
        self.active_loans = HashMap()        # (isbn,user_id) -> BorrowRecord
        self._id_counter = itertools.count(1)

    # ---------------- Admin: catalog management ----------------
    def add_book(self, isbn: str, title: str, author: str, copies: int = 1) -> "Book | str":
        isbn, title, author = isbn.strip(), title.strip(), author.strip()
        if not isbn or not title or not author:
            return "ISBN, title, and author are all required."
        if copies < 1:
            return "Copies must be at least 1."
        if self.books_by_isbn.contains(isbn):
            return f"A book with ISBN {isbn} already exists."

        book = Book(isbn=isbn, title=title, author=author,
                     copies_total=copies, copies_available=copies)
        self.books_by_isbn.put(isbn, book)
        # Key by (title, isbn) rather than title alone -- two different books
        # can legitimately share a title, and a title-only key would let the
        # second insert silently overwrite the first in the AVL tree.
        self.catalog_by_title.insert((title, isbn), isbn)
        self.title_trie.insert(title, isbn)
        self.title_trie.insert(author, isbn)
        self.co_borrow_graph.add_node(isbn)
        self.reservation_queues.put(isbn, Queue())
        self.undo_stack.push(("add_book", isbn))
        return book

    def delete_book(self, isbn: str) -> str:
        """Safe delete: refuses if any copy is currently on loan or the
        waitlist is non-empty, so state never goes inconsistent."""
        book = self.books_by_isbn.get(isbn)
        if not book:
            return "Book not found."
        if book.copies_available < book.copies_total:
            return f"Cannot delete '{book.title}': {book.copies_total - book.copies_available} copy(ies) still on loan."
        queue: Queue = self.reservation_queues.get(isbn)
        if queue is not None and len(queue) > 0:
            return f"Cannot delete '{book.title}': {len(queue)} user(s) still waitlisted."

        self.catalog_by_title.delete((book.title, isbn))
        self.title_trie.remove(book.title, isbn)
        self.title_trie.remove(book.author, isbn)
        self.books_by_isbn.remove(isbn)
        self.reservation_queues.remove(isbn)
        self.undo_stack.push(("remove_book", book))
        return f"'{book.title}' deleted."

    def remove_book(self, isbn: str) -> bool:
        """Internal, unconditional-*looking* removal used by undo_last_action.

        BUGFIX: this used to skip the same safety checks delete_book()
        performs, so undoing an old add_book() for a title that had since
        been borrowed would silently delete the book while active_loans /
        due_heap kept referencing an ISBN no longer in the catalog (orphaned
        loans). It also never cleaned up reservation_queues, leaking a
        Queue per removed ISBN. Both are fixed here: we refuse the removal
        (returning False) if the book still has copies checked out or a
        non-empty waitlist, and we clean up reservation_queues just like
        delete_book() does.
        """
        book = self.books_by_isbn.get(isbn)
        if not book:
            return False
        if book.copies_available < book.copies_total:
            return False  # would orphan active loans / due_heap entries
        queue: Queue = self.reservation_queues.get(isbn)
        if queue is not None and len(queue) > 0:
            return False  # would orphan waitlisted users

        self.catalog_by_title.delete((book.title, isbn))
        self.title_trie.remove(book.title, isbn)
        self.title_trie.remove(book.author, isbn)
        self.books_by_isbn.remove(isbn)
        self.reservation_queues.remove(isbn)
        self.undo_stack.push(("remove_book", book))
        return True

    def undo_last_action(self) -> Optional[str]:
        if self.undo_stack.is_empty():
            return None
        action, payload = self.undo_stack.pop()
        if action == "add_book":
            ok = self.remove_book(payload)
            if ok:
                return f"Undid add_book({payload})"
            # BUGFIX: don't silently swallow the action (and don't corrupt
            # state) if the book now has active loans / a waitlist -- put
            # the entry back so it can be retried once it's safe.
            self.undo_stack.push((action, payload))
            return (f"Cannot undo add_book({payload}): the book currently "
                     f"has active loans or a waitlist.")
        if action == "remove_book":
            b: Book = payload
            result = self.add_book(b.isbn, b.title, b.author, b.copies_total)
            return f"Undid remove_book({b.isbn})" if isinstance(result, Book) else str(result)
        return None

    # ---------------- Users ----------------
    def register_user(self, user_id: str, name: str) -> User:
        user = User(user_id=user_id, name=name)
        self.users_by_id.put(user_id, user)
        self.recently_viewed.put(user_id, LRUList(capacity=5))
        self.borrow_history.put(user_id, [])
        return user

    # ---------------- Search ----------------
    def get_book(self, isbn: str) -> Optional[Book]:
        return self.books_by_isbn.get(isbn)

    def autocomplete(self, prefix: str, limit: int = 10) -> List[Book]:
        isbns = self.title_trie.starts_with(prefix, limit)
        return [self.books_by_isbn.get(i) for i in isbns if self.books_by_isbn.get(i)]

    def browse_catalog_sorted(self) -> List[Book]:
        """O(n) in-order traversal -> books sorted by title."""
        return [self.books_by_isbn.get(isbn) for _, isbn in self.catalog_by_title.in_order()]

    def search_exact_title(self, title: str) -> Optional[Book]:
        """Demonstrates merge_sort + binary_search explicitly."""
        all_books = list(self.books_by_isbn.values())
        sorted_books = merge_sort(all_books, key=lambda b: b.title)
        idx = binary_search(sorted_books, title, key=lambda b: b.title)
        return sorted_books[idx] if idx != -1 else None

    def search_keyword(self, keyword: str) -> List[Book]:
        """Substring match across ISBN/title/author. Unlike autocomplete()
        (Trie, prefix-only, O(k)) this is a linear O(n) scan -- there's no
        efficient general-purpose structure for arbitrary substring search
        without a suffix tree/array, which is overkill for a catalog this
        size. Included because "contains" search is a genuinely different,
        useful mode that prefix search can't cover (e.g. searching by a
        word in the middle of a title)."""
        keyword = keyword.lower().strip()
        if not keyword:
            return []
        return [
            book for book in self.books_by_isbn.values()
            if keyword in book.isbn.lower()
            or keyword in book.title.lower()
            or keyword in book.author.lower()
        ]

    # ---------------- Borrow / return ----------------
    def borrow_book(self, isbn: str, user_id: str, today: date = None) -> str:
        today = today or date.today()
        book = self.books_by_isbn.get(isbn)
        user = self.users_by_id.get(user_id)
        if not book or not user:
            return "Book or user not found."

        self._track_view(user_id, isbn)

        # BUGFIX: without this guard, calling borrow_book() twice for the
        # same (isbn, user_id) -- while copies remain -- decrements
        # copies_available twice and increments borrow_count twice, but
        # active_loans is keyed by (isbn, user_id) so the second
        # BorrowRecord silently overwrites the first. A single later
        # return_book() call only restores +1 copy for a -2 that happened,
        # permanently losing a copy from inventory.
        if self.active_loans.get((isbn, user_id)):
            return f"{user.name} already has '{book.title}' checked out."

        if book.copies_available <= 0:
            queue: Queue = self.reservation_queues.get(isbn)
            if user_id in queue.to_list():
                position = queue.to_list().index(user_id) + 1
                return f"{user.name} is already on the waitlist (position {position})."
            queue.enqueue(user_id)
            return f"No copies available. {user.name} added to waitlist (position {len(queue)})."

        book.copies_available -= 1
        book.borrow_count += 1
        due = today + timedelta(days=LOAN_PERIOD_DAYS)
        record = BorrowRecord(isbn=isbn, user_id=user_id, borrow_date=today, due_date=due)
        self.active_loans.put((isbn, user_id), record)
        self.due_heap.push(due, (isbn, user_id))
        self._record_co_borrow(user_id, isbn)
        return f"{user.name} borrowed '{book.title}'. Due {due.isoformat()}."

    def return_book(self, isbn: str, user_id: str, today: date = None) -> str:
        today = today or date.today()
        record: BorrowRecord = self.active_loans.get((isbn, user_id))
        book = self.books_by_isbn.get(isbn)
        if not record or not book:
            return "No active loan found."

        record.return_date = today
        if today > record.due_date:
            days_late = (today - record.due_date).days
            record.fine = days_late * FINE_PER_DAY

        self.active_loans.remove((isbn, user_id))
        book.copies_available += 1

        queue: Queue = self.reservation_queues.get(isbn)
        msg = f"'{book.title}' returned."
        if record.fine:
            msg += f" Fine: {record.fine:.2f}."
        if queue is not None and len(queue) > 0:
            next_user_id = queue.dequeue()
            self.borrow_book(isbn, next_user_id, today)
            msg += f" Auto-assigned to next waitlisted user {next_user_id}."
        return msg

    def _record_co_borrow(self, user_id: str, isbn: str) -> None:
        """Whenever a user borrows a book, link it to other books they've
        borrowed before -> feeds the recommendation graph."""
        history: list = self.borrow_history.get(user_id) or []
        for prev_isbn in history:
            if prev_isbn != isbn:
                self.co_borrow_graph.add_edge(prev_isbn, isbn)
        history.append(isbn)
        self.borrow_history.put(user_id, history)

    def _track_view(self, user_id: str, isbn: str) -> None:
        lru: LRUList = self.recently_viewed.get(user_id)
        if lru is not None:
            lru.add_front(isbn)

    # ---------------- Recommendations ----------------
    def recommend_for_book(self, isbn: str, top_n: int = 5):
        ranked = self.co_borrow_graph.recommend(isbn, top_n)
        return [(self.books_by_isbn.get(i), weight) for i, weight in ranked]

    def recently_viewed_books(self, user_id: str) -> List[Book]:
        lru: LRUList = self.recently_viewed.get(user_id)
        if lru is None:
            return []
        return [self.books_by_isbn.get(i) for i in lru.to_list()]

    # ---------------- Dashboards ----------------
    def due_soonest(self, n: int = 5):
        """Non-destructive peek at the n soonest-due *active* loans.

        The heap uses lazy deletion: entries aren't removed when a book
        is returned early (that would need an O(n) heap search), they're
        simply skipped here by checking against the live loan table.
        Stale entries are also dropped from the heap as we pass them so
        it doesn't grow unbounded across many borrow/return cycles.
        """
        snapshot = self.due_heap.to_sorted_list()
        fresh, results, seen_loans = [], [], set()
        for due, (isbn, uid) in snapshot:
            record = self.active_loans.get((isbn, uid))
            if record and record.due_date == due:
                if (isbn, uid) in seen_loans:
                    continue  # older duplicate heap entry for the same active loan
                seen_loans.add((isbn, uid))
                fresh.append((due, (isbn, uid)))
                if len(results) < n:
                    results.append((due, isbn, uid))
            # else: stale entry (already returned) -> dropped, not re-pushed

        self.due_heap = MinHeap()
        for due, item in fresh:
            self.due_heap.push(due, item)

        return results

    def most_borrowed(self, n: int = 5) -> List[Book]:
        heap = MinHeap()
        for book in self.books_by_isbn.values():
            heap.push(-book.borrow_count, book)  # negate for max-heap behavior
        top = heap.to_sorted_list()
        return [book for _, book in top[:n]]

    def overdue_report(self, today: date = None) -> List[BorrowRecord]:
        today = today or date.today()
        return [r for r in self.active_loans.values() if r.due_date < today]

    # ---------------- Persistence ----------------
    # Only the raw facts are saved (books, users, active loans, borrow
    # history, waitlists). Everything derived -- the AVL catalog, the
    # Trie, the co-borrow graph, the due-heap -- is rebuilt from those
    # facts on load by replaying the same public methods used at
    # runtime, so there's exactly one code path that builds them and
    # save/load can never drift out of sync with normal operation.

    def to_state(self) -> dict:
        return {
            "books": [
                {
                    "isbn": b.isbn, "title": b.title, "author": b.author,
                    "copies_total": b.copies_total,
                    "copies_available": b.copies_available,
                    "borrow_count": b.borrow_count,
                }
                for b in self.books_by_isbn.values()
            ],
            "users": [
                {"user_id": u.user_id, "name": u.name}
                for u in self.users_by_id.values()
            ],
            "active_loans": [
                {
                    "isbn": r.isbn, "user_id": r.user_id,
                    "borrow_date": r.borrow_date.isoformat(),
                    "due_date": r.due_date.isoformat(),
                }
                for r in self.active_loans.values()
            ],
            "borrow_history": {
                uid: list(self.borrow_history.get(uid) or [])
                for uid in self.users_by_id.keys()
            },
            "reservation_queues": {
                isbn: self.reservation_queues.get(isbn).to_list()
                for isbn in self.books_by_isbn.keys()
                if self.reservation_queues.get(isbn)
            },
            "recently_viewed": {
                uid: (self.recently_viewed.get(uid).to_list()
                      if self.recently_viewed.get(uid) else [])
                for uid in self.users_by_id.keys()
            },
        }

    def save_to_file(self, filename: str = "library_data.json") -> bool:
        try:
            with open(filename, "w") as f:
                json.dump(self.to_state(), f, indent=2)
            return True
        except IOError as e:
            print(f"Unable to save data: {e}")
            return False

    def load_from_file(self, filename: str = "library_data.json") -> bool:
        """Resets in-memory state and rebuilds it from the saved file.
        Returns False (leaving a fresh/empty service) if the file is
        missing or corrupted, matching the JSON version's "start fresh
        on a bad file" behavior rather than crashing."""
        if not os.path.exists(filename):
            return False
        try:
            with open(filename) as f:
                state = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Could not read {filename} ({e}); starting fresh.")
            return False
        if not isinstance(state, dict):
            print(f"{filename} has an unexpected format; starting fresh.")
            return False

        self.__init__()  # reset every structure to empty before rebuilding

        for b in state.get("books", []):
            self.add_book(b["isbn"], b["title"], b["author"], b.get("copies_total", 1))
            book = self.books_by_isbn.get(b["isbn"])
            if book:
                book.copies_available = b.get("copies_available", book.copies_total)
                book.borrow_count = b.get("borrow_count", 0)

        for u in state.get("users", []):
            self.register_user(u["user_id"], u["name"])

        # Replay borrow history through the real method so the co-borrow
        # graph is rebuilt exactly as it would be from live traffic.
        for uid, history in state.get("borrow_history", {}).items():
            for isbn in history:
                if self.books_by_isbn.contains(isbn):
                    self._record_co_borrow(uid, isbn)

        for isbn, waiting in state.get("reservation_queues", {}).items():
            queue = self.reservation_queues.get(isbn)
            if queue is not None:  # NOT "if queue:" -- Queue defines __len__,
                for uid in waiting:  # so an empty-but-real queue is falsy and
                    queue.enqueue(uid)  # would be silently skipped by "if queue:"

        # recently_viewed lists are stored most-recent-first; add_front in
        # reverse so replaying them restores the same order.
        for uid, viewed in state.get("recently_viewed", {}).items():
            lru = self.recently_viewed.get(uid)
            if lru is not None:  # same __len__-truthiness trap as above
                for isbn in reversed(viewed):
                    lru.add_front(isbn)

        for loan in state.get("active_loans", []):
            isbn, uid = loan["isbn"], loan["user_id"]
            if not self.books_by_isbn.contains(isbn) or not self.users_by_id.contains(uid):
                continue
            record = BorrowRecord(
                isbn=isbn, user_id=uid,
                borrow_date=date.fromisoformat(loan["borrow_date"]),
                due_date=date.fromisoformat(loan["due_date"]),
            )
            self.active_loans.put((isbn, uid), record)
            self.due_heap.push(record.due_date, (isbn, uid))

        # BUGFIX: add_book() (called above while rebuilding the catalog)
        # unconditionally pushes an "add_book" entry onto undo_stack for
        # every book restored from the file. Left as-is, calling
        # undo_last_action() right after a load would undo book #1 of the
        # *restored* library instead of whatever the last real admin
        # action was before the file was saved. Loading isn't an
        # undoable admin action, so the load-induced entries are cleared.
        self.undo_stack = Stack()

        return True
