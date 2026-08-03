## Android BLE using `able`

Use `able` package when the user asks for BLE (Bluetooth Low Energy) operations.
`able` is installed; do not need to check for import errors before normal use.

Core API:
- Import the BLE dispatcher with:
    from able import BluetoothDispatcher
- Create one shared dispatcher and keep it alive while BLE operations are needed:
    ble = BluetoothDispatcher()
- Reuse the shared dispatcher across `there` commands:
    if "ble" not in globals() or ble is None:
        ble = BluetoothDispatcher()
- Close the current GATT client with:
    ble.close_gatt()
- Start scanning with:
    ble.start_scan()
- Stop scanning with:
    ble.stop_scan()
- Connect to a scanned Java BluetoothDevice with:
    ble.connect_gatt(device, autoconnect=False)
- Connect directly by hardware address with:
    ble.connect_by_device_address(address, autoconnect=False)
- Discover services after connection with:
    ble.discover_services()
- Read a characteristic with:
    ble.read_characteristic(characteristic)
- Write a characteristic with:
    ble.write_characteristic(characteristic, value)
- Write a descriptor with:
    ble.write_descriptor(descriptor, value)
- Enable notifications with:
    ble.enable_notifications(characteristic, enable=True, indication=False)
- Disable notifications with:
    ble.enable_notifications(characteristic, enable=False)
- Request MTU with:
    ble.request_mtu(mtu)
- Update RSSI with:
    ble.update_rssi()
- Change queue timeout with:
    ble.set_queue_timeout(timeout)

Important constants:
- Import common constants when needed:
    from able import GATT_SUCCESS, STATE_CONNECTED, STATE_DISCONNECTED, WriteType
- `GATT_SUCCESS` is 0.
- `STATE_CONNECTED` is 2.
- `STATE_DISCONNECTED` is 0.
- `WriteType.SIGNED` can be used for signed characteristic writes when requested.

BLE dispatcher state:
- Use a global variable named `ble` for the shared `BluetoothDispatcher`.
- Do not create a new `BluetoothDispatcher` for every operation.
- Keep the dispatcher globally inspectable so later `there` commands can run:
    ble.adapter
    ble.bonded_devices
    ble.gatt
    ble.name
    ble.stop_scan()
    ble.close_gatt()
- Store discovered devices in a global dictionary such as:
    ble_devices_by_address
- Store the latest services in:
    ble_services
- Store recent events in:
    ble_events
- Store recent errors in:
    ble_errors
- Store compact status messages in:
    ble_status_messages
- Store the latest characteristic values in:
    ble_characteristic_values
- Store the latest notification values in:
    ble_notifications
- Store the latest scan summary in:
    ble_scan_summary
- Store the currently connected address in:
    ble_connected_address
- Store the last operation status in:
    ble_last_result

Recommended shared initialization:
    from able import BluetoothDispatcher

    if "ble_events" not in globals():
        ble_events = []

    if "ble_errors" not in globals():
        ble_errors = []

    if "ble_status_messages" not in globals():
        ble_status_messages = []

    if "ble_devices_by_address" not in globals():
        ble_devices_by_address = {}

    if "ble_characteristic_values" not in globals():
        ble_characteristic_values = {}

    if "ble_notifications" not in globals():
        ble_notifications = []

    if "ble_scan_summary" not in globals():
        ble_scan_summary = {}

    if "ble" not in globals() or ble is None:
        ble = BluetoothDispatcher()

Subclassing pattern:
- For scans, connections, services, reads, writes, notifications, RSSI, and MTU, prefer a small subclass of `BluetoothDispatcher` with event handlers.
- Reuse an existing subclass instance when possible.
- Keep callbacks short.
- Do not rely on `print(...)` inside BLE callbacks as the only output. BLE
  callbacks may run after `there run` output capture has ended. Store every event,
  result, and error in globals such as `ble_events`, `ble_errors`,
  `ble_devices_by_address`, `ble_services`, and `ble_notifications`.
- In BLE callbacks, prefer appending a compact tuple/dict to `ble_events` or a
  feature-specific global over printing. Use `print(...)` only in immediate
  synchronous code that runs before the `there run` command returns.
