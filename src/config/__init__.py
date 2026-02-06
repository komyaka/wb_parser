"""Configuration management for WB Parser."""

from .profiles import ConfigManager, load_config, load_default_config, save_config

__all__ = [
    "ConfigManager",
    "load_default_config",
    "save_config",
    "load_config",
]
