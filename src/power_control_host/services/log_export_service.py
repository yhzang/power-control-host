from __future__ import annotations

from pathlib import Path

import pandas as pd

from power_control_host.models import TelemetrySample


class LogExportService:
    def export_samples_to_excel(self, samples: list[TelemetrySample], target: Path) -> Path:
        rows = [
            {
                "device_id": sample.device_id,
                "channel": sample.channel,
                "voltage": sample.voltage,
                "current": sample.current,
                "mode": sample.mode,
            }
            for sample in samples
        ]
        dataframe = pd.DataFrame(rows)
        target.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_excel(target, index=False)
        return target

