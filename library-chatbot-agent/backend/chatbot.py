"""College Library Chatbot.

A small rule-based assistant over a fixed book catalog. Supports lookups,
recommendations, comparisons, fuzzy title matching, and a lightweight
borrow / return simulation that actually mutates stock counts.

The module can be imported for testing or run directly as a CLI app.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional


@dataclass
class Book:
    author: str
    genre: str
    year: int
    available: int
    total: int
    borrow_days: int
    summary: str
    resources: str
    shelf: str
    price_inr: int
    waitlist: list[str] = field(default_factory=list)


def _catalog() -> dict[str, Book]:
    return {
        "atomic habits": Book(
            "James Clear", "Self-help", 2018, 2, 3, 14,
            "A book about building good habits and breaking bad habits through small changes.",
            "Book summary, habit-building guide, and author information.",
            "A-12", 499,
        ),
        "the alchemist": Book(
            "Paulo Coelho", "Fiction", 1988, 1, 2, 14,
            "A story about following your dreams and discovering your purpose.",
            "Book summary, author biography, and discussion guide.",
            "B-04", 299,
        ),
        "clean code": Book(
            "Robert C. Martin", "Programming", 2008, 1, 2, 21,
            "A guide to writing clean, readable, and maintainable software.",
            "Programming notes, clean-code principles, and related resources.",
            "D-15", 699,
        ),
        "1984": Book(
            "George Orwell", "Dystopian Fiction", 1949, 3, 3, 14,
            "A dystopian novel about surveillance, government control, and individual freedom.",
            "Book summary, author information, and discussion questions.",
            "B-11", 199,
        ),
        "rich dad poor dad": Book(
            "Robert Kiyosaki", "Finance", 1997, 2, 3, 14,
            "A personal finance book discussing financial education and investing.",
            "Personal finance guide and book summary.",
            "C-12", 299,
        ),
    }


GENRE_ALIASES = {
    "coding": "programming", "programming": "programming",
    "money": "finance", "finance": "finance", "history": "history",
    "fiction": "fiction", "self-help": "self-help", "habits": "self-help",
    "personal growth": "self-help",
}


def normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def books_by_genre(genre: str, catalog: dict[str, Book]) -> list[str]:
    """Return titles in a requested genre, accepting common topic aliases."""
    normalized_genre = normalize(genre)
    requested_genre = GENRE_ALIASES.get(normalized_genre, normalized_genre)
    return [
        title for title, book in catalog.items()
        if book.genre.lower() == requested_genre
        or (requested_genre == "fiction" and "fiction" in book.genre.lower())
    ]


class LibraryChatbot:
    """Answers catalog questions, remembers the last mentioned title, and
    simulates borrowing/returning books."""

    def __init__(self, catalog: Optional[dict[str, Book]] = None) -> None:
        self.books = catalog if catalog is not None else _catalog()
        self.last_book: Optional[str] = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def reply(self, user_message: str) -> str:
        message = normalize(user_message)
        if not message:
            return "Please enter a question about the library."

        titles = self._mentioned_titles(message)
        if titles:
            self.last_book = titles[0]

        if message in {"hi", "hello", "hey", "hii", "hiii"}:
            return (
                "Hello! I'm your College Library Assistant. Ask about books, "
                "availability, copies, cost, recommendations, authors, "
                "summaries, or borrowing periods. Type 'help' to see everything I can do."
            )
        if message in {"exit", "quit", "bye", "goodbye"}:
            return "Goodbye! Happy reading!"
        if message == "help":
            return self._help()
        if self._is_all_books_request(message):
            return self._all_books()
        if "how many books" in message or "how many titles" in message:
            return f"The catalog currently contains {len(self.books)} titles."
        if self._is_available_books_request(message):
            return self._available_books()
        if self._is_price_list_request(message):
            return self._price_list()
        if self._is_recommendation_request(message):
            return self._recommend(message)
        if message.startswith("borrow") or message.startswith("i want to borrow"):
            return self._borrow(message, titles)
        if message.startswith("return"):
            return self._return(message, titles)
        if "renew" in message:
            return "A book can be renewed once if nobody else has reserved it."
        if "late" in message or "fine" in message:
            return "Late returns may result in a temporary borrowing restriction."
        if any(word in message for word in ("opening", "hours", "timing")):
            return (
                "Library hours:\nMonday-Friday: 9 AM - 6 PM\n"
                "Saturday: 10 AM - 4 PM\nSunday: Closed"
            )
        if "membership" in message or "member" in message:
            return "Students can use their college ID to access library services."
        if message.startswith("author") or "written by" in message or "books by" in message:
            return self._by_author(message)
        if "compare" in message:
            return self._compare(titles)
        if self.last_book is None:
            suggestion = self._fuzzy_title(message)
            if suggestion:
                self.last_book = suggestion
                return (
                    f"I couldn't find an exact match, but did you mean "
                    f"'{suggestion.title()}'? Ask me anything about it, "
                    "or say 'list books' to browse the catalog."
                )
            return "Please mention a book title or ask to list the books. Type 'help' for options."
        return self._book_answer(message, self.last_book)

    # ------------------------------------------------------------------
    # Matching helpers
    # ------------------------------------------------------------------

    def _mentioned_titles(self, message: str) -> list[str]:
        # Longest-first avoids matching a short title before a longer title.
        return [
            title for title in sorted(self.books, key=len, reverse=True)
            if title in message
        ]

    def _fuzzy_title(self, message: str) -> Optional[str]:
        """Typo-tolerant fallback: matches a title close to any word run in
        the message (e.g. 'sapians' -> 'sapiens')."""
        words = message.split()
        candidates = {message} | {" ".join(words[i:j])
                                   for i in range(len(words))
                                   for j in range(i + 1, len(words) + 1)}
        for candidate in candidates:
            match = difflib.get_close_matches(candidate, self.books.keys(), n=1, cutoff=0.75)
            if match:
                return match[0]
        return None

    # ------------------------------------------------------------------
    # Intent detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_available_books_request(message: str) -> bool:
        words = set(message.split())
        has_book_word = bool({"book", "books", "titles"} & words)
        return "available" in words and (has_book_word or "what is available" in message)

    @staticmethod
    def _is_all_books_request(message: str) -> bool:
        words = set(message.split())
        if "available" in words:
            return False  # handled separately, more specific
        if "recommend" in words or "suggest" in words or "by" in words:
            return False  # recommendation / author-search intents, not a listing
        has_book_word = bool({"book", "books", "titles"} & words) or "catalog" in words
        if not has_book_word:
            return False
        trigger_words = {"list", "all", "which", "what", "show", "present", "catalog"}
        return bool(trigger_words & words)

    @staticmethod
    def _is_price_list_request(message: str) -> bool:
        has_price_word = any(word in message for word in ("price", "prices", "cost", "costs"))
        means_many = any(word in message for word in ("all", "list", "each", "books"))
        return has_price_word and means_many

    @staticmethod
    def _is_recommendation_request(message: str) -> bool:
        return any(word in message for word in ("recommend", "suggest", "looking for"))

    # ------------------------------------------------------------------
    # Response builders
    # ------------------------------------------------------------------

    def _help(self) -> str:
        return (
            "Here's what you can ask me:\n"
            "- 'list books' - see the full catalog\n"
            "- 'available books' - see what's in stock right now\n"
            "- 'prices' - see sample prices\n"
            "- 'recommend <topic>' - get suggestions (programming, finance, history, fiction, self-help)\n"
            "- '<title>' - ask about cost, availability, summary, author, shelf, year, or borrow period\n"
            "- 'books by <author>' - find titles by an author\n"
            "- 'compare <title> and <title>' - side-by-side comparison\n"
            "- 'borrow <title>' / 'return <title>' - simulate checking a book in or out\n"
            "- 'hours', 'membership', 'renew', 'late' - policy questions"
        )

    def _all_books(self) -> str:
        return "Books in the library:\n" + "\n".join(
            f"- {title.title()} by {book.author} ({book.genre})"
            for title, book in self.books.items()
        )

    def _price_list(self) -> str:
        rows = [
            f"- {title.title()}: ₹{book.price_inr:,}"
            for title, book in self.books.items()
        ]
        return "Sample prices per copy (INR):\n" + "\n".join(rows)

    def _available_books(self) -> str:
        rows = [
            f"- {title.title()} ({book.available} of {book.total} copies)"
            for title, book in self.books.items() if book.available > 0
        ]
        return "Available titles:\n" + "\n".join(rows) if rows else "No books are currently available."

    def _recommend(self, message: str) -> str:
        requested = {genre for alias, genre in GENRE_ALIASES.items() if alias in message}
        if not requested:
            return "What topic are you interested in? Try programming, finance, history, fiction, or self-help."
        matches = []
        for genre in requested:
            for title in books_by_genre(genre, self.books):
                book = self.books[title]
                stock = f"{book.available} available" if book.available else "currently checked out"
                matches.append(f"- {title.title()} by {book.author} ({stock})")
        matches = list(dict.fromkeys(matches))
        if not matches:
            return "I couldn't find a title for that topic in this catalog."
        return "Here are some suggestions:\n" + "\n".join(matches)

    def _by_author(self, message: str) -> str:
        matches = [
            title for title, book in self.books.items()
            if book.author.lower() in message
        ]
        if not matches:
            return "I don't recognize that author in this catalog. Try 'list books' to browse."
        return "Titles by that author:\n" + "\n".join(
            f"- {title.title()}" for title in matches
        )

    def _compare(self, titles: list[str]) -> str:
        if len(titles) < 2:
            return "Please mention two catalog titles you want me to compare."
        rows = ["Book comparison:"]
        for title in titles[:2]:
            book = self.books[title]
            rows.extend((
                f"\n{title.title()}", f"Author: {book.author}",
                f"Genre: {book.genre}", f"Year: {book.year}",
                f"Availability: {book.available}/{book.total} copies",
                f"Sample price: ₹{book.price_inr:,}",
            ))
        return "\n".join(rows)

    def _borrow(self, message: str, titles: list[str]) -> str:
        title = titles[0] if titles else self.last_book
        if title is None:
            return "Which book would you like to borrow?"
        book = self.books[title]
        if book.available <= 0:
            self.last_book = title
            return (
                f"{title.title()} is fully checked out ({book.total}/{book.total}). "
                "Say 'reserve it' if you'd like to join the waitlist."
            )
        book.available -= 1
        due = date.today() + timedelta(days=book.borrow_days)
        self.last_book = title
        return (
            f"Checked out {title.title()}. {book.available} of {book.total} copies now remain. "
            f"Due back by {due.isoformat()} ({book.borrow_days} days)."
        )

    def _return(self, message: str, titles: list[str]) -> str:
        title = titles[0] if titles else self.last_book
        if title is None:
            return "Which book are you returning?"
        book = self.books[title]
        if book.available >= book.total:
            return f"All copies of {title.title()} are already checked in."
        book.available += 1
        self.last_book = title
        return f"Thanks! {title.title()} checked in. {book.available} of {book.total} copies now available."

    def _book_answer(self, message: str, title: str) -> str:
        book = self.books[title]
        display_title = title.title()

        if any(word in message for word in ("cost", "price", "how much")):
            return f"The sample price of {display_title} is ₹{book.price_inr:,} per copy."
        if any(word in message for word in ("available", "availability", "stock", "units")):
            return (
                f"{display_title}: {book.available} of {book.total} copies are available."
                if book.available else
                f"{display_title} is currently unavailable; all {book.total} copies are checked out."
            )
        if "copies" in message or "total" in message:
            return f"The library has {book.total} copies of {display_title}; {book.available} are available."
        if "author" in message or "who wrote" in message or "written by" in message:
            return f"{display_title} was written by {book.author}."
        if any(word in message for word in ("summary", "about", "what is it")):
            return f"{display_title}: {book.summary}"
        if "genre" in message or "type" in message:
            return f"{display_title} belongs to the {book.genre} genre."
        if "shelf" in message or "location" in message or "where" in message:
            return f"{display_title} is located on shelf {book.shelf}."
        if "year" in message or "published" in message:
            return f"{display_title} was published in {book.year}."
        if "resource" in message:
            return f"Resources for {display_title}: {book.resources}"
        if "borrow" in message or "how long" in message:
            return f"{display_title} can be borrowed for {book.borrow_days} days."
        return (
            f"{display_title}: {book.author}, {book.year}, {book.genre}. "
            f"{book.available}/{book.total} copies available. "
            "Ask about its cost, summary, resources, or borrowing period."
        )


def run_chatbot() -> None:
    assistant = LibraryChatbot()
    print("Welcome to Lib Chatbot! How may I help you?")
    print("Ask about books, copies/units, costs, recommendations, or summaries. Type 'help' for options, 'exit' to quit.\n")
    while True:
        try:
            message = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! Happy reading!")
            break
        response = assistant.reply(message)
        print(f"\nBot: {response}\n")
        if normalize(message) in {"exit", "quit", "bye", "goodbye"}:
            break


if __name__ == "__main__":
    run_chatbot()
