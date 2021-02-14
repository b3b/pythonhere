---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.2'
      jupytext_version: 1.7.1
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

# Android Bluetooth Low Energy functions
BLE functions could be used with the [able](https://herethere.me/able) library.

```python
%load_ext pythonhere
%connect-there
```

```python
%%there
from kivy.logger import Logger
from able import BluetoothDispatcher, GATT_SUCCESS
```

BLE dispatcher callbacks results should be printed in logs:

```python
%there -b log
```

## Setup BLE interface
with logging callbacks

```python
%%there
class BLE(BluetoothDispatcher):

    def on_connection_state_change(self, status, state):
        Logger.info("on_connection_state_change: status=%s, state=%s", status, state)
        if status == GATT_SUCCESS and state:
            Logger.info("Connection: succeed")

    def on_services(self, status, services):
        Logger.info("on_services: status=%s", status)
        if status == GATT_SUCCESS:
            Logger.info("services discovered: %s", list(services.keys()))
            # save discovered services object
            self.services = services

    def on_characteristic_read(self, characteristic, status):
        Logger.info("on_characteristic_read: status=%s, characteristic=%s", status,
                    characteristic.getUuid().toString())
        if status == GATT_SUCCESS:
            Logger.info("Characteristic read: succeed")


ble = BLE()
print(ble)
```

## Get list of paired BLE devices

```python
%%there
for device in ble.bonded_devices:
    # device: https://developer.android.com/reference/android/bluetooth/BluetoothDevice
    print(type(device), device.getName(), "address:", device.getAddress())
```

## Connect to remote device by a hardware address
In this example device hardware address address is known.

```python
%%there
ble.connect_by_device_address("AA:AA:AA:AA:AA:11")
```

## Discover device services and characteristics
Wait a while, while device is connected. Start services discovery:

```python
%%there -d 5
ble.discover_services()
```

Wait a while, while services discovered. Print connected device characteristics:

```python
%%there -d 2
print(type(ble.services))
for service, characteristics in ble.services.items():
    print(f"Service {service} characteristics:")
    for characteristic in characteristics:
        print(f"\t*{characteristic}")
```

## Read characteristic
In this example, it is known that target device has characteristic
with UUID = 16fe**0d01**-c111-11e3-b8c8-0002a5d5c51b  
This characteristic is readable, and always returns a string value: "test".

```python
%%there
characteristic = ble.services.search("0d01")  
print(f"Characteristic UUID found: {characteristic.getUuid().toString()}")
print(f"Characteristic object: {characteristic}")
# https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic#getStringValue(int)
print(f"Characteristic value is not available yet: {characteristic.getStringValue(0)}")

ble.read_characteristic(characteristic)
```

Wait a while, and check characteristic value.  
**on_characteristic_read** message should appear in logs

```python
%%there -d 2
# https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic#getStringValue(int)
print(characteristic.getStringValue(0))
```
