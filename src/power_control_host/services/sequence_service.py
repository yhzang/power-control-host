from __future__ import annotations

from power_control_host.models import SequencePlan, SequenceStep


class SequenceService:
    def build_simple_startup_plan(self) -> SequencePlan:
        """
        这里只提供一个极小骨架。

        后续会根据“后上先下”“相对延时”需求，扩展成完整时序编排器。
        """

        return SequencePlan(
            name="placeholder_startup_plan",
            steps=[
                SequenceStep(device_id="odp_01", channel="CH1", action="set_voltage", voltage=12.0),
                SequenceStep(device_id="odp_01", channel="CH1", action="output_on", delay_seconds=0.0),
            ],
        )

