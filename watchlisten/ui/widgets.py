"""Reusable TUI widgets."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static

from watchlisten.models import DepStatus, Stage, StageStatus
from watchlisten.utils import format_duration

STAGE_ORDER = (
    Stage.VALIDATE,
    Stage.METADATA,
    Stage.DOWNLOAD,
    Stage.LISTEN,
    Stage.WATCH,
    Stage.TIMELINE,
    Stage.NOTES,
    Stage.EXPORT,
)

_STATUS_GLYPH = {
    StageStatus.PENDING: "·",
    StageStatus.RUNNING: "▶",
    StageStatus.DONE: "✓",
    StageStatus.SKIPPED: "–",
    StageStatus.ERROR: "✗",
}

_STATUS_STYLE = {
    StageStatus.PENDING: "dim",
    StageStatus.RUNNING: "bold #2dd4bf",
    StageStatus.DONE: "#2dd4bf",
    StageStatus.SKIPPED: "dim",
    StageStatus.ERROR: "bold #fb7185",
}


class BrandBar(Widget):
    def compose(self) -> ComposeResult:
        yield Label("◉  WATCHLISTEN", id="brand-mark")
        yield Label("AI notes from any YouTube video", id="brand-sub")
        yield Label("local  ·  private  ·  ollama", id="brand-privacy")


class DepBadges(Static):
    """Tiny status strip: ffmpeg ✓  ollama ✓  whisper · …"""

    def show(self, deps: DepStatus) -> None:
        bits = [
            _badge("ffmpeg", deps.ffmpeg),
            _badge("ollama", deps.ollama_reachable),
            _badge("whisper", deps.whisper),
            _badge("ocr", deps.tesseract),
            _badge("pdf", deps.weasyprint),
        ]
        self.update("   ".join(bits))


def _badge(name: str, ok: bool) -> str:
    mark = "✓" if ok else "·"
    colour = "#2dd4bf" if ok else "#8b949e"
    return f"[{colour}]{name} {mark}[/]"


class StageList(Static):
    states: reactive[dict[str, tuple[str, str]]] = reactive(dict, always_update=True)

    def reset(self) -> None:
        self.states = {
            stage.value: (StageStatus.PENDING.value, "") for stage in STAGE_ORDER
        }
        self.refresh_view()

    def set_stage(self, stage: Stage, status: StageStatus, detail: str = "") -> None:
        current = dict(self.states)
        current[stage.value] = (status.value, detail)
        self.states = current
        self.refresh_view()

    def refresh_view(self) -> None:
        lines: list[str] = []
        for stage in STAGE_ORDER:
            status_raw, detail = self.states.get(
                stage.value, (StageStatus.PENDING.value, "")
            )
            try:
                status = StageStatus(status_raw)
            except ValueError:
                status = StageStatus.PENDING
            glyph = _STATUS_GLYPH[status]
            style = _STATUS_STYLE[status]
            extra = f"  [dim]{detail[:36]}[/]" if detail else ""
            lines.append(f"[{style}]{glyph}  {stage.label:<22}[/]{extra}")
        self.update("\n".join(lines))

    def on_mount(self) -> None:
        self.reset()


class MetaBox(Static):
    def show_meta(self, title: str, channel: str, duration: float, chapters: int, captions: bool) -> None:
        caps = "captions" if captions else "no captions"
        ch = f"{chapters} chapter{'s' if chapters != 1 else ''}" if chapters else "no chapters"
        self.update(
            f"[b]{title}[/]\n[dim]{channel or 'Unknown channel'}  ·  "
            f"{format_duration(duration)}  ·  {ch}  ·  {caps}[/]"
        )
        self.add_class("visible")

    def hide_meta(self) -> None:
        self.update("")
        self.remove_class("visible")
