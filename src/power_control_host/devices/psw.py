from __future__ import annotations

from power_control_host.devices.base import PowerSupplyDevice
from power_control_host.models import TelemetrySample


class PswPowerSupply(PowerSupplyDevice):
    """
    PSW 系列的命令骨架。

    PSW 常见是单输出，上层仍统一保留 channel 参数，方便和其它设备抽象一致。
    """

    def set_voltage(self, channel: str, value: float) -> None:
        self.transport.write(f"VOLT {value}")

    def set_current(self, channel: str, value: float) -> None:
        self.transport.write(f"CURR {value}")

    def output_on(self, channel: str) -> None:
        self.transport.write("OUTP ON")

    def output_off(self, channel: str) -> None:
        self.transport.write("OUTP OFF")

    def read_measurement(self, channel: str) -> TelemetrySample:
        voltage = self.transport.query("MEAS:VOLT?")
        current = self.transport.query("MEAS:CURR?")
        return TelemetrySample(
            device_id=self.config.id,
            channel=channel,
            voltage=_to_float(voltage),
            current=_to_float(current),
            raw={"voltage": voltage, "current": current},
        )


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

