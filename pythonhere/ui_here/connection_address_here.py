"""Connection information widgets."""
from kivy.clock import Clock, mainthread
from kivy.logger import Logger
from kivy.properties import StringProperty  # pylint: disable=no-name-in-module
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout

from network_here import get_all_available_ipv4_adrresses


class ConnectionAddressLabel(Label):
    """Label with IPv4 address."""

    interface = StringProperty()
    address = StringProperty()


class ConnectionAddressInfoBox(GridLayout):
    """'Connect here via ...' information box."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Clock.schedule_once(self.show_device_ip_addresses, -1)

    @mainthread
    def show_device_ip_addresses(self, _):
        """Fill box with information about available IPv4 addresses."""
        box = self.ids.address_list
        try:
            for interface, address in get_all_available_ipv4_adrresses():
                box.add_widget(
                    ConnectionAddressLabel(interface=interface, address=address)
                )
        except Exception as exc:
            Logger.exception(exc)
