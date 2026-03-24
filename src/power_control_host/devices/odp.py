from __future__ import annotations

from power_control_host.devices.base import PowerSupplyDevice
from power_control_host.models import TelemetrySample


class OdpPowerSupply(PowerSupplyDevice):
    """
    ODP 电源驱动。

    当前已通过真实设备确认：
    - `*IDN?`
    - `INST CH1`
    - `VOLT`
    - `CURR`
    - `OUTP ON/OFF`
    - `MEAS:VOLT?`

    另外，这台 ODP3012 的 `MEAS:CURR?` 返回的不是单值，而是一组 `#` 分隔的状态块。
    当前先按已知格式从“实测电流块”里提取指定通道的电流值。
    """

    def set_voltage(self, channel: str, value: float) -> None:
        self._select_channel(channel)
        self.transport.write(f"VOLT {value}")

    def set_current(self, channel: str, value: float) -> None:
        self._select_channel(channel)
        self.transport.write(f"CURR {value}")

    def output_on(self, channel: str) -> None:
        self._select_channel(channel)
        self.transport.write("OUTP ON")

    def output_off(self, channel: str) -> None:
        self._select_channel(channel)
        self.transport.write("OUTP OFF")

    def read_measurement(self, channel: str) -> TelemetrySample:
        self._select_channel(channel)
        voltage_response = self.transport.query("MEAS:VOLT?")
        current_response = self.transport.query("MEAS:CURR?")
        return TelemetrySample(
            device_id=self.config.id,
            channel=channel,
            voltage=_to_float(voltage_response),
            current=_parse_odp_current_block(current_response, channel),
            raw={
                "voltage": voltage_response,
                "current": current_response,
            },
        )

    def _select_channel(self, channel: str) -> None:
        self.transport.write(f"INST {channel}")


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_odp_current_block(value: str, channel: str) -> float | None:
    direct = _to_float(value)
    if direct is not None:
        return direct

    blocks = [item.strip() for item in value.split("#") if item.strip()]
    if len(blocks) < 4:
        return None

    channel_index = _channel_index(channel)
    if channel_index is None:
        return None

    current_block = [item.strip() for item in blocks[3].split(",")]
    if channel_index >= len(current_block):
        return None

    return _to_float(current_block[channel_index])


def _channel_index(channel: str) -> int | None:
    normalized = channel.strip().upper()
    if normalized.startswith("CH") and normalized[2:].isdigit():
        return int(normalized[2:]) - 1
    return None
