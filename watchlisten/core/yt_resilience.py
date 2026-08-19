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
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Aug 2026: android_vr streams often 403; tv frequently reports false DRM (SABR).
# Prefer web/ios clients that still return regular HTTPS/HLS formats.
DEFAULT_PLAYER_CLIENTS = (
    "web_safari",
    "web_embedded",
    "ios",
    "mweb",
    "tv",
    "android_vr",
)

# Empty string = do not set `format`; let yt-dlp pick whatever exists.
FORMAT_ANY = ""
FORMAT_MERGED = "bv*+ba/b"
FORMAT_AUDIO = "ba/b"
FORMAT_VIDEO_720 = FORMAT_MERGED  # kept for older tests / callers

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
    # One client listing only SABR/Widevine formats. Other clients often still
    # have a normal stream — this is NOT a request to break real DRM.
    "this video is drm protected",
    "drm protected",
    "only images are available",
    "sabr streaming",
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


def is_drm_report(exc: BaseException | str) -> bool:
    """True when yt-dlp labelled formats as DRM — often only one client."""
    return "drm" in _norm(exc)


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


def detect_js_runtime() -> dict[str, dict]:
    """Return yt-dlp `js_runtimes` for whatever interpreter is on PATH."""
    import shutil
    import subprocess

    found: dict[str, dict] = {}
    deno = shutil.which("deno")
    if deno:
        found["deno"] = {"path": deno}
    node = shutil.which("node") or shutil.which("nodejs")
    if node and _node_major(node) >= 20:
        found["node"] = {"path": node}
    for binary in ("qjs", "quickjs", "qjs-ng"):
        path = shutil.which(binary)
        if path:
            found["quickjs"] = {"path": path}
            break
    return found


def _node_major(path: str) -> int:
    try:
        proc = subprocess.run(
            [path, "-v"], capture_output=True, text=True, timeout=5, check=False
        )
        raw = (proc.stdout or proc.stderr or "").strip().lstrip("vV")
        return int(raw.split(".", 1)[0])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return 0


def ejs_installed() -> bool:
    try:
        import yt_dlp_ejs  # noqa: F401

        return True
    except Exception:
        return False


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

    # 1. Let yt-dlp pick clients AND format. This is the only strategy that
    #    stays correct as YouTube changes — we just supply EJS + a JS runtime.
    add("", FORMAT_ANY, "yt-dlp default", want_video=True, use_cookies=False, backoff=4)
    add("", FORMAT_MERGED, "yt-dlp default · any stream", want_video=True, use_cookies=False, backoff=4)
    if cookies_configured:
        add("", FORMAT_ANY, "yt-dlp default + cookies", want_video=True, use_cookies=True, backoff=4)
    # 2. Named clients only if the default mix failed.
    for client in (primary, *rest[:3]):
        add(client, FORMAT_ANY, f"{client} · any", want_video=True, use_cookies=False, backoff=3)
    # 3. Audio-only is enough to listen.
    add("", FORMAT_AUDIO, "audio only", want_video=False, use_cookies=False, backoff=3)
    if cookies_configured:
        add("", FORMAT_AUDIO, "audio + cookies", want_video=False, use_cookies=True, backoff=0)
    return plan


def build_metadata_plan(
    *,
    cookies_configured: bool,
    clients: list[str] | None = None,
) -> list[DownloadAttempt]:
    """Lighter ladder for `extract_info(download=False)`.

    First shot lets yt-dlp pick its own client mix. We never need a
    downloadable format here — only title, duration, chapters, captions.
    """
    names = [c.strip() for c in (clients or list(DEFAULT_PLAYER_CLIENTS)) if c and c.strip()]
    if not names:
        names = list(DEFAULT_PLAYER_CLIENTS)
    plan: list[DownloadAttempt] = [
        DownloadAttempt(
            client="",
            format_spec="",
            label="meta/default",
            want_video=False,
            use_cookies=False,
            backoff=1,
        )
    ]
    for client in names:
        plan.append(
            DownloadAttempt(
                client=client,
                format_spec="",
                label=f"meta/{client}",
                want_video=False,
                use_cookies=False,
                backoff=1,
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
                backoff=1,
            )
        )
    return plan