- Do not schedule delayed functions whose purpose is to print scan summaries.
  A delayed `Clock.schedule_once(...)` callback may run after `there run` output
  capture has ended. Store delayed summaries in globals such as
  `ble_scan_summary` and update visible UI/status messages instead.
- If the user asked for visible progress, update a Kivy status label or popup
  from callbacks using `Clock.schedule_once(...)`.
- Store Java objects by address or UUID-like key so later `there` commands can use them.
- Do not print huge advertisement dumps or service trees directly.
- Print compact immediate summaries from the initiating `there run` command and store full
  callback results globally.

Recommended dispatcher subclass skeleton:
    from able import BluetoothDispatcher, GATT_SUCCESS, STATE_CONNECTED, STATE_DISCONNECTED
    from kivy.clock import Clock

    def update_ble_status(message):
        ble_status_messages.append(str(message))
        label = globals().get("ble_status_label")
        if label is not None:
            Clock.schedule_once(lambda dt: setattr(label, "text", str(message)), 0)

    class PythonHereBLE(BluetoothDispatcher):
        def on_scan_started(self, success):
            ble_events.append(("scan_started", bool(success)))
            update_ble_status(f"BLE scan started: {bool(success)}")

        def on_scan_completed(self):
            ble_events.append(("scan_completed", None))
            update_ble_status("BLE scan completed")

        def on_device(self, device, rssi, advertisement):
            address = str(device.getAddress())
            try:
                name = device.getName()
                name = str(name) if name is not None else None
            except Exception:
                name = None

            ble_devices_by_address[address] = {
                "device": device,
                "address": address,
                "name": name,
                "rssi": int(rssi),
                "advertisement": advertisement,
            }
            ble_events.append(("device", address, int(rssi), name))
            update_ble_status(f"{len(ble_devices_by_address)} BLE devices found")

        def on_connection_state_change(self, status, state):
            global ble_connected_address
            ble_events.append(("connection_state_change", int(status), int(state)))

            if int(status) == GATT_SUCCESS and int(state) == STATE_CONNECTED:
                ble_connected_address = "connected"
                update_ble_status("BLE connected")
                self.discover_services()
            elif int(state) == STATE_DISCONNECTED:
                ble_connected_address = None
                update_ble_status("BLE disconnected")
            else:
                update_ble_status(f"BLE connection state: {status}, {state}")

        def on_services(self, services, status):
            global ble_services
            ble_events.append(("services", int(status)))
            if int(status) == GATT_SUCCESS:
                ble_services = services
                update_ble_status("BLE services discovered; stored in ble_services")
            else:
                update_ble_status(f"BLE service discovery failed: {status}")

        def on_characteristic_read(self, characteristic, status):
            uuid = str(characteristic.getUuid())
            value = list(characteristic.getValue() or [])
            ble_characteristic_values[uuid] = {
                "uuid": uuid,
                "status": int(status),
                "value": value,
                "characteristic": characteristic,
            }
            ble_events.append(("characteristic_read", uuid, int(status), value[:32]))
            update_ble_status(f"Characteristic read: {uuid} status={status}")

        def on_characteristic_write(self, characteristic, status):
            uuid = str(characteristic.getUuid())
            ble_events.append(("characteristic_write", uuid, int(status)))
            update_ble_status(f"Characteristic write: {uuid} status={status}")

        def on_characteristic_changed(self, characteristic):
            uuid = str(characteristic.getUuid())
            value = list(characteristic.getValue() or [])
            event = {
                "uuid": uuid,
                "value": value,
                "characteristic": characteristic,
            }
            ble_notifications.append(event)
            ble_events.append(("notification", uuid, value[:32]))
            update_ble_status(f"Notification: {uuid}")

        def on_descriptor_read(self, descriptor, status):
            uuid = str(descriptor.getUuid())
            ble_events.append(("descriptor_read", uuid, int(status)))
            update_ble_status(f"Descriptor read: {uuid} status={status}")

        def on_descriptor_write(self, descriptor, status):
            uuid = str(descriptor.getUuid())
            ble_events.append(("descriptor_write", uuid, int(status)))
            update_ble_status(f"Descriptor write: {uuid} status={status}")

        def on_rssi_updated(self, rssi, status):
            ble_events.append(("rssi_updated", int(rssi), int(status)))
            update_ble_status(f"RSSI: {int(rssi)} status={status}")

        def on_mtu_changed(self, mtu, status):
            ble_events.append(("mtu_changed", int(mtu), int(status)))
            update_ble_status(f"MTU: {int(mtu)} status={status}")

        def on_gatt_release(self):
            ble_events.append(("gatt_release", None))

        def on_error(self, msg):
            msg = str(msg)
            ble_errors.append(msg)
            update_ble_status(f"BLE error: {msg}")

    if "ble" not in globals() or ble is None or not isinstance(ble, PythonHereBLE):
        ble = PythonHereBLE()

