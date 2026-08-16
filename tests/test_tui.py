from __future__ import annotations

import pytest

from watchlisten.ui.app import WatchListenApp


@pytest.mark.asyncio
async def test_home_validates_youtube_url():
    app = WatchListenApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert type(app.screen).__name__ == "HomeScreen"
        inp = app.screen.query_one("#url-input")
        inp.value = "https://vimeo.com/123"
        await pilot.pause()
        assert app.screen.query_one("#go-btn").disabled is True
        inp.value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        await pilot.pause()
        assert app.screen.query_one("#go-btn").disabled is False


@pytest.mark.asyncio
async def test_help_and_settings_modals():
    app = WatchListenApp()
    async with app.run_test(size=(120, 42)) as pilot:
        await pilot.pause()
        app.screen.action_open_help()
        await pilot.pause()
        assert type(app.screen).__name__ == "HelpScreen"
        await pilot.press("escape")
        await pilot.pause()
        app.screen.action_open_settings()
        await pilot.pause()
        assert type(app.screen).__name__ == "SettingsScreen"
        await pilot.click("#set-cancel")
        await pilot.pause()
        assert type(app.screen).__name__ == "HomeScreen"
