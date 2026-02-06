"""Unit tests for configuration models."""

import pytest
from src.models.config import ParserConfig, CleaningConfig


class TestParserConfig:
    """Test ParserConfig validation and defaults."""

    def test_defaults(self):
        """Test default configuration values."""
        config = ParserConfig()

        assert config.concurrency == 4
        assert config.min_delay == 0.5
        assert config.max_delay == 1.5
        assert config.retry_max == 5
        assert config.timeout == 20.0
        assert config.use_cache is True
        assert config.enable_checkpoints is True

    def test_validate_success(self):
        """Test validation with valid config."""
        config = ParserConfig(
            concurrency=10, min_delay=1.0, max_delay=2.0, retry_max=3, timeout=30.0
        )

        errors = config.validate()
        assert len(errors) == 0

    def test_validate_concurrency_bounds(self):
        """Test concurrency validation."""
        config = ParserConfig(concurrency=0)
        errors = config.validate()
        assert any("Concurrency" in e for e in errors)

        config = ParserConfig(concurrency=100)
        errors = config.validate()
        assert any("Concurrency" in e for e in errors)

    def test_validate_negative_delays(self):
        """Test negative delay validation."""
        config = ParserConfig(min_delay=-1.0)
        errors = config.validate()
        assert any("Delays must be non-negative" in e for e in errors)

    def test_validate_delay_order(self):
        """Test min_delay > max_delay validation."""
        config = ParserConfig(min_delay=2.0, max_delay=1.0)
        errors = config.validate()
        assert any("Min delay must be <= max delay" in e for e in errors)

    def test_validate_negative_retry(self):
        """Test negative retry_max validation."""
        config = ParserConfig(retry_max=-1)
        errors = config.validate()
        assert any("Retry max must be non-negative" in e for e in errors)

    def test_validate_zero_timeout(self):
        """Test zero timeout validation."""
        config = ParserConfig(timeout=0)
        errors = config.validate()
        assert any("Timeout must be positive" in e for e in errors)

    def test_validate_checkpoint_interval(self):
        """Test checkpoint interval validation."""
        config = ParserConfig(checkpoint_interval=0)
        errors = config.validate()
        assert any("Checkpoint interval must be positive" in e for e in errors)


class TestCleaningConfig:
    """Test CleaningConfig."""

    def test_defaults(self):
        """Test default cleaning configuration."""
        config = CleaningConfig()

        assert config.stop_categories_file == "data/1stop.txt"
        assert config.stop_words_file == "data/2stop.txt"
        assert config.remove_numeric_only is True
        assert config.case_sensitive is False

    def test_column_mapping(self):
        """Test default column mapping."""
        config = CleaningConfig()

        assert "Поисковый запрос" in config.user_column_map
        assert "Категория" in config.user_column_map
        assert "Количество запросов" in config.user_column_map
