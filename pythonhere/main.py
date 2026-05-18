"""PythonHere app."""

# pylint: disable=wrong-import-order,wrong-import-position

from launcher_here import try_startup_script

try:
    try_startup_script()  # run script entrypoint, if it was passed
except Exception as exc:
    startup_script_exception = exc  # pylint: disable=invalid-name
else:
    startup_script_exception = None  # pylint: disable=invalid-name

import asyncio
import os
import sys
import threading
from pathlib import Path
from typing import Any

from enum_here import ScreenName, ServerState
from exception_manager_here import install_exception_handler, show_exception_popup
from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config, ConfigParser
from kivy.logger import Logger
from patches_here import monkeypatch_kivy
from server_here import run_ssh_server
from window_here import reset_window_environment

monkeypatch_kivy()


class PythonHereApp(App):
    """PythonHere main app."""

    def __init__(self):
        super().__init__()
        self.server_task: asyncio.Task | None = None
        self.app_task: asyncio.Task | None = None
        self.asyncio_loop: asyncio.AbstractEventLoop | None = None
        self.settings = None

        # Created once a running asyncio loop exists.
        self.ssh_server_config_ready: asyncio.Event | None = None
        self.ssh_server_started: asyncio.Event | None = None
        self.ssh_server_connected: asyncio.Event | None = None

        self.ssh_server_namespace = {}
        self.icon = "data/logo/logo-32.png"

    def init_asyncio_state(self):
        """Initialize asyncio-owned state after the event loop is running."""
        self.asyncio_loop = asyncio.get_running_loop()
        self.ssh_server_config_ready = asyncio.Event()
        self.ssh_server_started = asyncio.Event()
        self.ssh_server_connected = asyncio.Event()

    @property
    def upload_dir(self) -> str:
        """Path to the directory to use for uploaded data."""
        root_dir = Path(self.user_data_dir or ".").resolve()
        upload_dir = Path(root_dir) / "upload"
        upload_dir.mkdir(exist_ok=True)
        return str(upload_dir)

    @property
    def config_path(self) -> str:
        """Path to the application config file."""
        root_dir = Path(self.user_data_dir or ".").resolve()
        return str(root_dir / "config.ini")

    def load_config(self) -> ConfigParser:
        """Returning the application configuration."""
        Config.read(self.config_path)  # Override the configuration file location
        return super().load_config()

    def build(self):
        """Initialize application UI."""
        super().build()
        install_exception_handler()
        self.settings = self.root.ids.settings
        self.ssh_server_namespace.update(
            {
                "app": self,
                "root": self.root,
            }
        )
        self.update_server_config_status()
        if startup_script_exception:
            Clock.schedule_once(
                lambda _: show_exception_popup(startup_script_exception), 0
            )

    async def run_app(self):
        """Run application and SSH server until either main task exits."""
        self.init_asyncio_state()

        self.server_task = asyncio.create_task(run_ssh_server(self))
        self.app_task = asyncio.create_task(self.async_run_app())

        tasks = (self.server_task, self.app_task)

        try:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

            for task in done:
                if task.cancelled():
                    continue
                exc = task.exception()
                if exc is not None:
                    raise exc
        finally:
            await self.cancel_app_tasks()

    async def async_run_app(self):
        """Run app asynchronously."""
        try:
            await self.async_run()
            Logger.info("PythonHere: async run completed")
        except asyncio.CancelledError:
            Logger.info("PythonHere: app main task canceled")
            raise
        except Exception as exc:
            Logger.exception(exc)
            raise
        finally:
            if self.get_running_app():
                self.stop()

    async def cancel_app_tasks(self):
        """Cancel tasks owned by this app."""
        tasks = [
            task
            for task in (self.server_task, self.app_task)
            if task is not None
            and task is not asyncio.current_task()
            and not task.done()
        ]

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def update_server_config_status(self):
        """Check and update value of the `ssh_server_config_ready`, update screen."""

        def update():
            if all(self.get_pythonhere_config().values()):
                if (
                    self.asyncio_loop is not None
                    and self.ssh_server_config_ready is not None
                ):
                    self.asyncio_loop.call_soon_threadsafe(
                        self.ssh_server_config_ready.set
                    )

            Clock.schedule_once(lambda _: screen.update(), 0)

        screen = self.root.ids.here_screen_manager
        screen.current = ServerState.starting_server
        self.root.switch_screen(ScreenName.here)
        threading.Thread(name="update_server_config_status", target=update).start()

    def get_pythonhere_config(self):
        """Return user settings for SSH server."""
        return self.settings.get_pythonhere_config()

    def update_ssh_server_namespace(self, namespace: dict[str, Any]):
        """Update SSH server namespace."""
        self.ssh_server_namespace.update(namespace)

    def on_start(self):
        """App start handler."""
        Logger.info("PythonHere: app started")

    def on_stop(self):
        """App stop handler."""
        Logger.info("PythonHere: app stopped")

    def on_pause(self):
        """Pause mode request handler."""
        return True

    def on_ssh_connection_made(self):
        """New authenticated SSH client connected handler."""
        Logger.info("PythonHere: new SSH client connected")

        if self.ssh_server_connected is None:
            Logger.warning("PythonHere: SSH connected before asyncio state was ready")
            return

        if not self.ssh_server_connected.is_set():
            self.ssh_server_connected.set()

            Logger.info("PythonHere: reset window environment")
            self.ssh_server_namespace["root"] = reset_window_environment()
            self.chdir(self.upload_dir)

    def chdir(self, path: str):
        """Changes the working directory."""
        Logger.info("PythonHere: change working directory to %s", path)
        os.chdir(path)
        sys.path.insert(0, path)


async def main():
    """Run PythonHere."""
    app = PythonHereApp()
    await app.run_app()


if __name__ == "__main__":
    asyncio.run(main())
