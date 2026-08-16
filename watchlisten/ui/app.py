"""Textual application shell."""

from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from watchlisten.config import Config
from watchlisten.models import PipelineResult
from watchlisten.ui.screens import HomeScreen

CSS_PATH = Path(__file__).resolve().parent / "styles.tcss"


class WatchListenApp(App[None]):
    CSS_PATH = CSS_PATH
    TITLE = "WatchListen"
    SUB_TITLE = "local notes"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f1", "help", "Help"),
    ]

    def __init__(
        self,
        config: Config | None = None,
        *,
        initial_url: str | None = None,
    ) -> None:
        super().__init__()
        self.watch_config = config or Config.load()
        self.watch_result: PipelineResult | None = None
        self.initial_url = initial_url or ""

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

    def action_help(self) -> None:
        from watchlisten.ui.screens import HelpScreen

        if isinstance(self.screen, HelpScreen):
            return
        self.push_screen(HelpScreen())


def run_tui(config: Config | None = None, initial_url: str | None = None) -> None:
    WatchListenApp(config, initial_url=initial_url).run()
