"""Canonical Markdown → styled HTML → PDF, with optional keyframe embeds."""

from __future__ import annotations

import html
import shutil
from collections.abc import Callable
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown import markdown as md_to_html

from watchlisten.config import Config
from watchlisten.models import ExportFormat, FrameDescription, NotesDocument
from watchlisten.utils import WatchListenError, format_timestamp, sanitize_filename

LogHook = Callable[[str], None]

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


class Exporter:
    def __init__(self, config: Config, *, on_log: LogHook | None = None) -> None:
        self.config = config
        self.on_log = on_log or (lambda _m: None)
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def export(
        self,
        notes: NotesDocument,
        dest_dir: Path,
        formats: list[ExportFormat],
        keyframes: list[FrameDescription] | None = None,
    ) -> dict[ExportFormat, Path]:
        dest_dir.mkdir(parents=True, exist_ok=True)
        stem = sanitize_filename(notes.title)
        written: dict[ExportFormat, Path] = {}

        md_path = dest_dir / f"{stem}.md"
        md_path.write_text(_ensure_trailing_newline(notes.markdown), encoding="utf-8")
        written[ExportFormat.MARKDOWN] = md_path
        self.on_log(f"Wrote Markdown → {md_path}")

        assets_dir = dest_dir / "assets"
        embedded = []
        if self.config.export.embed_frames:
            embedded = self._copy_keyframes(
                keyframes or notes.keyframes,
                assets_dir,
                self.config.export.max_embedded_frames,
            )

        need_html = ExportFormat.HTML in formats or ExportFormat.PDF in formats
        html_path = dest_dir / f"{stem}.html"
        if need_html:
            html_doc = self.render_html(notes, embedded)
            html_path.write_text(html_doc, encoding="utf-8")
            if ExportFormat.HTML in formats:
                written[ExportFormat.HTML] = html_path
                self.on_log(f"Wrote HTML → {html_path}")

        if ExportFormat.PDF in formats:
            pdf_path = dest_dir / f"{stem}.pdf"
            self.render_pdf(html_path, pdf_path)
            written[ExportFormat.PDF] = pdf_path
            self.on_log(f"Wrote PDF → {pdf_path}")

        # If the user only asked for HTML/PDF we still keep the canonical .md
        return written

    def render_html(self, notes: NotesDocument, frames: list[dict] | None = None) -> str:
        body = md_to_html(
            notes.markdown,
            extensions=["extra", "sane_lists", "smarty", "toc"],
            output_format="html5",
        )
        template = self._env.get_template("notes.html")
        meta = notes.metadata
        return template.render(
            title=html.escape(notes.title),
            raw_title=notes.title,
            body=body,
            url=meta.webpage_url or meta.url,
            channel=meta.channel or meta.uploader,
            duration=meta.duration,
            frames=frames or [],
            generated_by="WatchListen AI Notes",
        )

    def render_pdf(self, html_path: Path, pdf_path: Path) -> None:
        try:
            from weasyprint import HTML
        except ImportError as exc:
            raise WatchListenError(
                "PDF export needs WeasyPrint (`pip install weasyprint`) plus "
                "system libraries (cairo, pango, gdk-pixbuf). "
                "On Debian/Ubuntu: sudo apt install libpango-1.0-0 libpangocairo-1.0-0."
            ) from exc
        try:
            HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        except Exception as exc:
            raise WatchListenError(f"WeasyPrint failed to render PDF: {exc}") from exc

    def _copy_keyframes(
        self,
        frames: list[FrameDescription],
        assets_dir: Path,
        limit: int,
    ) -> list[dict]:
        noteworthy = [f for f in frames if f.noteworthy]
        chosen = (noteworthy or frames)[: max(limit, 0)]
        if not chosen:
            return []
        assets_dir.mkdir(parents=True, exist_ok=True)
        payload: list[dict] = []
        for idx, frame in enumerate(chosen, start=1):
            src = Path(frame.path)
            if not src.exists():
                continue
            dest = assets_dir / f"frame_{idx:02d}_{int(frame.timestamp)}s{src.suffix or '.jpg'}"
            shutil.copy2(src, dest)
            payload.append(
                {
                    "src": f"assets/{dest.name}",
                    "timestamp": format_timestamp(frame.timestamp),
                    "alt": (frame.description or "Keyframe")[:180],
                    "ocr": frame.ocr_text,
                }
            )
        return payload


def markdown_to_html_fragment(text: str) -> str:
    return md_to_html(text, extensions=["extra", "sane_lists", "smarty"], output_format="html5")


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"
