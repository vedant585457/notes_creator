"""YouTube / yt-dlp rate-limit detection, backoff, and fallback strategies.

YouTube throttles anonymous Innertube traffic (HTTP 429, "try again later",
"confirm you're not a bot"). Official yt-dlp guidance:

* use a *single* player client that does not need a PO token (`android_vr`)
* sleep between extractor requests
* retry with exponential backoff
* force IPv4 (IPv6 guest sessions are banned more aggressively)
* if still blocked, switch client (tv / ios / web_safari) rather than fail
* cookies are a last resort — they can get an account flagged if overused

This module is pure (no yt-dlp import) so the plan can be unit-tested offline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Clients that currently work *without* a PO token for most public videos.
# Order is "fewest extra requests / most reliable" first.
DEFAULT_PLAYER_CLIENTS = ("android_vr", "tv", "ios", "web_safari", "mweb")

FORMAT_VIDEO_720 = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
FORMAT_VIDEO_480 = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
FORMAT_PROGRESSIVE = "best[ext=mp4][height<=720]/best[height<=720]/best[ext=mp4]/best"
FORMAT_AUDIO = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"

RATE_LIMIT_MARKERS = (
    "http error 429",
    "too many requests",
    "sign in to confirm you're not a bot",
    "sign in to confirm you’re not a bot",
    "confirm you're not a bot",
    "confirm you’re not a bot",
    "this content isn't available, try again later",
    "this content isn’t available, try again later",
    "rate-limit",
    "rate limit",
    "has been rate-limited",
    "please wait and try again",
)

RECOVERABLE_MARKERS = RATE_LIMIT_MARKERS + (
    "http error 403",
    "http error 503",
    "http error 502",
    "http error 500",
    "gave http error 403",
    "unable to download video data",
    "unable to download webpage",
    "the downloaded file is empty",
    "premature end of content",
    "the read operation timed out",
    "timed out",
    "connection reset",
    "temporary failure",
    "eof occurred in violation",
    "ssl: unexpected_eof",
    "fragment not found",
    "requested format is not available",
)


@dataclass(frozen=True, slots=True)
class DownloadAttempt:
    """One concrete yt-dlp strategy to try before giving up."""

    client: str
    format_spec: str
    label: str
    want_video: bool
    use_cookies: bool
    backoff: float
    write_subs: bool = False


def _norm(exc: BaseException | str) -> str:
    return str(exc).lower().replace("’", "'").replace("“", '"').replace("”", '"')


def is_rate_limited(exc: BaseException | str) -> bool:
    text = _norm(exc)
    return any(marker in text for marker in RATE_LIMIT_MARKERS)


def is_recoverable(exc: BaseException | str) -> bool:
    text = _norm(exc)
    return any(marker in text for marker in RECOVERABLE_MARKERS)


def backoff_seconds(attempt_index: int, *, base: float = 8.0, cap: float = 60.0) -> float:
    """Exponential wait after a throttled attempt. attempt_index is 0-based."""
    if attempt_index < 0:
        attempt_index = 0
    return float(min(cap, base * (1.6**attempt_index)))


def parse_rate(value: str | int | float | None) -> int | None:
    """Parse `2.5M`, `500K`, or a raw byte count into bytes/sec."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value) if value else None
    raw = str(value).strip().upper().replace("B", "")
    if not raw:
        return None
    multiplier = 1
    if raw.endswith("G"):
        multiplier = 1024**3
        raw = raw[:-1]
    elif raw.endswith("M"):
        multiplier = 1024**2
        raw = raw[:-1]
    elif raw.endswith("K"):
        multiplier = 1024
        raw = raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except ValueError:
        return None


def parse_cookies_from_browser(value: str) -> tuple[str, ...] | None:
    """`firefox` → `('firefox',)`; `chrome:Default` → `('chrome', 'Default')`."""
    raw = (value or "").strip()
    if not raw or raw.lower() in {"none", "off", "false"}:
        return None
    if raw.lower() == "auto":
        return None
    if ":" in raw:
        browser, profile = raw.split(":", 1)
        browser, profile = browser.strip(), profile.strip()
        if browser and profile:
            return (browser, profile)
        if browser:
            return (browser,)
        return None
    return (raw,)