Scanning:
- For simple scan requests, start scanning and schedule `ble.stop_scan()` after a short timeout.
- Do not scan indefinitely unless the user explicitly asks.
- Store devices by Bluetooth address in `ble_devices_by_address`.
- Store compact scan summaries in `ble_scan_summary`.
- Do not schedule delayed print summaries after scans. Print only one immediate
  line before the `there run` command returns, naming the globals where results will appear.
- If the user gives a name/address/service/manufacturer filter, use Able filters instead of scanning everything when possible.

Recommended simple scan:
    from kivy.clock import Clock

    def finish_ble_scan(dt):
        global ble_scan_summary
        try:
            ble.stop_scan()
        finally:
            sample = []
            for address, info in list(ble_devices_by_address.items())[:10]:
                sample.append({
                    "address": address,
                    "name": info.get("name"),
                    "rssi": info.get("rssi"),
                })
            ble_scan_summary = {
                "device_count": len(ble_devices_by_address),
                "sample": sample,
            }
            ble_events.append(("scan_summary", ble_scan_summary))
            update_ble_status(
                f"BLE scan complete: {ble_scan_summary['device_count']} device(s)"
            )

    ble.start_scan()
    Clock.schedule_once(finish_ble_scan, 8)
    print("Scanning for 8 seconds. Results will be stored in ble_devices_by_address and ble_scan_summary.")

Scan filters:
- Import filters from `able.filters` when needed:
    from able.filters import (
        EmptyFilter,
        DeviceAddressFilter,
        DeviceNameFilter,
        ManufacturerDataFilter,
        ServiceDataFilter,
        ServiceSolicitationFilter,
        ServiceUUIDFilter,
    )
- Use `DeviceNameFilter(name)` for exact device-name filtering.
- Use `DeviceAddressFilter("01:02:03:AB:CD:EF")` for a specific BLE address.
- Use `ServiceUUIDFilter(uuid)` for service UUID filtering.
- Use `ManufacturerDataFilter(id, data, mask=None)` for manufacturer data filtering.
- Use `ServiceDataFilter(uuid, data, mask=None)` for service data filtering.
- Filters of different kinds can be combined with `&`.
- Do not combine two filters of the same kind; Able raises `ValueError`.
- Pass filters as a list to `ble.start_scan(filters=[...])`.

Scan settings:
- Import scan setting builders when the user asks for scan mode, match mode, callback type, or low-latency scan tuning:
    from able.scan_settings import ScanSettingsBuilder, ScanSettings
- Use `ScanSettingsBuilder()` and builder methods for custom settings.
- Keep settings simple unless the user asks for advanced tuning.

Advertisement parsing:
- Use `able.Advertisement` objects received by `on_device`.
- Do not manually parse raw advertisement bytes unless the user asks.
- For readable summaries, iterate over the advertisement and store parsed AD structures.
- Keep manufacturer and service data as lists of integers or bytes-like values.

Services:
- `on_services(services, status)` receives an Able `Services` dict-like object.
- Store it globally as `ble_services`.
- Use `ble_services.search(pattern)` to find a characteristic by regex pattern.
- Do not assume a characteristic UUID exists before services are discovered.
- For user-provided UUID or partial UUID, search `ble_services` first.
- Store found characteristics in a global such as `ble_characteristics_by_name`.

Recommended characteristic search:
    characteristic = ble_services.search("2a37")
    if characteristic is None:
        print("Characteristic not found")
    else:
        print("Characteristic stored in characteristic")
        ble_characteristic = characteristic

Connecting:
- If the user gives a BLE address, use:
    ble.connect_by_device_address(address, autoconnect=False)
- If the user picks a scanned device, retrieve it from:
    ble_devices_by_address[address]["device"]
  then call:
    ble.connect_gatt(device, autoconnect=False)
