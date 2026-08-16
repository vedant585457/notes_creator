"""WatchListen AI Notes — local, privacy-first YouTube notes via Ollama."""

__version__ = "0.1.0"
__app_name__ = "WatchListen"

from watchlisten.config import Config
from watchlisten.models import (
    Chapter,
    FrameDescription,
    NotesDocument,
    TimelineEntry,
    TranscriptSegment,
    VideoMetadata,
)

__all__ = [
    "Config",
    "Chapter",
    "FrameDescription",
    "NotesDocument",
    "TimelineEntry",
    "TranscriptSegment",
    "VideoMetadata",
    "__version__",
    "__app_name__",
]
