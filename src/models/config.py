"""Configuration data models."""

from dataclasses import dataclass, field


@dataclass
class CleaningConfig:
    """Configuration for data cleaning."""

    stop_categories_file: str = "data/1stop.txt"
    stop_words_file: str = "data/2stop.txt"
    remove_numeric_only: bool = True
    case_sensitive: bool = False

    # Column mapping similar to chistka_good.py
    user_column_map: dict[str, str] = field(
        default_factory=lambda: {
            "Поисковый запрос": "query",
            "Категория": "category",
            "Количество запросов": "count",
        }
    )


@dataclass
class ParserConfig:
    """Configuration for WB API parser."""

    # Concurrency settings
    concurrency: int = 4
    min_concurrency: int = 1
    max_concurrency: int = 20

    # Delay settings (seconds)
    min_delay: float = 0.5
    max_delay: float = 1.5

    # Retry settings
    retry_max: int = 5
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    retry_exponential_base: float = 2.0

    # Timeout settings (seconds)
    timeout: float = 20.0

    # Cache settings
    use_cache: bool = True
    cache_db_path: str = "wb_cache.db"
    force_refresh: bool = False

    # Checkpoint settings
    enable_checkpoints: bool = True
    checkpoint_interval: int = 50  # Save every N queries
    checkpoint_file: str = "wb_checkpoint.json"

    # Output settings
    output_csv: str = "wb_results.csv"
    output_encoding: str = "utf-8-sig"
    save_raw_response: bool = False

    # API settings
    api_base_url: str = (
        "https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search"
    )
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not (self.min_concurrency <= self.concurrency <= self.max_concurrency):
            errors.append(
                f"Concurrency must be between {self.min_concurrency} and {self.max_concurrency}"
            )

        if self.min_delay < 0 or self.max_delay < 0:
            errors.append("Delays must be non-negative")

        if self.min_delay > self.max_delay:
            errors.append("Min delay must be <= max delay")

        if self.retry_max < 0:
            errors.append("Retry max must be non-negative")

        if self.timeout <= 0:
            errors.append("Timeout must be positive")

        if self.checkpoint_interval <= 0:
            errors.append("Checkpoint interval must be positive")

        return errors
