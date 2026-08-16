"""CLI + TUI entry point: `watchlisten` or `python -m watchlisten`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from watchlisten import __app_name__, __version__
from watchlisten.config import Config
from watchlisten.models import ExportFormat, Stage, StageStatus
from watchlisten.pipeline import Pipeline, PipelineCancelled, PipelineHooks
from watchlisten.utils import CancelledError, WatchListenError, probe_dependencies

console = Console(stderr=False)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        console.print(f"{__app_name__} {__version__}")
        return 0

    config = Config.load(Path(args.config) if args.config else None)
    _apply_cli_overrides(config, args)

    if args.check:
        return _cmd_check(config)

    url = args.url
    want_tui = args.tui or not url
    if want_tui and not args.cli:
        from watchlisten.ui.app import run_tui

        run_tui(config, initial_url=url)
        return 0

    if not url:
        parser.error("a YouTube URL is required in CLI mode (or omit it to launch the TUI)")

    try:
        return _cmd_run(config, url, args)
    except (PipelineCancelled, CancelledError):
        console.print("[yellow]Cancelled.[/]")
        return 130
    except WatchListenError as exc:
        console.print(f"[red]{exc}[/]")
        return 2
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/]")
        return 130


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="watchlisten",
        description=(
            "Watch and listen to a YouTube video locally (Ollama + Whisper) "
            "and export structured notes as Markdown, HTML, or PDF."
        ),
    )
    parser.add_argument("url", nargs="?", help="YouTube URL (omit to launch the TUI)")
    parser.add_argument("-f", "--format", dest="formats", default=None, help="md,html,pdf")
    parser.add_argument("-o", "--output", dest="output", default=None, help="Output directory")
    parser.add_argument("--vision-model", dest="vision", default=None)
    parser.add_argument("--text-model", dest="text", default=None)
    parser.add_argument("--whisper-model", dest="whisper", default=None)
    parser.add_argument("--config", dest="config", default=None, help="Path to config.toml")
    parser.add_argument("--agentic", action="store_true", help="Let the text model call watch/listen tools")
    parser.add_argument("--skip-vision", action="store_true", help="Transcribe only; do not watch frames")
    parser.add_argument("--captions-only", action="store_true", help="Use YouTube captions instead of Whisper")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--keep-media", action="store_true")
    parser.add_argument(
        "--cookies-from-browser",
        dest="cookies_from_browser",
        default=None,
        help="firefox, chrome, brave, edge, chromium, or auto — used if YouTube rate-limits the guest session",
    )
    parser.add_argument(
        "--cookies",
        dest="cookiefile",
        default=None,
        help="Netscape cookies.txt exported from a logged-in YouTube tab",
    )
    parser.add_argument("--proxy", dest="proxy", default=None, help="HTTP/SOCKS proxy for yt-dlp")
    parser.add_argument("--tui", action="store_true", help="Force the terminal UI")
    parser.add_argument("--cli", action="store_true", help="Force headless CLI mode")
    parser.add_argument("--check", action="store_true", help="Probe local dependencies and exit")
    parser.add_argument("--version", action="store_true")
    return parser


def _apply_cli_overrides(config: Config, args: argparse.Namespace) -> None:
    if args.vision:
        config.models.vision = args.vision
    if args.text:
        config.models.text = args.text
    if args.whisper:
        config.models.whisper = args.whisper
    if args.output:
        config.export.output_dir = args.output
    if args.formats:
        config.export.formats = [f.value for f in ExportFormat.parse_many(args.formats)]
    if args.agentic:
        config.notes.agentic = True
    if args.max_frames:
        config.watcher.max_frames = args.max_frames
    if args.keep_media:
        config.keep_media = True
    if args.cookies_from_browser:
        config.download.cookies_from_browser = args.cookies_from_browser
    if args.cookiefile:
        config.download.cookiefile = args.cookiefile
    if args.proxy:
        config.download.proxy = args.proxy


def _cmd_check(config: Config) -> int:
    deps = probe_dependencies(config.resolved_ollama_host())
    table = Table(title="WatchListen environment", show_header=True, header_style="bold")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Detail")
    table.add_row("ffmpeg", _ok(deps.ffmpeg), "required for download + frames")
    table.add_row("ollama", _ok(deps.ollama_reachable), config.resolved_ollama_host())
    table.add_row("faster-whisper", _ok(deps.whisper), "optional if captions exist")
    table.add_row("tesseract OCR", _ok(deps.tesseract), "optional on-screen text")
    table.add_row("weasyprint", _ok(deps.weasyprint), "required only for PDF")
    table.add_row("opencv", _ok(deps.opencv), "frame fallback")
    table.add_row("PySceneDetect", _ok(deps.scenedetect), "scene-change frames")
    console.print(table)
    if deps.all_models:
        console.print("Installed Ollama models: " + ", ".join(deps.all_models))
        if deps.vision_models:
            console.print("Vision-like: " + ", ".join(deps.vision_models))
    elif not deps.ollama_reachable:
        console.print("[yellow]Start Ollama with `ollama serve`, then `ollama pull llama3.1` and a vision model.[/]")
    return 0 if deps.ready_to_run else 1


def _ok(flag: bool) -> str:
    return "[green]yes[/]" if flag else "[red]no[/]"


def _cmd_run(config: Config, url: str, args: argparse.Namespace) -> int:
    formats = ExportFormat.parse_many(args.formats) if args.formats else config.export_formats
    console.print(
        Panel.fit(
            f"[bold]{__app_name__}[/]  watch · listen · note\n[dim]{url}[/]",
            border_style="yellow",
        )
    )

    current_task: dict[str, int | None] = {"id": None}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        overall = progress.add_task("Running pipeline", total=len(Stage))
        finished_stages: set[Stage] = set()

        def on_log(message: str) -> None:
            console.log(message)

        def on_stage(stage: Stage, status: StageStatus, detail: str) -> None:
            label = stage.label
            if detail:
                label = f"{label} — {detail}"
            if status is StageStatus.RUNNING:
                tid = current_task["id"]
                if tid is not None:
                    progress.remove_task(tid)
                current_task["id"] = progress.add_task(label, total=None)
            elif status in {StageStatus.DONE, StageStatus.SKIPPED, StageStatus.ERROR}:
                if stage not in finished_stages:
                    finished_stages.add(stage)
                    progress.advance(overall, 1)
                tid = current_task["id"]
                if tid is not None:
                    progress.update(tid, description=f"{label} ({status.value})")

        def on_progress(stage: str, current: int, total: int, message: str) -> None:
            tid = current_task["id"]
            if tid is None:
                return
            desc = f"{stage}: {message}" if message else stage
            if total > 0:
                progress.update(tid, total=total, completed=current, description=desc)
            else:
                progress.update(tid, description=desc)

        hooks = PipelineHooks(on_log=on_log, on_progress=on_progress, on_stage=on_stage)
        result = Pipeline(config, hooks).run(
            url,
            formats=formats,
            skip_vision=bool(args.skip_vision),
            captions_only=bool(args.captions_only),
        )

    console.print("\n[bold green]Notes written[/]")
    for fmt, path in result.exports.items():
        console.print(f"  [yellow]{fmt.value:<4}[/] {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
