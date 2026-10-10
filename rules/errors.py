"""Errors raised before any assessment is produced."""


class ConfigError(ValueError):
    """Rule-engine configuration is invalid; the message names the file and the entry."""