- Validate address-like strings before direct connect when possible.
- Do not assume connection succeeds immediately; wait for `on_connection_state_change`.
- After successful connection, call `discover_services()` from the connection callback or instruct the user to run it after connection.
- Store connected state in globals.

Reads and writes:
- For reads, use a characteristic object from `ble_services.search(...)` or a previously stored characteristic.
- For writes, accept bytes, bytearray, or list of integers.
- Keep values in 0..255.
- Convert simple text only when the user clearly asks to send text.
- Do not write to characteristics discovered as read-only unless the user explicitly asks to try.
- Do not repeatedly write in a loop unless the user explicitly asks.
- Store write attempts and statuses in `ble_events`.

Notifications and indications:
- Use `ble.enable_notifications(characteristic, enable=True, indication=False)` for notifications.
- Use `indication=True` only when the user asks for indications or when the characteristic is known to require indications.
- Store received notification values in `ble_notifications`.
- Provide a disable command:
    ble.enable_notifications(characteristic, enable=False)

RSSI and MTU:
- Use `ble.update_rssi()` when the user asks for signal strength.
- Use `ble.request_mtu(mtu)` when the user asks to change MTU.
- Validate MTU as a reasonable positive integer before requesting.
- Do not assume MTU changed until `on_mtu_changed` reports status.

Advertising:
- Use advertising only when the user asks to advertise, broadcast, become a BLE peripheral advertiser, or send advertisement data.
- Import advertising helpers when needed:
    from able.advertising import (
        Advertiser,
        AdvertiseData,
        DeviceName,
        TXPowerLevel,
        ServiceUUID,
        ServiceData,
        ManufacturerData,
        Interval,
        TXPower,
        Status,
    )
- Create one global advertiser reference:
    ble_advertiser
- Stop existing advertising before starting a new advertiser if appropriate.
- Keep advertising payload small.
- Do not include private data in BLE advertisements.
- Store advertising status in:
    ble_advertising_result
- Provide a stop helper for advertising:
    def stop_ble_advertising():
        ble_advertiser.stop()

Advertising example:
    from able.advertising import Advertiser, AdvertiseData, DeviceName, TXPowerLevel, Interval, TXPower

    ble_advertiser = Advertiser(
        ble=ble,
        data=AdvertiseData(DeviceName()),
        scan_data=AdvertiseData(TXPowerLevel()),
        interval=Interval.HIGH,
        tx_power=TXPower.MEDIUM,
    )
    ble_advertiser.start()
    print("Started BLE advertising; advertiser stored in ble_advertiser")

Permissions:
- Able methods that require the Bluetooth adapter can request runtime permissions and ask the user to enable Bluetooth.
- Target API level <= 30 commonly needs `ACCESS_FINE_LOCATION` to obtain BLE scan results.
- Target API level >= 31 commonly needs `BLUETOOTH_CONNECT`, `BLUETOOTH_SCAN`, `ACCESS_FINE_LOCATION`, and sometimes `BLUETOOTH_ADVERTISE`.
- Able permission constants are available as:
    from able import Permission
    Permission.ACCESS_FINE_LOCATION
    Permission.ACCESS_BACKGROUND_LOCATION
    Permission.BLUETOOTH_CONNECT
    Permission.BLUETOOTH_SCAN
    Permission.BLUETOOTH_ADVERTISE
- The requested permission list can be overridden with:
    BluetoothDispatcher(runtime_permissions=[...])
- Do not duplicate generic Android permission request code here; use Able's dispatcher behavior or the always-enabled Android permissions prompt when the user explicitly asks for permission-specific checks.
- Do not claim BLE permissions are granted until the relevant operation callback or permission result confirms success.

Bluetooth adapter:
- `ble.adapter` returns the local Android BluetoothAdapter Java object or None.
- `ble.name` reads or sets the adapter name.
- `ble.bonded_devices` returns Java BluetoothDevice objects for paired devices.
- If the adapter is disabled, Able may launch the system activity to let the user enable Bluetooth.
- Do not assume BLE is available on all devices.

