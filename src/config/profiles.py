"""Configuration profile management."""

import json
from pathlib import Path

from ..models.config import CleaningConfig, ParserConfig


class ConfigManager:
    """Manages configuration profiles."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_profile(
        self, name: str, parser_config: ParserConfig, cleaning_config: CleaningConfig
    ) -> None:
        """Save configuration profile."""
        profile_path = self.config_dir / f"{name}.json"

        data = {"parser": parser_config.__dict__, "cleaning": cleaning_config.__dict__}

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_profile(self, name: str) -> tuple[ParserConfig, CleaningConfig]:
        """Load configuration profile."""
        profile_path = self.config_dir / f"{name}.json"

        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{name}' not found")

        with open(profile_path, encoding="utf-8") as f:
            data = json.load(f)

        parser_config = ParserConfig(**data["parser"])
        cleaning_config = CleaningConfig(**data["cleaning"])

        return parser_config, cleaning_config

    def list_profiles(self) -> list[str]:
        """List available profiles."""
        return [p.stem for p in self.config_dir.glob("*.json")]

    def delete_profile(self, name: str) -> None:
        """Delete configuration profile."""
        profile_path = self.config_dir / f"{name}.json"
        if profile_path.exists():
            profile_path.unlink()


def load_default_config() -> tuple[ParserConfig, CleaningConfig]:
    """Load default configuration."""
    return ParserConfig(), CleaningConfig()


def save_config(
    parser_config: ParserConfig, cleaning_config: CleaningConfig, filepath: str
) -> None:
    """Save configuration to file."""
    data = {"parser": parser_config.__dict__, "cleaning": cleaning_config.__dict__}

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_config(filepath: str) -> tuple[ParserConfig, CleaningConfig]:
    """Load configuration from file."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    parser_config = ParserConfig(**data["parser"])
    cleaning_config = CleaningConfig(**data["cleaning"])

    return parser_config, cleaning_config
