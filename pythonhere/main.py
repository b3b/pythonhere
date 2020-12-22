"""PythonHere app."""
import asyncio

from kivy.app import App
from kivy.logger import Logger

from enum_here import ScreenName
from patches_here import monkeypatch_kivy
from server_here import run_ssh_server
from window_here import reset_window_environment

monkeypatch_kivy()


class PythonHereApp(App):
    """PythonHere main app."""

    def __init__(self):
        super().__init__()
        self.server_task = None
        self.settings = None
        self.ssh_server_config_ready = asyncio.Event()
        self.ssh_server_started = asyncio.Event()
        self.ssh_server_connected = asyncio.Event()
        self.ssh_server_namespace = {}
        self.icon = "data/logo/logo-32.png"

    def build(self):
        """Initialize application UI."""
        super().build()

        self.settings = self.root.ids.settings

        self.ssh_server_namespace.update(
            {
                "app": self,
                "root": self.root,
            }
        )

        self.update_server_config_status()
        self.root.switch_screen(
            ScreenName.here
            if self.ssh_server_config_ready.is_set()
            else ScreenName.settings
        )

    def run_app(self):
        """Run application and SSH server tasks."""
        self.ssh_server_started = asyncio.Event()
        self.server_task = asyncio.ensure_future(run_ssh_server(self))
        return asyncio.gather(self.async_run_app(), self.server_task)

    async def async_run_app(self):
        """Run app asynchronously."""
        try:
            await self.async_run(async_lib="asyncio")
            Logger.info("PythonHere: async run completed")
        except asyncio.CancelledError:
            Logger.info("PythonHere: app main task canceled")
        except Exception as exc:
            Logger.exception(exc)

        if self.server_task:
            self.server_task.cancel()

    def update_server_config_status(self):
        """Check and update value of the `ssh_server_config_ready`."""
        if all(self.get_pythonhere_config().values()):
            self.ssh_server_config_ready.set()

    def get_pythonhere_config(self):
        """Return user settings for SSH server."""
        return self.settings.get_pythonhere_config()

    def on_start(self):
        """App start handler."""
        Logger.info("PythonHere: app started")

    def on_stop(self):
        """App stop handler."""
        Logger.info("PythonHere: app stopped")

    def on_ssh_connection_made(self):
        """New SSH client connected handler."""
        if not self.ssh_server_connected.is_set():
            self.ssh_server_connected.set()
            self.ssh_server_namespace["root"] = reset_window_environment()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(PythonHereApp().run_app())
    loop.close()
