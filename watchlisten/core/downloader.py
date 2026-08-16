"""yt-dlp wrapper: metadata, resilient media download, captions, audio extract."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from watchlisten.config import Config
from watchlisten.core.yt_resilience import (
    DownloadAttempt,
    build_attempt_plan,
    build_metadata_plan,
    detect_browsers,
    is_rate_limited,
    is_recoverable,
    parse_cookies_from_browser,
    parse_rate,
)
from watchlisten.models import Chapter, MediaBundle, VideoMetadata
from watchlisten.utils import (
    CancelledError,
    MediaError,
    URLValidationError,
    extract_video_id,
    ffmpeg_available,
    normalize_youtube_url,
    run_cmd,
)

ProgressHook = Callable[[str, int, int, str], None]
LogHook = Callable[[str], None]
CancelHook = Callable[[], bool]
SleepFn = Callable[[float], None]

VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
AUDIO_EXTS = {".m4a", ".webm", ".opus", ".mp3", ".ogg", ".wav", ".aac"}


class Downloader:
    def __init__(
        self,
        config: Config,
        *,
        on_progress: ProgressHook | None = None,
        on_log: LogHook | None = None,
        is_cancelled: CancelHook | None = None,
        sleeper: SleepFn | None = None,
        ydl_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.config = config
        self.on_progress = on_progress or (lambda *_args: None)
        self.on_log = on_log or (lambda _msg: None)
        self.is_cancelled = is_cancelled or (lambda: False)
        self._sleep = sleeper or time.sleep
        self._ydl_factory = ydl_factory or _yt_dlp

    def fetch_metadata(self, url: str) -> VideoMetadata:
        url = normalize_youtube_url(url)
        plan = build_metadata_plan(
            cookies_configured=self._cookies_ready(),
            clients=list(self.config.download.player_clients),
        )
        last_error: Exception | None = None
        for index, attempt in enumerate(plan):
            self._check_cancel()
            opts = self._ydl_opts(attempt, skip_download=True)
            self.on_log(f"Fetching metadata via {attempt.label}")
            try:
                info = self._extract(url, opts)
            except Exception as exc:
                last_error = exc
                if not is_recoverable(exc) or index == len(plan) - 1:
                    raise _translate_ytdlp_error(exc, url) from exc
                wait = attempt.backoff
                self.on_log(self._retry_message(exc, attempt, wait, index, len(plan)))
                self._interruptible_sleep(wait)
                continue
            if not info:
                last_error = MediaError(f"yt-dlp returned no metadata for {url}")
                continue
            if info.get("_type") == "playlist":
                entries = info.get("entries") or []
                if not entries:
                    raise MediaError("This looks like a playlist, not a single video.")
                info = entries[0]
            return _metadata_from_info(url, info)
        raise _translate_ytdlp_error(last_error or MediaError("metadata failed"), url)

    def download(self, url: str, workdir: Path, meta: VideoMetadata | None = None) -> MediaBundle:
        url = normalize_youtube_url(url)
        video_id = meta.video_id if meta else extract_video_id(url)
        workdir.mkdir(parents=True, exist_ok=True)

        reused = self._reuse_existing(workdir, video_id)
        if reused is not None:
            return reused

        plan = build_attempt_plan(
            cookies_configured=self._cookies_ready(),
            clients=list(self.config.download.player_clients),
        )
        last_error: Exception | None = None
        for index, attempt in enumerate(plan):
            self._check_cancel()
            self.on_log(f"Download strategy {index + 1}/{len(plan)}: {attempt.label}")
            self.on_progress("download", index, len(plan), attempt.label)
            opts = self._ydl_opts(attempt, skip_download=False, workdir=workdir, video_id=video_id)
            try:
                self._download(url, opts)
            except Exception as exc:
                last_error = exc
                if not is_recoverable(exc):
                    raise _translate_ytdlp_error(exc, url) from exc
                wait = attempt.backoff
                if index < len(plan) - 1 and wait > 0:
                    self.on_log(self._retry_message(exc, attempt, wait, index, len(plan)))
                    self._interruptible_sleep(wait)
                else:
                    self.on_log(f"{attempt.label} failed: {_short_error(exc)}")
                continue

            bundle = self._collect_bundle(workdir, video_id)
            if bundle.video_path or bundle.audio_path:
                if not bundle.caption_path:
                    self._try_captions(url, workdir, video_id)
                    bundle.caption_path = _pick_caption(workdir, video_id)
                return bundle
            self.on_log(f"{attempt.label} finished but produced no media; trying next strategy.")

        # Last resort: notes from captions still beat a hard 429.
        caption_only = self._try_captions(url, workdir, video_id)
        if caption_only is not None:
            self.on_log(
                "YouTube blocked the media download, but captions are available — "
                "continuing so notes can still be written."
            )
            return MediaBundle(workdir=workdir, caption_path=caption_only)

        raise _translate_ytdlp_error(
            last_error or MediaError("download failed"),
            url,
            exhausted=True,
        )

    # ------------------------------------------------------------------
    # yt-dlp session
    # ------------------------------------------------------------------

    def _extract(self, url: str, opts: dict[str, Any]) -> dict[str, Any] | None:
        ydl = self._ydl_factory()
        with ydl.YoutubeDL(opts) as client:
            return client.extract_info(url, download=False)

    def _download(self, url: str, opts: dict[str, Any]) -> None:
        ydl = self._ydl_factory()
        with ydl.YoutubeDL(opts) as client:
            client.download([url])

    def _ydl_opts(
        self,
        attempt: DownloadAttempt,
        *,
        skip_download: bool,
        workdir: Path | None = None,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        cfg = self.config.download
        opts: dict[str, Any] = {
            "skip_download": skip_download,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "overwrites": False,
            "continuedl": True,
            "ignoreerrors": False,
            "noprogress": True,
            "retries": max(int(cfg.retries), 3),
            "fragment_retries": max(int(cfg.retries), 3),
            "extractor_retries": max(3, int(cfg.retries) // 2),
            "file_access_retries": 3,
            "retry_sleep_functions": {
                "http": lambda n: min(2**n, 45),
                "fragment": lambda n: min(2**n, 30),
                "extractor": lambda n: min(4 * n, 30),
            },
            "sleep_interval_requests": float(cfg.sleep_requests),
            "sleep_interval": 2.0,
            "max_sleep_interval": 6.0,
            "sleep_interval_subtitles": 2.0,
            "concurrent_fragment_downloads": max(1, int(cfg.concurrent_fragments)),
            "socket_timeout": 30,
            "cachedir": str(self.config.cache_path / "yt-dlp"),
            "extractor_args": {"youtube": {"player_client": [attempt.client]}},
            "progress_hooks": [self._ydl_hook],
        }
        if attempt.format_spec:
            opts["format"] = attempt.format_spec
        if not skip_download:
            opts["merge_output_format"] = "mp4"
        if cfg.force_ipv4:
            opts["source_address"] = "0.0.0.0"
        rate = parse_rate(cfg.limit_rate)
        if rate:
            opts["ratelimit"] = rate
        if cfg.proxy:
            opts["proxy"] = cfg.proxy
        if attempt.use_cookies:
            self._apply_cookies(opts)
        if attempt.write_subs:
            opts.update(_subtitle_opts())
        if workdir is not None and video_id:
            opts["outtmpl"] = str(workdir / f"{video_id}.%(ext)s")
        return opts

    def _apply_cookies(self, opts: dict[str, Any]) -> None:
        cfg = self.config.download
        cookiefile = (cfg.cookiefile or "").strip()
        if cookiefile:
            path = Path(cookiefile).expanduser()
            if path.is_file():
                opts["cookiefile"] = str(path)
                self.on_log(f"Using cookie file {path}")
                return
            self.on_log(f"Cookie file not found: {path}")
        spec = (cfg.cookies_from_browser or "").strip()
        if spec.lower() == "auto":
            browsers = detect_browsers()
            if not browsers:
                self.on_log("No local browser profiles found for cookies.")
                return
            spec = browsers[0]
            self.on_log(f"Auto-selected browser cookies from {spec}")
        parsed = parse_cookies_from_browser(spec)
        if parsed:
            opts["cookiesfrombrowser"] = parsed
            self.on_log(f"Reading cookies from browser {parsed[0]}")

    def _cookies_ready(self) -> bool:
        cfg = self.config.download
        if (cfg.cookiefile or "").strip():
            return True
        spec = (cfg.cookies_from_browser or "").strip()
        if not spec:
            return False
        if spec.lower() == "auto":
            return bool(detect_browsers())
        return parse_cookies_from_browser(spec) is not None

    # ------------------------------------------------------------------
    # media on disk
    # ------------------------------------------------------------------

    def _reuse_existing(self, workdir: Path, video_id: str) -> MediaBundle | None:
        bundle = self._collect_bundle(workdir, video_id, extract=False)
        if bundle.video_path is None and bundle.audio_path is None:
            return None
        needs_wav = bundle.audio_path is None or bundle.audio_path.suffix.lower() != ".wav"
        if needs_wav:
            source = bundle.video_path or bundle.audio_path
            if source is not None and ffmpeg_available():
                wav = workdir / f"{video_id}.wav"
                self._extract_audio(source, wav)
                bundle.audio_path = wav if wav.exists() else bundle.audio_path
        self.on_log(
            f"Reusing cached media "
            f"{(bundle.video_path or bundle.audio_path).name}"  # type: ignore[union-attr]
        )
        return bundle

    def _collect_bundle(self, workdir: Path, video_id: str, *, extract: bool = True) -> MediaBundle:
        video_path = _find_first(
            workdir, [f"{video_id}.mp4", f"{video_id}.mkv", f"{video_id}.webm", f"{video_id}.mov"]
        )
        if video_path is None:
            video_path = next(
                (p for p in workdir.iterdir() if p.suffix.lower() in VIDEO_EXTS and video_id in p.stem),
                None,
            )
        audio_src = _find_first(
            workdir,
            [f"{video_id}.m4a", f"{video_id}.opus", f"{video_id}.mp3", f"{video_id}.ogg", f"{video_id}.aac"],
        )
        wav = workdir / f"{video_id}.wav"
        if extract and ffmpeg_available():
            source = video_path or audio_src
            if source is not None and not wav.exists():
                try:
                    self._extract_audio(source, wav)
                except MediaError as exc:
                    self.on_log(str(exc))
        audio_path = wav if wav.exists() else audio_src
        return MediaBundle(
            workdir=workdir,
            video_path=video_path,
            audio_path=audio_path,
            caption_path=_pick_caption(workdir, video_id),
            thumbnail_path=_find_first(
                workdir, [f"{video_id}.jpg", f"{video_id}.webp", f"{video_id}.png", f"{video_id}.jpeg"]
            ),
        )

    def _extract_audio(self, media: Path, dest: Path) -> None:
        self.on_log(f"Extracting 16 kHz mono WAV via ffmpeg → {dest.name}")
        result = run_cmd(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(media),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                str(dest),
            ],
            timeout=600,
        )
        if result.returncode != 0 or not dest.exists():
            tail = (result.stderr or result.stdout or "").strip().splitlines()
            hint = tail[-1] if tail else "unknown ffmpeg error"
            raise MediaError(f"ffmpeg failed to extract audio: {hint}")

    def _try_captions(self, url: str, workdir: Path, video_id: str) -> Path | None:
        existing = _pick_caption(workdir, video_id)
        if existing:
            return existing
        self._check_cancel()
        try:
            opts = self._ydl_opts(
                DownloadAttempt(
                    client=self.config.download.player_clients[0]
                    if self.config.download.player_clients
                    else "android_vr",
                    format_spec="",
                    label="captions",
                    want_video=False,
                    use_cookies=self._cookies_ready(),
                    backoff=0,
                    write_subs=False,
                ),
                skip_download=True,
            )
            info = self._extract(url, opts) or {}
        except Exception as exc:
            self.on_log(f"Caption lookup skipped: {_short_error(exc)}")
            return None
        saved = _save_caption_from_info(info, workdir, video_id, log=self.on_log)
        return saved or _pick_caption(workdir, video_id)

    def _ydl_hook(self, event: dict[str, Any]) -> None:
        status = event.get("status")
        if status == "downloading":
            downloaded = int(event.get("downloaded_bytes") or 0)
            total = int(event.get("total_bytes") or event.get("total_bytes_estimate") or 0)
            speed = event.get("_speed_str") or ""
            eta = event.get("_eta_str") or ""
            msg = " ".join(p for p in (speed, f"eta {eta}" if eta else "") if p)
            self.on_progress("download", downloaded, total, msg)
        elif status == "finished":
            filename = event.get("filename") or ""
            self.on_log(f"Download finished: {Path(filename).name}")
            self.on_progress("download", 1, 1, "merging streams")

    def _retry_message(
        self,
        exc: Exception,
        attempt: DownloadAttempt,
        wait: float,
        index: int,
        total: int,
    ) -> str:
        kind = "rate-limited" if is_rate_limited(exc) else "blocked"
        return (
            f"YouTube {kind} on {attempt.label} ({_short_error(exc)}). "
            f"Waiting {wait:.0f}s, then trying the next strategy "
            f"({index + 2}/{total})…"
        )

    def _interruptible_sleep(self, seconds: float) -> None:
        if seconds <= 0:
            return
        end = time.monotonic() + seconds
        while True:
            self._check_cancel()
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            self._sleep(min(0.25, remaining))

    def _check_cancel(self) -> None:
        if self.is_cancelled():
            raise CancelledError("Cancelled by user.")


def parse_caption_file(path: Path) -> list[tuple[float, float, str]]:
    """Parse a small VTT or SRT file into (start, end, text) triples."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".vtt" or text.lstrip().startswith("WEBVTT"):
        return _parse_vtt(text)
    return _parse_srt(text)


