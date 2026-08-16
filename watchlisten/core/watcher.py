"""Watch the video: scene-change frames + Ollama vision + optional OCR."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from watchlisten.config import Config
from watchlisten.models import FrameDescription
from watchlisten.utils import WatchListenError, format_timestamp, run_cmd, tesseract_available

LogHook = Callable[[str], None]
ProgressHook = Callable[[str, int, int, str], None]
CancelHook = Callable[[], bool]

VISION_PROMPT = """You are watching a single frame from a video, like a human glancing at the screen.

Describe ONLY what is visible. Be specific and concise (4–8 sentences max).
Cover, when present:
- On-screen text, slide titles, code, equations, diagrams, charts (quote text verbatim)
- People, gestures, objects, setting
- What action seems to be happening

End with exactly one line:
NOTEWORTHY: yes — <why this frame matters for notes>   OR   NOTEWORTHY: no
"""


class Watcher:
    def __init__(
        self,
        config: Config,
        *,
        on_progress: ProgressHook | None = None,
        on_log: LogHook | None = None,
        is_cancelled: CancelHook | None = None,
    ) -> None:
        self.config = config
        self.on_progress = on_progress or (lambda *_a: None)
        self.on_log = on_log or (lambda _m: None)
        self.is_cancelled = is_cancelled or (lambda: False)

    def analyze(self, video_path: Path, workdir: Path, duration: float) -> list[FrameDescription]:
        if self.is_cancelled():
            return []
        frames_dir = workdir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        timestamps = self.select_timestamps(video_path, duration)
        self.on_log(f"Selected {len(timestamps)} frames to watch")
        extracted = self.extract_frames(video_path, frames_dir, timestamps)
        described: list[FrameDescription] = []
        total = len(extracted)
        for idx, frame in enumerate(extracted, start=1):
            if self.is_cancelled():
                break
            self.on_progress("watch", idx - 1, total, f"frame @ {format_timestamp(frame.timestamp)}")
            if self.config.watcher.enable_ocr:
                frame.ocr_text = self.ocr_frame(frame.path)
            frame.description, frame.noteworthy = self.describe_frame(frame.path, frame.ocr_text)
            described.append(frame)
            preview = (frame.description or "")[:70].replace("\n", " ")
            self.on_log(f"[{format_timestamp(frame.timestamp)}] {preview}")
        self.on_progress("watch", total, total, f"{len(described)} frames")
        return described

    def select_timestamps(self, video_path: Path, duration: float) -> list[float]:
        cfg = self.config.watcher
        duration = max(float(duration or 0.0), 0.0)
        scene_ts = self._detect_scenes(video_path)
        if scene_ts:
            self.on_log(f"Scene detect found {len(scene_ts)} cuts")
            chosen = scene_ts
        else:
            step = max(cfg.interval_fallback, 3.0)
            self.on_log(f"No scene detector / no cuts — sampling every {step:.0f}s")
            if duration <= 0:
                chosen = [0.0]
            else:
                chosen = []
                t = min(1.0, duration * 0.02)
                while t < duration - 0.4:
                    chosen.append(round(t, 3))
                    t += step

        # Always include a near-start frame so title cards are not missed
        if duration > 0 and (not chosen or chosen[0] > 3.0):
            chosen.insert(0, min(1.0, duration / 4))

        chosen = _cap_timestamps(chosen, cfg.max_frames, duration)
        return chosen

    def extract_frames(
        self, video_path: Path, dest_dir: Path, timestamps: list[float]
    ) -> list[FrameDescription]:
        frames: list[FrameDescription] = []
        dest_dir.mkdir(parents=True, exist_ok=True)
        for ts in timestamps:
            if self.is_cancelled():
                break
            out = dest_dir / f"frame_{int(ts * 1000):09d}.jpg"
            ok = self._grab_frame_ffmpeg(video_path, ts, out)
            if not ok:
                ok = self._grab_frame_cv2(video_path, ts, out)
            if ok and out.exists():
                frames.append(FrameDescription(timestamp=ts, path=out))
            else:
                self.on_log(f"Could not extract frame at {format_timestamp(ts)}")
        return frames

    def describe_frame(self, image_path: Path, ocr_text: str = "") -> tuple[str, bool]:
        extra = ""
        if ocr_text.strip():
            extra = (
                "\n\nOCR (may be noisy, verify against the image) found this text:\n"
                f"{ocr_text.strip()[:800]}"
            )
        try:
            client = self._ollama()
            response = client.chat(
                model=self.config.models.vision,
                messages=[
                    {
                        "role": "user",
                        "content": VISION_PROMPT + extra,
                        "images": [str(image_path)],
                    }
                ],
                options={"temperature": 0.2},
            )
            content = _message_content(response)
        except Exception as exc:
            self.on_log(f"Vision model error on {image_path.name}: {exc}")
            if ocr_text.strip():
                return f"Vision unavailable. OCR text: {ocr_text.strip()}", True
            return f"(vision model failed: {exc})", False
        return _parse_noteworthy(content)

    def ocr_frame(self, image_path: Path) -> str:
        if not self.config.watcher.enable_ocr or not tesseract_available():
            return ""
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return ""
        try:
            with Image.open(image_path) as img:
                text = pytesseract.image_to_string(img) or ""
            return " ".join(text.split())
        except Exception as exc:
            self.on_log(f"OCR skipped for {image_path.name}: {exc}")
            return ""

    def describe_at(self, video_path: Path, dest_dir: Path, timestamp: float) -> FrameDescription:
        """On-demand frame (used by the watch_frame_at tool)."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        frames = self.extract_frames(video_path, dest_dir, [timestamp])
        if not frames:
            raise WatchListenError(f"Could not extract a frame at {format_timestamp(timestamp)}")
        frame = frames[0]
        if self.config.watcher.enable_ocr:
            frame.ocr_text = self.ocr_frame(frame.path)
        frame.description, frame.noteworthy = self.describe_frame(frame.path, frame.ocr_text)
        return frame

    def _detect_scenes(self, video_path: Path) -> list[float]:
        try:
            from scenedetect import ContentDetector, detect
        except ImportError:
            self.on_log("PySceneDetect not installed — using interval sampling.")
            return []
        try:
            threshold = self.config.watcher.scene_threshold
            min_len = max(int(self.config.watcher.min_scene_len * 2), 5)
            scenes = detect(
                str(video_path),
                ContentDetector(threshold=threshold, min_scene_len=min_len),
                show_progress=False,
            )
        except Exception as exc:
            self.on_log(f"Scene detection failed ({exc}); falling back to interval sampling.")
            return []
        stamps: list[float] = []
        for start, _end in scenes:
            try:
                stamps.append(float(start.get_seconds()))
            except Exception:
                continue
        return stamps

    def _grab_frame_ffmpeg(self, video_path: Path, timestamp: float, dest: Path) -> bool:
        quality = max(2, min(31, int(round((100 - self.config.watcher.jpeg_quality) / 3))))
        result = run_cmd(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-q:v",
                str(quality),
                "-y",
                str(dest),
            ],
            timeout=60,
        )
        return result.returncode == 0 and dest.exists() and dest.stat().st_size > 0

    def _grab_frame_cv2(self, video_path: Path, timestamp: float, dest: Path) -> bool:
        try:
            import cv2
        except ImportError:
            return False
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return False
        cap.set(cv2.CAP_PROP_POS_MSEC, max(timestamp, 0.0) * 1000.0)
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            return False
        return bool(cv2.imwrite(str(dest), frame))

    def _ollama(self):
        import ollama

        host = self.config.resolved_ollama_host()
        return ollama.Client(host=host)


