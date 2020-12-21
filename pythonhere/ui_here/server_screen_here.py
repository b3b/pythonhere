"""%here server screen."""
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager

from enum_here import ServerState


class ServerScreenManager(ScreenManager):
    """Screen manager for server %here section."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_event = Clock.schedule_interval(self.update, 0.5)

    def update(self, _=None):
        """Determines server state, and switch to appropriate screen."""
        app = App.get_running_app()
        if app.ssh_server_config_ready.is_set():
            if app.ssh_server_started.is_set():
                self.current = ServerState.ready
                Clock.unschedule(self.update_event)
            else:
                self.current = ServerState.starting_server
        else:
            self.current = ServerState.not_configured