def _parse_vtt(text: str) -> list[tuple[float, float, str]]:
    from watchlisten.utils import parse_timestamp

    cues: list[tuple[float, float, str]] = []
    blocks = _split_cue_blocks(text)
    for block in blocks:
        lines = [ln.strip("\ufeff") for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        timing = next((ln for ln in lines if "-->" in ln), None)
        if not timing:
            continue
        start_s, end_s = _split_arrow(timing)
        try:
            start, end = parse_timestamp(_strip_vtt_settings(start_s)), parse_timestamp(
                _strip_vtt_settings(end_s)
            )
        except ValueError:
            continue
        body_lines = []
        seen_timing = False
        for ln in lines:
            if "-->" in ln:
                seen_timing = True
                continue
            if not seen_timing:
                continue
            cleaned = _strip_tags(ln).strip()
            if cleaned:
                body_lines.append(cleaned)
        body = " ".join(body_lines).strip()
        if body:
            cues.append((start, end, body))
    return _dedupe_caption_cues(cues)


def _parse_srt(text: str) -> list[tuple[float, float, str]]:
    from watchlisten.utils import parse_timestamp

    cues: list[tuple[float, float, str]] = []
    for block in _split_cue_blocks(text):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        timing = next((ln for ln in lines if "-->" in ln), None)
        if not timing:
            continue
        start_s, end_s = _split_arrow(timing)
        try:
            start = parse_timestamp(start_s.replace(",", "."))
            end = parse_timestamp(end_s.replace(",", "."))
        except ValueError:
            continue
        body_lines = []
        seen = False
        for ln in lines:
            if "-->" in ln:
                seen = True
                continue
            if not seen:
                continue
            cleaned = _strip_tags(ln).strip()
            if cleaned:
                body_lines.append(cleaned)
        body = " ".join(body_lines).strip()
        if body:
            cues.append((start, end, body))
    return _dedupe_caption_cues(cues)


def _split_cue_blocks(text: str) -> list[str]:
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    return [b for b in normalised.split("\n\n") if b.strip() and not b.strip().startswith("NOTE")]


def _split_arrow(timing: str) -> tuple[str, str]:
    left, right = timing.split("-->", 1)
    return left.strip(), right.strip()


def _strip_vtt_settings(token: str) -> str:
    return token.split()[0].replace(",", ".")


def _strip_tags(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text)


def _dedupe_caption_cues(
    cues: list[tuple[float, float, str]],
) -> list[tuple[float, float, str]]:
    """YouTube auto-captions repeat rolling windows; keep new words only."""
    if not cues:
        return []
    out: list[tuple[float, float, str]] = []
    prev = ""
    for start, end, text in cues:
        if text == prev:
            continue
        if prev and text.startswith(prev):
            delta = text[len(prev) :].strip()
            if delta:
                out.append((start, end, delta))
            prev = text
            continue
        out.append((start, end, text))
        prev = text
    return out


def _metadata_from_info(url: str, info: dict[str, Any]) -> VideoMetadata:
    video_id = str(info.get("id") or extract_video_id(url))
    chapters: list[Chapter] = []
    raw_chapters = info.get("chapters") or []
    duration = float(info.get("duration") or 0.0)
    for idx, ch in enumerate(raw_chapters):
        start = float(ch.get("start_time") or 0.0)
        end = ch.get("end_time")
        if end is None and idx + 1 < len(raw_chapters):
            end = raw_chapters[idx + 1].get("start_time")
        if end is None:
            end = duration or None
        chapters.append(
            Chapter(
                title=str(ch.get("title") or f"Chapter {idx + 1}"),
                start=start,
                end=float(end) if end is not None else None,
            )
        )
    subs = info.get("subtitles") or {}
    autos = info.get("automatic_captions") or {}
    langs = sorted({*subs.keys(), *autos.keys()})
    return VideoMetadata(
        url=url,
        video_id=video_id,
        title=str(info.get("title") or video_id),
        duration=duration,
        description=str(info.get("description") or ""),
        uploader=str(info.get("uploader") or info.get("channel") or ""),
        channel=str(info.get("channel") or info.get("uploader") or ""),
        upload_date=str(info.get("upload_date") or ""),
        thumbnail=str(info.get("thumbnail") or ""),
        webpage_url=str(info.get("webpage_url") or url),
        chapters=chapters,
        categories=list(info.get("categories") or []),
        tags=list(info.get("tags") or [])[:24],
        language=str(info.get("language") or ""),
        has_captions=bool(subs or autos),
        caption_langs=langs,
    )


def _save_caption_from_info(
    info: dict[str, Any],
    workdir: Path,
    video_id: str,
    *,
    log: LogHook,
) -> Path | None:
    preferred = ("en", "en-orig", "en-US", "en-GB", "hi", "hi-IN")
    buckets = [info.get("subtitles") or {}, info.get("automatic_captions") or {}]
    chosen_url = ""
    chosen_lang = ""
    for bucket in buckets:
        for lang in preferred:
            tracks = bucket.get(lang) or []
            url = _best_caption_url(tracks)
            if url:
                chosen_url, chosen_lang = url, lang
                break
        if chosen_url:
            break
        for lang, tracks in bucket.items():
            url = _best_caption_url(tracks)
            if url:
                chosen_url, chosen_lang = url, str(lang)
                break
        if chosen_url:
            break
    if not chosen_url:
        return None
    dest = workdir / f"{video_id}.{chosen_lang}.vtt"
    try:
        req = Request(chosen_url, headers={"User-Agent": "Mozilla/5.0 WatchListen/0.1"})
        with urlopen(req, timeout=30) as resp:
            payload = resp.read()
        if not payload:
            return None
        dest.write_bytes(payload)
        log(f"Saved captions ({chosen_lang}) → {dest.name}")
        return dest
    except Exception as exc:
        log(f"Could not download captions: {_short_error(exc)}")
        return None


def _best_caption_url(tracks: list[Any]) -> str:
    if not isinstance(tracks, list):
        return ""
    preferred_ext = ("vtt", "srt", "ttml")
    for ext in preferred_ext:
        for track in tracks:
            if not isinstance(track, dict):
                continue
            if str(track.get("ext") or "") == ext and track.get("url"):
                return str(track["url"])
    for track in tracks:
        if isinstance(track, dict) and track.get("url"):
            return str(track["url"])
    return ""


def _find_first(folder: Path, names: list[str]) -> Path | None:
    for name in names:
        candidate = folder / name
        if candidate.exists():
            return candidate
    return None


def _pick_caption(folder: Path, video_id: str) -> Path | None:
    preferred_suffixes = (".en.vtt", ".en-orig.vtt", ".hi.vtt", ".en.srt", ".vtt", ".srt")
    files = list(folder.iterdir())
    for suffix in preferred_suffixes:
        for path in files:
            if path.name.startswith(video_id) and path.name.endswith(suffix.lstrip(".")):
                return path
            if path.name.startswith(video_id) and path.suffix.lower() in {".vtt", ".srt"}:
                if suffix in path.name or path.suffix.lower() == suffix:
                    return path
    for path in files:
        if path.suffix.lower() in {".vtt", ".srt"}:
            return path
    return None


def _subtitle_opts() -> dict[str, Any]:
    return {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "vtt/srt/best",
        "subtitleslangs": ["en", "en-orig", "hi", "en.*", "hi.*"],
    }


def _short_error(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    return text[:180]


def _yt_dlp():
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover
        raise MediaError("yt-dlp is not installed. `pip install yt-dlp`.") from exc
    return yt_dlp


def _translate_ytdlp_error(exc: Exception, url: str, *, exhausted: bool = False) -> MediaError:
    message = str(exc)
    lowered = message.lower()
    if "private video" in lowered:
        return MediaError("This video is private. WatchListen cannot access it.")
    if "age-restricted" in lowered or "sign in to confirm your age" in lowered:
        return MediaError(
            "This video is age-restricted. Sign into YouTube in a browser and set "
            "download.cookies_from_browser (e.g. firefox) or --cookies-from-browser."
        )
    if "video unavailable" in lowered or (
        "not available" in lowered and "try again later" not in lowered
    ):
        return MediaError(
            "Video unavailable (removed, region-locked, or not a public YouTube video)."
        )
    if is_rate_limited(exc) or exhausted and is_recoverable(exc):
        hint = (
            "YouTube rate-limited this IP after several fallbacks "
            "(android_vr → tv → ios, then audio, then captions). "
            "Wait a few minutes, or sign into YouTube in Firefox/Chrome and rerun with "
            "`--cookies-from-browser firefox` so the request looks like a normal session."
        )
        return MediaError(hint)
    if isinstance(exc, URLValidationError):
        return MediaError(str(exc))
    return MediaError(f"Download failed for {url}: {message}")


def dump_info_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
