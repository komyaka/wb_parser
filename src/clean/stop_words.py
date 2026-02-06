"""Stop words and categories filter."""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class StopWordsFilter:
    """Filter for stop words and stop categories."""

    def __init__(
        self,
        stop_categories_file: str | None = None,
        stop_words_file: str | None = None,
        case_sensitive: bool = False,
    ):
        """
        Initialize stop words filter.

        Args:
            stop_categories_file: Path to file with stop categories (1stop.txt)
            stop_words_file: Path to file with stop words (2stop.txt)
            case_sensitive: Whether matching is case-sensitive
        """
        self.case_sensitive = case_sensitive
        self.stop_categories: set[str] = set()
        self.stop_words: set[str] = set()
        self.numeric_pattern = re.compile(r"^\d+$")

        if stop_categories_file:
            self.load_stop_categories(stop_categories_file)

        if stop_words_file:
            self.load_stop_words(stop_words_file)

    def load_stop_categories(self, filepath: str) -> None:
        """Load stop categories from file."""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Stop categories file not found: {filepath}")
            return

        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    category = line if self.case_sensitive else line.lower()
                    self.stop_categories.add(category)

        logger.info(f"Loaded {len(self.stop_categories)} stop categories from {filepath}")

    def load_stop_words(self, filepath: str) -> None:
        """Load stop words from file."""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Stop words file not found: {filepath}")
            return

        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    word = line if self.case_sensitive else line.lower()
                    self.stop_words.add(word)

        logger.info(f"Loaded {len(self.stop_words)} stop words from {filepath}")

    def is_numeric_only(self, query: str) -> bool:
        """Check if query contains only digits."""
        return bool(self.numeric_pattern.match(query.strip()))

    def matches_stop_category(self, category: str) -> bool:
        """
        Check if category matches stop categories (case-insensitive word matching).

        Args:
            category: Category text to check

        Returns:
            True if matches any stop category
        """
        if not category or not self.stop_categories:
            return False

        # Normalize category for comparison
        check_category = category if self.case_sensitive else category.lower()

        # Check if any stop category word appears in the category
        for stop_cat in self.stop_categories:
            # Word boundary matching
            if re.search(r"\b" + re.escape(stop_cat) + r"\b", check_category):
                return True

        return False

    def matches_stop_word(self, query: str) -> tuple[bool, str | None]:
        """
        Check if query matches stop words using token-start matching.

        Token-start matching rule: stop word must appear at the start of a token.
        Example: stop word "термо" matches "термокружка" but not "гидротермокружка"

        Args:
            query: Query text to check

        Returns:
            Tuple of (matches, matched_stop_word)
        """
        if not query or not self.stop_words:
            return False, None

        # Normalize query for comparison
        check_query = query if self.case_sensitive else query.lower()

        # Tokenize query (split by spaces and special chars)
        tokens = re.findall(r"\w+", check_query)

        # Check each token
        for token in tokens:
            for stop_word in self.stop_words:
                # Token-start matching: token starts with stop word
                if token.startswith(stop_word):
                    return True, stop_word

        return False, None

    def should_remove(
        self, query: str, category: str | None = None, remove_numeric: bool = True
    ) -> tuple[bool, str]:
        """
        Check if row should be removed.

        Args:
            query: Search query text
            category: Category text (optional)
            remove_numeric: Whether to remove numeric-only queries

        Returns:
            Tuple of (should_remove, reason)
        """
        # Check numeric-only
        if remove_numeric and self.is_numeric_only(query):
            return True, "numeric_only"

        # Check stop category
        if category and self.matches_stop_category(category):
            return True, "stop_category"

        # Check stop word
        matches, stop_word = self.matches_stop_word(query)
        if matches:
            return True, f"stop_word:{stop_word}"

        return False, ""