def _cap_timestamps(stamps: list[float], max_frames: int, duration: float) -> list[float]:
    cleaned: list[float] = []
    for ts in stamps:
        if ts < 0:
            continue
        if duration and ts > duration:
            continue
        cleaned.append(float(ts))
    cleaned = sorted(set(round(t, 3) for t in cleaned))
    if max_frames <= 0 or len(cleaned) <= max_frames:
        return cleaned
    # Evenly sample across the selected scene cuts so we don't only keep the start
    if max_frames == 1:
        return [cleaned[0]]
    out: list[float] = []
    last_idx = len(cleaned) - 1
    for i in range(max_frames):
        idx = round(i * last_idx / (max_frames - 1))
        out.append(cleaned[idx])
    # unique, stable
    uniq: list[float] = []
    seen: set[float] = set()
    for t in out:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq


def _message_content(response: object) -> str:
    if isinstance(response, dict):
        msg = response.get("message") or {}
        if isinstance(msg, dict):
            return str(msg.get("content") or "")
    message = getattr(response, "message", None)
    if message is not None:
        return str(getattr(message, "content", "") or "")
    return str(response or "")


def _parse_noteworthy(content: str) -> tuple[str, bool]:
    text = (content or "").strip()
    noteworthy = True
    lines = text.splitlines()
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("NOTEWORTHY:"):
            rest = stripped.split(":", 1)[1].strip().lower()
            noteworthy = not rest.startswith("no")
            continue
        kept.append(line)
    return "\n".join(kept).strip(), noteworthy
