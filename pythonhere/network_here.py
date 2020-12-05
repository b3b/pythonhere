"""Network addresses discovering."""
from typing import Iterator, Tuple

from kivy import platform

if platform == "android":
    from jnius import autoclass  # pylint: disable=import-error

    NetworkInterface = autoclass("java.net.NetworkInterface")
    Inet4Address = autoclass("java.net.Inet4Address")


def get_android_interface_addresses(
    interface: "NetworkInterface",
) -> Iterator[Tuple[str, str]]:
    """Yields active IPv4 addresses for given network interface."""
    if interface.isUp():
        addresses = interface.getInetAddresses()
        while addresses.hasMoreElements():
            address = addresses.nextElement()
            if isinstance(address, Inet4Address) and not address.isLoopbackAddress():
                yield interface.getDisplayName(), address.getHostAddress()


def get_all_available_ipv4_adrresses() -> Iterator[Tuple[str, str]]:
    """Yields available interfaces with IPv4 addresses
    available for connections from there.
    """
    if platform == "android":
        interfaces = NetworkInterface.getNetworkInterfaces()
        while interfaces.hasMoreElements():
            yield from get_android_interface_addresses(interfaces.nextElement())
    else:
        yield ("???", "...")
