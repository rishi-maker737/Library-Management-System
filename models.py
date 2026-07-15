"""Plain data models used throughout the library service."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Book:
    isbn: str
    title: str
    author: str
    copies_total: int
    copies_available: int
    borrow_count: int = 0


@dataclass
class User:
    user_id: str
    name: str


@dataclass
class BorrowRecord:
    isbn: str
    user_id: str
    borrow_date: date
    due_date: date
    return_date: Optional[date] = None
    fine: float = 0.0
