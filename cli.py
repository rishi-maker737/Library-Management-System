#!/usr/bin/env python3
"""Command-line interface for LibraryService.

Usage examples:
    python cli.py add-book 978-0 "Clean Code" "Robert C. Martin" --copies 2
    python cli.py register u1 Asha
    python cli.py borrow 978-0 u1
    python cli.py return 978-0 u1
    python cli.py browse
    python cli.py search Clean
    python cli.py recommend 978-1
    python cli.py recent u1
    python cli.py due
    python cli.py top
    python cli.py undo
    python cli.py overdue

State is persisted to library_data.json (in the current directory) between
runs -- every command loads it on startup and saves it before exiting.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from services.library_service import LibraryService

DATA_FILE = "library_data.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="library", description="Library management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add-book", help="Add a new book to the catalog")
    p.add_argument("isbn")
    p.add_argument("title")
    p.add_argument("author")
    p.add_argument("--copies", type=int, default=1)

    p = sub.add_parser("delete-book", help="Remove a book (only if no active loans/waitlist)")
    p.add_argument("isbn")

    p = sub.add_parser("register", help="Register a new user")
    p.add_argument("user_id")
    p.add_argument("name")

    p = sub.add_parser("borrow", help="Borrow a book (or join the waitlist)")
    p.add_argument("isbn")
    p.add_argument("user_id")

    p = sub.add_parser("return", help="Return a book")
    p.add_argument("isbn")
    p.add_argument("user_id")

    p = sub.add_parser("browse", help="List the full catalog, sorted by title")

    p = sub.add_parser("search", help="Autocomplete search by title/author prefix")
    p.add_argument("prefix")
    p.add_argument("--limit", type=int, default=10)

    p = sub.add_parser("find", help="Substring search across isbn/title/author")
    p.add_argument("keyword")

    p = sub.add_parser("recommend", help="Co-borrow recommendations for a book")
    p.add_argument("isbn")
    p.add_argument("--top", type=int, default=5)

    p = sub.add_parser("recent", help="A user's recently viewed books")
    p.add_argument("user_id")

    p = sub.add_parser("due", help="Soonest-due active loans")
    p.add_argument("--n", type=int, default=5)

    p = sub.add_parser("top", help="Most-borrowed books")
    p.add_argument("--n", type=int, default=5)

    p = sub.add_parser("overdue", help="List currently overdue loans")

    p = sub.add_parser("undo", help="Undo the last catalog admin action")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    svc = LibraryService()
    svc.load_from_file(DATA_FILE)

    if args.command == "add-book":
        result = svc.add_book(args.isbn, args.title, args.author, args.copies)
        print(result if isinstance(result, str) else f"Added '{result.title}' ({result.copies_total} copies).")

    elif args.command == "delete-book":
        print(svc.delete_book(args.isbn))

    elif args.command == "register":
        user = svc.register_user(args.user_id, args.name)
        print(f"Registered {user.user_id} = {user.name}")

    elif args.command == "borrow":
        print(svc.borrow_book(args.isbn, args.user_id))

    elif args.command == "return":
        print(svc.return_book(args.isbn, args.user_id))

    elif args.command == "browse":
        for b in svc.browse_catalog_sorted():
            print(f"{b.isbn}  {b.title!r} by {b.author}  ({b.copies_available}/{b.copies_total} available)")

    elif args.command == "search":
        for b in svc.autocomplete(args.prefix, args.limit):
            print(f"{b.isbn}  {b.title!r} by {b.author}")

    elif args.command == "find":
        for b in svc.search_keyword(args.keyword):
            print(f"{b.isbn}  {b.title!r} by {b.author}")

    elif args.command == "recommend":
        book = svc.get_book(args.isbn)
        if not book:
            print("Book not found.")
        else:
            recs = svc.recommend_for_book(args.isbn, args.top)
            if not recs:
                print(f"No recommendations yet for '{book.title}'.")
            for rec_book, weight in recs:
                print(f"  {rec_book.title!r} (score {weight:.2f})")

    elif args.command == "recent":
        books = svc.recently_viewed_books(args.user_id)
        for b in books:
            print(f"{b.isbn}  {b.title!r}")

    elif args.command == "due":
        for due, isbn, uid in svc.due_soonest(args.n):
            book = svc.get_book(isbn)
            title = book.title if book else isbn
            print(f"Due {due}  {title!r}  (user {uid})")

    elif args.command == "top":
        for b in svc.most_borrowed(args.n):
            print(f"{b.title!r} — borrowed {b.borrow_count}x")

    elif args.command == "overdue":
        records = svc.overdue_report()
        for r in records:
            book = svc.get_book(r.isbn)
            title = book.title if book else r.isbn
            print(f"{title!r}  user {r.user_id}  was due {r.due_date}")
        if not records:
            print("No overdue loans.")

    elif args.command == "undo":
        result = svc.undo_last_action()
        print(result if result else "Nothing to undo.")

    svc.save_to_file(DATA_FILE)


if __name__ == "__main__":
    main()
