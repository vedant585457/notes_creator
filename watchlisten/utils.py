"""Pure helpers: timestamps, URLs, filenames, dependency probes."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from watchlisten.models import DepStatus

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_UNSAFE_FS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")


class WatchListenError(Exception):
    """Base error for user-facing failures."""


class URLValidationError(WatchListenError):
    pass


class DependencyError(WatchListenError):
    pass


class MediaError(WatchListenError):
    pass


class ModelError(WatchListenError):
    pass


def parse_timestamp(value: str | float | int) -> float:
    """Parse seconds, `MM:SS`, `HH:MM:SS`, or `HH:MM:SS.mmm` into seconds."""
    if isinstance(value, (int, float)):
        if value < 0:
            raise ValueError("timestamp cannot be negative")
        return float(value)
    raw = value.strip()
    if not raw:
        raise ValueError("empty timestamp")
    if re.fullmatch(r"\d+(\.\d+)?", raw):
        return float(raw)
    parts = raw.split(":")
    if not 2 <= len(parts) <= 3:
        raise ValueError(f"invalid timestamp: {value!r}")
    try:
        nums = [float(p) for p in parts]
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc
    if any(n < 0 for n in nums):
        raise ValueError(f"invalid timestamp: {value!r}")
    if len(nums) == 2:
        minutes, seconds = nums
        hours = 0.0
    else:
        hours, minutes, seconds = nums
    if minutes >= 60 or seconds >= 60:
        # tolerate slightly sloppy LLM output like 00:90
        pass
    return hours * 3600 + minutes * 60 + seconds


def format_timestamp(seconds: float, millis: bool = False) -> str:
    """Format seconds as `H:MM:SS` (or `M:SS` when under an hour)."""
    if seconds < 0:
        seconds = 0.0
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if millis:
        frac = int(round((seconds - int(seconds)) * 1000))
        if frac == 1000:
            frac = 0
            secs += 1
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}.{frac:03d}"
        return f"{minutes}:{secs:02d}.{frac:03d}"
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_duration(seconds: float) -> str:
    """Human duration such as `1h 12m` or `4m 08s`."""
    if seconds < 0:
        seconds = 0.0
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def extract_video_id(url: str) -> str:
    """Extract an 11-char YouTube video id from common URL shapes."""
    raw = (url or "").strip()
    if not raw:
        raise URLValidationError("URL is empty")
    if _VIDEO_ID_RE.fullmatch(raw):
        return raw

    # Tolerate missing scheme
    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        raise URLValidationError(
            f"Not a YouTube URL: {url!r}. Paste a youtube.com or youtu.be link."
        )

    path = parsed.path or ""
    query = parse_qs(parsed.query)

    if host.endswith("youtu.be"):
        vid = path.strip("/").split("/")[0]
        if _VIDEO_ID_RE.fullmatch(vid):
            return vid
        raise URLValidationError(f"Could not find a video id in {url!r}")

    if "v" in query and query["v"]:
        vid = query["v"][0]
        if _VIDEO_ID_RE.fullmatch(vid):
            return vid

    for prefix in ("/shorts/", "/embed/", "/live/", "/v/"):
        if path.startswith(prefix):
            vid = path[len(prefix) :].split("/")[0]
            if _VIDEO_ID_RE.fullmatch(vid):
                return vid

    raise URLValidationError(f"Could not find a video id in {url!r}")


def normalize_youtube_url(url: str) -> str:
    vid = extract_video_id(url)
    return f"https://www.youtube.com/watch?v={vid}"


def is_youtube_url(url: str) -> bool:
    try:
        extract_video_id(url)
        return True
    except URLValidationError:
        return False


def sanitize_filename(name: str, max_len: int = 80) -> str:
    cleaned = _UNSAFE_FS.sub("", name)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip().strip(".")
    cleaned = cleaned.replace(" ", "_")
    if not cleaned:
        cleaned = "notes"
    return cleaned[:max_len]


def which(binary: str) -> str | None:
    return shutil.which(binary)


def run_cmd(
    args: list[str],
    *,
    timeout: int | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd) if cwd else None,
    )


def ffmpeg_available() -> bool:
    return which("ffmpeg") is not None


def tesseract_available() -> bool:
    return which("tesseract") is not None


def probe_dependencies(ollama_host: str | None = None) -> DepStatus:
    """Best-effort inventory of optional / required runtime pieces."""
    status = DepStatus(
        ffmpeg=ffmpeg_available(),
        tesseract=tesseract_available(),
        ollama=True,  # python package is a hard dep; reachability checked below
    )
    try:
        import cv2  # noqa: F401

        status.opencv = True
    except Exception:
        status.opencv = False
    try:
        import scenedetect  # noqa: F401

        status.scenedetect = True
    except Exception:
        status.scenedetect = False
    try:
        import faster_whisper  # noqa: F401

        status.whisper = True
    except Exception:
        status.whisper = False
    try:
        import weasyprint  # noqa: F401

        status.weasyprint = True
    except Exception:
        status.weasyprint = False

    try:
        import ollama

        client_kwargs = {}
        if ollama_host:
            client_kwargs["host"] = ollama_host
        client = ollama.Client(**client_kwargs) if client_kwargs else ollama.Client()
        listing = client.list()
        models = _extract_model_names(listing)
        status.ollama_reachable = True
        status.all_models = models
        status.vision_models = [m for m in models if _looks_like_vision(m)]
        status.text_models = models
    except Exception:
        status.ollama_reachable = False

    return status


def _extract_model_names(listing: object) -> list[str]:
    models: list[str] = []
    raw_list: list[object] = []
    if isinstance(listing, dict):
        raw_list = list(listing.get("models") or [])
    else:
        raw_list = list(getattr(listing, "models", None) or [])
    for item in raw_list:
        name = ""
        if isinstance(item, dict):
            name = str(item.get("model") or item.get("name") or "")
        else:
            name = str(getattr(item, "model", "") or getattr(item, "name", "") or "")
        name = name.strip()
        if name:
            models.append(name)
    return models


def _looks_like_vision(name: str) -> bool:
    lowered = name.lower()
    needles = ("vision", "llava", "moondream", "minicpm", "qwen2.5vl", "qwen2-vl", "bakllava")
    return any(n in lowered for n in needles)


def chunked(seq: list, size: int) -> list[list]:
    if size <= 0:
        raise ValueError("size must be positive")
    return [seq[i : i + size] for i in range(0, len(seq), size)]
