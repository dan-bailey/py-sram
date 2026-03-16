"""
SRAM AXS Bluetooth Low Energy Connection Module
Handles discovery and connection to SRAM AXS cycling components
"""

import asyncio
from bleak import BleakScanner, BleakClient
from typing import Dict, Optional, List, Callable
import struct

# SRAM AXS Service and Characteristic UUIDs
SRAM_SERVICE_UUID = "00001818-0000-1000-8000-00805f9b34fb"  # Cycling Power Service
WAHOO_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"  # Heart Rate Service
QUARQ_POWER_UUID = "00001818-0000-1000-8000-00805f9b34fb"  # Cycling Power Service

# Standard Bluetooth SIG UUIDs
CYCLING_POWER_MEASUREMENT = "00002a63-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"


class SRAMDevice:
    """Represents a single SRAM AXS or compatible BLE device"""

    def __init__(self, name: str, address: str, device_type: str):
        self.name = name
        self.address = address
        self.device_type = device_type
        self.client: Optional[BleakClient] = None
        self.data: Dict = {}
        self.connected = False

    async def connect(self):
        """Connect to the device"""
        try:
            self.client = BleakClient(self.address)
            await self.client.connect()
            self.connected = True
            print(f"Connected to {self.name}")
        except Exception as e:
            print(f"Failed to connect to {self.name}: {e}")
            self.connected = False

    async def disconnect(self):
        """Disconnect from the device"""
        if self.client and self.connected:
            await self.client.disconnect()
            self.connected = False
            print(f"Disconnected from {self.name}")

    async def start_notifications(self, callback: Callable):
        """Start receiving notifications from the device"""
        if not self.client or not self.connected:
            return

        try:
            if self.device_type == "power_meter":
                await self.client.start_notify(
                    CYCLING_POWER_MEASUREMENT,
                    lambda sender, data: self._handle_power_data(data, callback)
                )
            elif self.device_type == "heart_rate":
                await self.client.start_notify(
                    HEART_RATE_MEASUREMENT,
                    lambda sender, data: self._handle_hr_data(data, callback)
                )
        except Exception as e:
            print(f"Error starting notifications for {self.name}: {e}")

    def _handle_power_data(self, data: bytearray, callback: Callable):
        """Parse cycling power measurement data"""
        # Cycling Power Measurement format (see Bluetooth SIG specification)
        flags = struct.unpack('<H', data[0:2])[0]

        power = 0
        cadence = 0

        # Instantaneous Power is always present
        if len(data) >= 4:
            power = struct.unpack('<h', data[2:4])[0]

        # Check if Crank Revolution Data is present (bit 5 of flags)
        if flags & 0x20 and len(data) >= 8:
            cumulative_crank_revs = struct.unpack('<H', data[4:6])[0]
            last_crank_event_time = struct.unpack('<H', data[6:8])[0]
            # Calculate cadence if we have previous data
            if hasattr(self, '_prev_crank_revs'):
                rev_diff = cumulative_crank_revs - self._prev_crank_revs
                time_diff = (last_crank_event_time - self._prev_crank_time) / 1024  # Convert to seconds
                if time_diff > 0:
                    cadence = int((rev_diff / time_diff) * 60)
            self._prev_crank_revs = cumulative_crank_revs
            self._prev_crank_time = last_crank_event_time

        self.data = {
            "device": self.name,
            "type": "power",
            "power_watts": power,
            "cadence_rpm": cadence
        }
        callback(self.data)

    def _handle_hr_data(self, data: bytearray, callback: Callable):
        """Parse heart rate measurement data"""
        # Heart Rate Measurement format
        flags = data[0]
        hr_format = flags & 0x01

        if hr_format == 0:
            # Heart Rate Value Format is UINT8
            heart_rate = data[1]
        else:
            # Heart Rate Value Format is UINT16
            heart_rate = struct.unpack('<H', data[1:3])[0]

        self.data = {
            "device": self.name,
            "type": "heart_rate",
            "bpm": heart_rate
        }
        callback(self.data)


class SRAMManager:
    """Manages multiple SRAM AXS and compatible BLE devices"""

    def __init__(self):
        self.devices: List[SRAMDevice] = []
        self.scanning = False

    async def scan_devices(self, duration: int = 10) -> List[SRAMDevice]:
        """Scan for SRAM AXS and compatible devices"""
        print(f"Scanning for devices for {duration} seconds...")
        self.scanning = True

        devices_found = await BleakScanner.discover(timeout=duration)

        for device in devices_found:
            name = device.name or "Unknown"

            # Identify SRAM AXS, Wahoo, and Quarq devices
            if "SRAM" in name.upper() or "AXS" in name.upper():
                sram_device = SRAMDevice(name, device.address, "shifter")
                self.devices.append(sram_device)
                print(f"Found SRAM device: {name}")

            elif "WAHOO" in name.upper() or "TRACKR" in name.upper():
                wahoo_device = SRAMDevice(name, device.address, "heart_rate")
                self.devices.append(wahoo_device)
                print(f"Found Wahoo device: {name}")

            elif "QUARQ" in name.upper() or "POWER" in name.upper():
                quarq_device = SRAMDevice(name, device.address, "power_meter")
                self.devices.append(quarq_device)
                print(f"Found Quarq device: {name}")

        self.scanning = False
        print(f"Scan complete. Found {len(self.devices)} compatible devices.")
        return self.devices

    async def connect_all(self):
        """Connect to all discovered devices"""
        tasks = [device.connect() for device in self.devices]
        await asyncio.gather(*tasks)

    async def disconnect_all(self):
        """Disconnect from all devices"""
        tasks = [device.disconnect() for device in self.devices]
        await asyncio.gather(*tasks)

    async def start_all_notifications(self, callback: Callable):
        """Start notifications on all connected devices"""
        tasks = [device.start_notifications(callback) for device in self.devices]
        await asyncio.gather(*tasks)

    def get_all_data(self) -> Dict:
        """Get current data from all devices"""
        return {
            device.name: device.data
            for device in self.devices
            if device.connected and device.data
        }
