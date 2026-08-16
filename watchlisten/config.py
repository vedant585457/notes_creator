"""Load / save WatchListen configuration from TOML + environment overrides."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - py<3.11 not supported
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w

from watchlisten.models import ExportFormat


APP_DIR_NAME = "watchlisten"
DEFAULT_VISION_MODELS = (
    "llama3.2-vision",
    "llava",
    "qwen2.5vl",
    "moondream",
    "minicpm-v",
    "bakllava",
)
DEFAULT_TEXT_MODELS = (
    "llama3.1",
    "qwen2.5",
    "mistral-nemo",
    "llama3.2",
    "gemma2",
    "phi3",
)


def default_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / APP_DIR_NAME / "config.toml"


def default_cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / APP_DIR_NAME


def default_output_dir() -> Path:
    return Path.cwd() / "notes"


@dataclass(slots=True)
class ModelsConfig:
    vision: str = "llama3.2-vision"
    text: str = "llama3.1"
    whisper: str = "base"


@dataclass(slots=True)
class WhisperConfig:
    device: str = "auto"  # auto | cpu | cuda
    compute_type: str = "auto"  # auto | int8 | int8_float16 | float16 | float32
    language: str = "auto"
    vad_filter: bool = True
    prefer_captions: bool = False


@dataclass(slots=True)
class WatcherConfig:
    max_frames: int = 36
    min_scene_len: float = 8.0
    interval_fallback: float = 12.0
    scene_threshold: float = 27.0
    enable_ocr: bool = True
    jpeg_quality: int = 85


@dataclass(slots=True)
class NotesConfig:
    language: str = "auto"
    chunk_minutes: float = 8.0
    temperature: float = 0.3
    agentic: bool = False
    max_tool_rounds: int = 8


@dataclass(slots=True)
class ExportConfig:
    output_dir: str = "./notes"
    formats: list[str] = field(default_factory=lambda: ["md", "html"])
    embed_frames: bool = True
    max_embedded_frames: int = 16


@dataclass(slots=True)
class Config:
    models: ModelsConfig = field(default_factory=ModelsConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    watcher: WatcherConfig = field(default_factory=WatcherConfig)
    notes: NotesConfig = field(default_factory=NotesConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    cache_dir: str = ""
    keep_media: bool = False
    ollama_host: str = ""

    # --- helpers ---------------------------------------------------------

    @property
    def cache_path(self) -> Path:
        return Path(self.cache_dir).expanduser() if self.cache_dir else default_cache_dir()

    @property
    def output_path(self) -> Path:
        return Path(self.export.output_dir).expanduser().resolve()

    @property
    def export_formats(self) -> list[ExportFormat]:
        return ExportFormat.parse_many(self.export.formats)

    def resolved_ollama_host(self) -> str:
        return (
            self.ollama_host
            or os.environ.get("OLLAMA_HOST")
            or "http://127.0.0.1:11434"
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "models": asdict(self.models),
            "whisper": asdict(self.whisper),
            "watcher": asdict(self.watcher),
            "notes": asdict(self.notes),
            "export": asdict(self.export),
            "cache_dir": self.cache_dir,
            "keep_media": self.keep_media,
            "ollama_host": self.ollama_host,
        }
        return data

    def save(self, path: Path | None = None) -> Path:
        path = path or default_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(tomli_w.dumps(self.to_dict()).encode("utf-8"))
        return path

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Config:
        data = data or {}
        cfg = cls()
        if "models" in data and isinstance(data["models"], dict):
            cfg.models = _fill(ModelsConfig, data["models"])
        if "whisper" in data and isinstance(data["whisper"], dict):
            cfg.whisper = _fill(WhisperConfig, data["whisper"])
        if "watcher" in data and isinstance(data["watcher"], dict):
            cfg.watcher = _fill(WatcherConfig, data["watcher"])
        if "notes" in data and isinstance(data["notes"], dict):
            cfg.notes = _fill(NotesConfig, data["notes"])
        if "export" in data and isinstance(data["export"], dict):
            cfg.export = _fill(ExportConfig, data["export"])
        if "cache_dir" in data and data["cache_dir"] is not None:
            cfg.cache_dir = str(data["cache_dir"])
        if "keep_media" in data and data["keep_media"] is not None:
            cfg.keep_media = bool(data["keep_media"])
        if "ollama_host" in data and data["ollama_host"] is not None:
            cfg.ollama_host = str(data["ollama_host"])
        return cfg

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        """Load first existing of: explicit path, ./watchlisten.toml, XDG config."""
        candidates: list[Path] = []
        if path is not None:
            candidates.append(Path(path))
        candidates.append(Path.cwd() / "watchlisten.toml")
        candidates.append(default_config_path())

        data: dict[str, Any] = {}
        for candidate in candidates:
            if candidate.is_file():
                with candidate.open("rb") as fh:
                    loaded = tomllib.load(fh) or {}
                if isinstance(loaded, dict):
                    data = loaded
                break
        cfg = cls.from_dict(data)
        return _apply_env(cfg)


def _fill(cls: type, data: dict[str, Any]) -> Any:
    allowed = {f.name for f in fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in allowed}
    return cls(**kwargs)


def _apply_env(cfg: Config) -> Config:
    """Lightweight overrides so operators can tweak without a file."""
    models = cfg.models
    export = cfg.export
    extra: dict[str, Any] = {}
    if value := os.environ.get("WATCHLISTEN_VISION_MODEL"):
        models = replace(models, vision=value)
    if value := os.environ.get("WATCHLISTEN_TEXT_MODEL"):
        models = replace(models, text=value)
    if value := os.environ.get("WATCHLISTEN_WHISPER_MODEL"):
        models = replace(models, whisper=value)
    if value := os.environ.get("WATCHLISTEN_OUTPUT_DIR"):
        export = replace(export, output_dir=value)
    if value := os.environ.get("WATCHLISTEN_OLLAMA_HOST") or os.environ.get("OLLAMA_HOST"):
        extra["ollama_host"] = value
    return replace(cfg, models=models, export=export, **extra)
