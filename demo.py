import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from services.library_service import LibraryService


def line(title=""):
    print("\n" + "=" * 60)
    if title:
        print(title)
        print("=" * 60)


def main():
    svc = LibraryService()

    line("1) Seeding catalog (HashMap + AVL Tree + Trie)")
    books = [
        ("978-0", "Clean Code", "Robert C. Martin", 2),
        ("978-1", "The Pragmatic Programmer", "Andrew Hunt", 1),
        ("978-2", "Clean Architecture", "Robert C. Martin", 1),
        ("978-3", "Introduction to Algorithms", "Cormen", 2),
        ("978-4", "Cracking the Coding Interview", "Gayle McDowell", 1),
    ]
    for isbn, title, author, copies in books:
        svc.add_book(isbn, title, author, copies)
    print(f"Added {len(books)} books.")

    line("2) Sorted catalog (AVL in-order traversal, O(n))")
    for b in svc.browse_catalog_sorted():
        print(f"  {b.title!r} by {b.author}")

    line("3) Autocomplete search (Trie, O(k))")
    print("Prefix 'Clean' ->", [b.title for b in svc.autocomplete("Clean")])
    print("Prefix 'Robert' ->", [b.title for b in svc.autocomplete("Robert")])

    line("4) Register users")
    svc.register_user("u1", "Asha")
    svc.register_user("u2", "Rohit")
    svc.register_user("u3", "Meera")
    print("Registered u1=Asha, u2=Rohit, u3=Meera")

    line("5) Borrow / waitlist (HashMap lookups + Queue for overflow)")
    print(svc.borrow_book("978-1", "u1"))  # only 1 copy -> succeeds
    print(svc.borrow_book("978-1", "u2"))  # no copies left -> waitlisted
    print(svc.borrow_book("978-0", "u1"))
    print(svc.borrow_book("978-2", "u1"))

    line("5b) Double-borrow guard (bugfix regression check)")
    print(svc.borrow_book("978-0", "u1"))  # u1 already has this -> should be refused

    line("6) Recommendations (Graph + BFS on co-borrow history)")
    recs = svc.recommend_for_book("978-1", top_n=3)
    for book, weight in recs:
        print(f"  Because you borrowed 'The Pragmatic Programmer' -> {book.title} (score {weight:.2f})")

    line("7) Recently viewed (Doubly Linked List / LRU, O(1) evict)")
    print("Asha's recently viewed:", [b.title for b in svc.recently_viewed_books("u1")])

    line("8) Return book -> auto-assign to waitlist (Queue FIFO)")
    print(svc.return_book("978-1", "u1"))

    line("9) Due-soonest dashboard (Min-Heap, O(log n) push)")
    for due, isbn, uid in svc.due_soonest(5):
        print(f"  Due {due} -> ISBN {isbn}, user {uid}")

    line("10) Most-borrowed leaderboard (Max-Heap via negation)")
    for b in svc.most_borrowed(3):
        print(f"  {b.title} — borrowed {b.borrow_count}x")

    line("11) Admin undo (Stack, LIFO)")
    svc.add_book("978-9", "Temp Draft Book", "Nobody", 1)
    print("Added a temp book by mistake.")
    print(svc.undo_last_action())
    print("Still in catalog?", svc.get_book("978-9") is not None)

    line("11b) Undo safety guard (bugfix regression check)")
    svc.add_book("978-8", "Another Temp Book", "Nobody", 1)
    svc.borrow_book("978-8", "u3")  # now has an active loan
    print(svc.undo_last_action())   # should refuse: undo target for 978-8 isn't on top anymore
    print("Still in catalog (978-8)?", svc.get_book("978-8") is not None)

    line("12) Overdue report (simulate future date)")
    future = date.today() + timedelta(days=20)
    overdue = svc.overdue_report(today=future)
    print(f"Overdue loans as of {future}: {len(overdue)}")

    line("13) Save/load persistence round-trip")
    svc.save_to_file("library_data.json")
    svc2 = LibraryService()
    svc2.load_from_file("library_data.json")
    print("Books after reload:", len(svc2.books_by_isbn.values()))
    print("Users after reload:", len(svc2.users_by_id.values()))
    print("Active loans after reload:", len(svc2.active_loans.values()))

    line("Demo complete.")


if __name__ == "__main__":
    main()
