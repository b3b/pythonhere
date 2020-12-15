"""Python Here app."""
import asyncio

from kivy.app import App
from kivy.logger import Logger

from enum_here import ScreenName
from herethere.here import ServerConfig, start_server
from patches_here import monkeypatch_kivy

monkeypatch_kivy()


async def run_ssh_server(app):
    """Start and run SSH server."""
    Logger.debug("Python Here: wait for %here settings")
    try:
        await app.ssh_server_config_ready.wait()
    except asyncio.CancelledError:
        return

    config = ServerConfig(
        host="",
        chroot=app.user_data_dir or "",
        key_path="./key.rsa",
        **app.get_pythonhere_config(),
    )

    try:
        server = await start_server(config, namespace=app.ssh_server_namespace)
        app.ssh_server_started.set()
    except Exception as exc:
        Logger.error("Python Here: SSH server start error")
        Logger.exception(exc)
        raise

    try:
        await server.wait_closed()
    except asyncio.CancelledError:
        Logger.info("Python Here: SSH server task canceled")
        server.close()
    except Exception as exc:
        Logger.errror("Python Here: SSH server stop by exception")
        Logger.exception(exc)
        raise
    Logger.info("Python Here: SSH server closed")


class PythonHereApp(App):
    """Python Here main app."""

    def __init__(self):
        super().__init__()
        self.server_task = None
        self.settings = None
        self.ssh_server_config_ready = asyncio.Event()
        self.ssh_server_started = asyncio.Event()
        self.ssh_server_namespace = {}

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

        self.settings.bind(on_config_change=self.handle_config_change)
        self.update_server_config_status()
        self.root.switch_screen(ScreenName.here)

    def run_app(self):
        """Run application and SSH server tasks."""
        self.ssh_server_started = asyncio.Event()
        self.server_task = asyncio.ensure_future(run_ssh_server(self))
        return asyncio.gather(self.async_run_app(), self.server_task)

    async def async_run_app(self):
        """Run app asynchronously."""
        try:
            await self.async_run(async_lib="asyncio")
            Logger.info("Python Here: async run completed")
        except asyncio.CancelledError:
            Logger.info("Python Here: app main task canceled")
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

    def handle_config_change(
        self, settings, config, section, key, value
    ):  # pylint: disable=too-many-arguments, unused-argument
        """Config change handler."""
        if section == "pythonhere":
            self.update_server_config_status()

    def on_start(self):
        """App start handler."""
        Logger.info("Python Here: app started")

    def on_stop(self):
        """App stop handler."""
        Logger.info("Python Here: app stopped")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(PythonHereApp().run_app())
    loop.close()
