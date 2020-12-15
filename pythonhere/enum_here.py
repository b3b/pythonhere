"""Enums."""
from enum import Enum


class StrEnum(str, Enum):
    """Base class for str enums."""

    def __str__(self):
        return str(self.value)


class ScreenName(StrEnum):
    """Enum for root screen names."""

    here = "here"
    settings = "settings"


class ServerState(StrEnum):
    """Enum for %here server state (screen name)."""

    not_configured = "not_configured"
    starting_server = "starting_server"
    ready = "ready"
