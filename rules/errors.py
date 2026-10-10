"""Errors raised before any assessment is produced."""


class ConfigError(ValueError):
    """Rule-engine configuration is invalid; the message names the file and the entry."""


class TimelineError(ValueError):
    """The input timeline cannot be assessed (malformed, or mixes recordings).

    `code` is a stable identifier listed in docs/rule_engine/anomalies.md.
    """

    def __init__(self, code, message):
        super().__init__(f"{message} [{code}]")
        self.code = code