def detect_browsers() -> list[str]:
    """Return browsers that look installed enough for `--cookies-from-browser`."""
    home = Path.home()
    local_app = os.environ.get("LOCALAPPDATA") or ""
    roaming_app = os.environ.get("APPDATA") or ""
    local = Path(local_app) if local_app else None
    roaming = Path(roaming_app) if roaming_app else None
    checks: dict[str, list[Path]] = {
        "firefox": [
            home / ".mozilla" / "firefox",
            home / "Library" / "Application Support" / "Firefox",
        ],
        "chrome": [
            home / ".config" / "google-chrome",
            home / "Library" / "Application Support" / "Google" / "Chrome",
        ],
        "chromium": [
            home / ".config" / "chromium",
            home / "Library" / "Application Support" / "Chromium",
        ],
        "brave": [
            home / ".config" / "BraveSoftware" / "Brave-Browser",
            home / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser",
        ],
        "edge": [
            home / ".config" / "microsoft-edge",
            home / "Library" / "Application Support" / "Microsoft Edge",
        ],
        "vivaldi": [
            home / ".config" / "vivaldi",
            home / "Library" / "Application Support" / "Vivaldi",
        ],
    }
    if roaming is not None:
        checks["firefox"].append(roaming / "Mozilla" / "Firefox")
    if local is not None:
        checks["chrome"].append(local / "Google" / "Chrome" / "User Data")
        checks["brave"].append(local / "BraveSoftware" / "Brave-Browser" / "User Data")
        checks["edge"].append(local / "Microsoft" / "Edge" / "User Data")
        checks["vivaldi"].append(local / "Vivaldi" / "User Data")
    found: list[str] = []
    for name, paths in checks.items():
        if any(p.exists() for p in paths):
            found.append(name)
    return found


def build_attempt_plan(
    *,
    cookies_configured: bool,
    clients: list[str] | None = None,
) -> list[DownloadAttempt]:
    """Build a short ladder: one client at a time, then lower quality, then audio.

    Trying every client in a *single* yt-dlp call multiplies Innertube hits and
    makes a 429 worse. We walk the ladder ourselves instead.
    """
    names = [c.strip() for c in (clients or list(DEFAULT_PLAYER_CLIENTS)) if c and c.strip()]
    if not names:
        names = list(DEFAULT_PLAYER_CLIENTS)

    plan: list[DownloadAttempt] = []
    primary = names[0]
    rest = names[1:]

    def add(
        client: str,
        fmt: str,
        label: str,
        *,
        want_video: bool,
        use_cookies: bool,
        backoff: float,
        write_subs: bool = False,
    ) -> None:
        plan.append(
            DownloadAttempt(
                client=client,
                format_spec=fmt,
                label=label,
                want_video=want_video,
                use_cookies=use_cookies,
                backoff=backoff,
                write_subs=write_subs,
            )
        )

    # 1. Quiet guest session on the friendliest client, 720p, no extra caption traffic.
    add(primary, FORMAT_VIDEO_720, f"{primary} · 720p", want_video=True, use_cookies=False, backoff=8)
    # 2. Same client, progressive (one file, fewer fragment 403s).
    add(
        primary,
        FORMAT_PROGRESSIVE,
        f"{primary} · progressive",
        want_video=True,
        use_cookies=False,
        backoff=12,
    )
    # 3. If the user configured cookies, use them *now* — still on the primary client.
    if cookies_configured:
        add(
            primary,
            FORMAT_VIDEO_720,
            f"{primary} · 720p + cookies",
            want_video=True,
            use_cookies=True,
            backoff=10,
        )
    # 4. Other clients at 720p / 480p.
    for idx, client in enumerate(rest):
        fmt = FORMAT_VIDEO_720 if idx == 0 else FORMAT_VIDEO_480
        kind = "720p" if idx == 0 else "480p"
        add(client, fmt, f"{client} · {kind}", want_video=True, use_cookies=False, backoff=16 + idx * 6)
    # 5. Audio-only: enough to listen. Watch can be skipped.
    add(primary, FORMAT_AUDIO, f"{primary} · audio only", want_video=False, use_cookies=False, backoff=20)
    if rest:
        add(rest[0], FORMAT_AUDIO, f"{rest[0]} · audio only", want_video=False, use_cookies=False, backoff=8)
    if cookies_configured:
        add(
            primary,
            FORMAT_AUDIO,
            f"{primary} · audio + cookies",
            want_video=False,
            use_cookies=True,
            backoff=0,
        )
    return plan


def build_metadata_plan(
    *,
    cookies_configured: bool,
    clients: list[str] | None = None,
) -> list[DownloadAttempt]:
    """Lighter ladder for `extract_info(download=False)`."""
    names = [c.strip() for c in (clients or list(DEFAULT_PLAYER_CLIENTS)) if c and c.strip()]
    if not names:
        names = list(DEFAULT_PLAYER_CLIENTS)
    plan: list[DownloadAttempt] = []
    for idx, client in enumerate(names[:4]):
        plan.append(
            DownloadAttempt(
                client=client,
                format_spec="",
                label=f"meta/{client}",
                want_video=False,
                use_cookies=False,
                backoff=backoff_seconds(idx, base=5.0, cap=30.0),
            )
        )
    if cookies_configured:
        plan.append(
            DownloadAttempt(
                client=names[0],
                format_spec="",
                label=f"meta/{names[0]}+cookies",
                want_video=False,
                use_cookies=True,
                backoff=8,
            )
        )
    return plan