Diagnostics:
- For debugging, print readable compact diagnostics.
- Useful diagnostics include:
  - whether the shared `ble` object exists,
  - class name of `ble`,
  - `ble.adapter is not None`,
  - `ble.name`,
  - number of `ble.bonded_devices`,
  - number of discovered devices,
  - discovered device addresses/names/RSSI,
  - whether `ble.gatt` is not None,
  - whether `ble_services` exists,
  - recent `ble_events`,
  - recent `ble_errors`,
  - recent notifications.
- Do not print private data from arbitrary BLE payloads unless the user asks to inspect that payload.
- Do not access unrelated phone data such as contacts, SMS, call logs, files, camera, microphone, or location for BLE diagnostics.

Cleanup:
- For cleanup, prefer:
    ble.stop_scan()
    ble.close_gatt()
- For advertising cleanup, call:
    ble_advertiser.stop()
- For notification cleanup, disable notifications on the characteristic if known.
- Keep cleanup helpers simple and globally available:
    stop_ble_scan()
    disconnect_ble()
    stop_ble_advertising()
- Do not set `ble = None` unless the user asks to release the dispatcher itself.
- Do not leave scans or advertising running without a stop path.

Recommended cleanup helpers:
    def stop_ble_scan():
        try:
            ble.stop_scan()
            print("BLE scan stopped")
        except Exception as exc:
            print("Could not stop BLE scan:", repr(exc))

    def disconnect_ble():
        try:
            ble.close_gatt()
            print("BLE GATT closed")
        except Exception as exc:
            print("Could not close BLE GATT:", repr(exc))

    def stop_ble_advertising():
        if "ble_advertiser" not in globals() or ble_advertiser is None:
            print("No ble_advertiser global found")
            return
        try:
            ble_advertiser.stop()
            print("BLE advertising stopped")
        except Exception as exc:
            print("Could not stop BLE advertising:", repr(exc))

Good command examples:
- Initialize or reuse:
    from able import BluetoothDispatcher

    if "ble" not in globals() or ble is None:
        ble = BluetoothDispatcher()

- Scan briefly:
    from kivy.clock import Clock

    ble.start_scan()
    Clock.schedule_once(lambda dt: ble.stop_scan(), 8)

- Scan by device name:
    from able.filters import DeviceNameFilter
    from kivy.clock import Clock

    ble.start_scan(filters=[DeviceNameFilter("MyDevice")])
    Clock.schedule_once(lambda dt: ble.stop_scan(), 8)

- Connect by address:
    ble.connect_by_device_address("01:02:03:AB:CD:EF", autoconnect=False)

- Connect scanned device:
    device = ble_devices_by_address["01:02:03:AB:CD:EF"]["device"]
    ble.connect_gatt(device, autoconnect=False)

- Find a characteristic:
    characteristic = ble_services.search("2a37")

- Read a characteristic:
    ble.read_characteristic(characteristic)

- Write bytes:
    ble.write_characteristic(characteristic, bytes([1, 2, 3]))

- Enable notifications:
    ble.enable_notifications(characteristic, enable=True)

- Disable notifications:
    ble.enable_notifications(characteristic, enable=False)

- Request MTU:
    ble.request_mtu(247)

- Read RSSI:
    ble.update_rssi()

Avoid:
- Do not start endless scans.
- Do not connect repeatedly in a tight loop.
- Do not write repeatedly in a tight loop.
- Do not schedule delayed `print(...)` summaries for scan results.
- Do not assume scan, connect, services, read, write, notify, RSSI, or MTU operations are synchronous.
- Do not assume a BLE address, UUID, service, characteristic, or descriptor exists before checking.
- Do not print huge advertisement dumps, service trees, or notification streams directly.
- Do not include personal or sensitive data in BLE advertisements.

For simple user requests:
- If the user asks to scan, run a minimal Able scan program with a shared dispatcher, event handlers, `ble_devices_by_address`, and a scheduled stop.
- If the user asks to connect, use a scanned device or direct address and store connection events.
- If the user asks to list services, call `discover_services()` after connection and store `ble_services`.
- If the user asks to read, search or use the provided characteristic and call `read_characteristic`.
- If the user asks to write, validate the value and call `write_characteristic`.
- If the user asks for notifications, enable notifications and store values in `ble_notifications`.
- If the user asks to advertise, use `able.advertising` and store `ble_advertiser`.
- If the user asks for diagnostics, print compact BLE state and recent events.
- If the user asks for cleanup, stop scan, stop advertising if active, and close GATT.
