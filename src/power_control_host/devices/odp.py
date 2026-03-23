from __future__ import annotations

from power_control_host.devices.base import PowerSupplyDevice
from power_control_host.models import TelemetrySample


class OdpPowerSupply(PowerSupplyDevice):
    """
    ODP 双路设备的命令骨架。

    这里先按常见 SCPI 风格预留接口，后续要以现场手册和设备返回结果逐条校正。
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
        voltage = self.transport.query("MEAS:VOLT?")
        current = self.transport.query("MEAS:CURR?")
        return TelemetrySample(
            device_id=self.config.id,
            channel=channel,
            voltage=_to_float(voltage),
            current=_to_float(current),
            raw={"voltage": voltage, "current": current},
        )

    def _select_channel(self, channel: str) -> None:
        self.transport.write(f"INST {channel}")


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

