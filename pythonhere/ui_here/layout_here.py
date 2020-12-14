"""Layouts."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.togglebutton import ToggleButton


class RootLayout(BoxLayout):
    """Application root layout."""

    def switch_screen(self, name: str):
        """Switch application screen manager to a given screen."""
        if name:
            self.ids.screen_manager.current = name
            for button in ToggleButton.get_widgets("screen"):
                button.state = "down" if button.screen == name else "normal"
