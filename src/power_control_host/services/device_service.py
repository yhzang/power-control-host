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
