from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from enum import Enum
else:
    from discord import Enum

__all__ = (
    "ErrorSeverity",
    "LoadType",
)

class ErrorSeverity(Enum):
    common = "COMMON"
    suspicious = "SUSPICIOUS"
    fault = "FAULT"

class LoadType(Enum):
    track_loaded = "TRACK_LOADED"
    playlist_loaded = "PLAYLIST_LOADED"
    search_result = "SEARCH_RESULT"
    no_matches = "NO_MATCHES"
    load_failed = "LOAD_FAILED"