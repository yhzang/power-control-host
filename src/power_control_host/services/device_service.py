from __future__ import annotations

from dataclasses import dataclass

from power_control_host.devices.base import PowerSupplyDevice
from power_control_host.devices.registry import build_device
from power_control_host.models import TelemetrySample
from power_control_host.settings import AppSettings


@dataclass(slots=True)
class DeviceIdentity:
    device_id: str
    model: str
    identity: str


class DeviceService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.devices = [build_device(item) for item in settings.devices]

    def list_devices(self) -> list[str]:
        return [f"{device.config.id} ({device.config.model})" for device in self.devices]

    def get_device(self, device_id: str) -> PowerSupplyDevice:
        for device in self.devices:
            if device.config.id == device_id:
                return device
        raise ValueError(f"未找到设备: {device_id}")

    def get_logical_channels(self, device_id: str) -> list[str]:
        return list(self.get_device(device_id).config.logical_channels)

    def identify_all(self) -> list[DeviceIdentity]:
        results: list[DeviceIdentity] = []
        for device in self.devices:
            device.connect()
            try:
                results.append(
                    DeviceIdentity(
                        device_id=device.config.id,
                        model=device.config.model,
                        identity=device.identify(),
                    )
                )
            finally:
                device.disconnect()
        return results

    def identify(self, device_id: str) -> DeviceIdentity:
        device = self.get_device(device_id)
        device.connect()
        try:
            return DeviceIdentity(
                device_id=device.config.id,
                model=device.config.model,
                identity=device.identify(),
            )
        finally:
            device.disconnect()

    def set_voltage(self, device_id: str, channel: str | None, value: float) -> str:
        device = self.get_device(device_id)
        resolved_channel = self._resolve_channel(device, channel)
        device.connect()
        try:
            device.set_voltage(resolved_channel, value)
            return resolved_channel
        finally:
            device.disconnect()

    def set_current(self, device_id: str, channel: str | None, value: float) -> str:
        device = self.get_device(device_id)
        resolved_channel = self._resolve_channel(device, channel)
        device.connect()
        try:
            device.set_current(resolved_channel, value)
            return resolved_channel
        finally:
            device.disconnect()

    def output_on(self, device_id: str, channel: str | None) -> str:
        device = self.get_device(device_id)
        resolved_channel = self._resolve_channel(device, channel)
        device.connect()
        try:
            device.output_on(resolved_channel)
            return resolved_channel
        finally:
            device.disconnect()

    def output_off(self, device_id: str, channel: str | None) -> str:
        device = self.get_device(device_id)
        resolved_channel = self._resolve_channel(device, channel)
        device.connect()
        try:
            device.output_off(resolved_channel)
            return resolved_channel
        finally:
            device.disconnect()

    def read_measurement(self, device_id: str, channel: str | None) -> TelemetrySample:
        device = self.get_device(device_id)
        resolved_channel = self._resolve_channel(device, channel)
        device.connect()
        try:
            return device.read_measurement(resolved_channel)
        finally:
            device.disconnect()

    def _resolve_channel(
        self, device: PowerSupplyDevice, channel: str | None
    ) -> str:
        if channel:
            return channel
        if device.config.logical_channels:
            return device.config.logical_channels[0]
        raise ValueError(f"设备 {device.config.id} 未配置逻辑通道，请在配置文件中补充。")

    @staticmethod
    def _parse_serial_number(idn_response: str) -> str:
        """Extract serial number (3rd comma-delimited field) from *IDN? response.

        Format: MANUFACTURER,MODEL,SERIAL,FIRMWARE
        Example: OWON,ODP3012,24320076,FV:V3.9.0 -> '24320076'
        """
        parts = idn_response.strip().split(",")
        if len(parts) >= 3:
            return parts[2].strip()
        return ""

    def get_device_serial_number(self, device_id: str) -> str:
        """Connect device and extract serial number from *IDN? response.

        Returns device_id as fallback on failure.
        """
        device = self.get_device(device_id)
        try:
            device.connect()
            try:
                idn = device.identify()
                serial = self._parse_serial_number(idn)
                return serial if serial else device_id
            finally:
                device.disconnect()
        except Exception:
            return device_id

    def list_devices_with_serial(self) -> list[dict[str, str]]:
        """List all devices with serial numbers.

        Returns list of dicts with keys: device_id, model, serial_number.
        serial_number is 'unknown' when query fails.
        """
        results: list[dict[str, str]] = []
        for device in self.devices:
            try:
                device.connect()
                try:
                    idn = device.identify()
                    serial = self._parse_serial_number(idn)
                    if not serial:
                        serial = "unknown"
                finally:
                    device.disconnect()
            except Exception:
                serial = "unknown"
            results.append(
                {
                    "device_id": device.config.id,
                    "model": device.config.model,
                    "serial_number": serial,
                }
            )
        return results
