# UI 功能调用说明

本文档记录后续 GUI 可直接复用的后端能力。建议 UI 优先调用 Python service/function，不要通过解析 CLI 文本驱动界面；CLI 只作为人工调试入口。

## 设备扫描

UI 推荐字段：

| 字段 | 默认值 | 说明 |
|---|---:|---|
| `subnet` | `192.168.1` | 扫描网段前三段，例如 `192.168.10` 表示扫描 `192.168.10.1-254` |
| `odp_port` | `4196` | ODP socket 端口 |
| `psw_port` | `2268` | PSW socket 端口 |
| `timeout_ms` | `1000` | 每个端口探测超时 |
| `workers` | `100` | 并发扫描线程数 |

Python 调用：

```python
from power_control_host.discovery import devices_to_yaml, scan_subnet

devices = scan_subnet(
    "192.168.10",
    timeout_ms=1000,
    workers=100,
    odp_port=4196,
    psw_port=2268,
)
yaml_text = devices_to_yaml(devices)
```

CLI 等价命令：

```powershell
power-control-host scan-devices --subnet 192.168.10 --odp-port 4196 --psw-port 2268 --emit-yaml
```

`scan_subnet()` 返回 `DiscoveredDevice` 列表，UI 可展示这些字段：

| 字段 | 说明 |
|---|---|
| `suggested_id` | 自动建议的设备 ID，例如 `odp_01`、`psw_01` |
| `host` | 设备 IP |
| `port` | 实际发现端口 |
| `vendor` | `owon` 或 `gwinstek` |
| `model` | 设备型号 |
| `idn` | 原始 `*IDN?` 返回 |
| `suggested_channels` | 自动推断的逻辑通道 |

一台仪器也可以测试扫描链路；只接 ODP 时只能验证 ODP 扫描，只接 PSW 时只能验证 PSW 扫描。

## 单设备连通

已配置设备连通确认：

```powershell
power-control-host --config config/devices.local.yaml probe-idn --device odp_01
```

批量显示配置设备；不带 `--with-serial` 时不连接设备，适合快速显示列表：

```powershell
power-control-host --config config/devices.local.yaml show-devices
power-control-host --config config/devices.local.yaml show-devices --with-serial
```

后续 UI 可用 `DeviceService.identify()`、`DeviceService.list_devices()`、`DeviceService.list_devices_with_serial()` 实现同等能力。

## 单设备控制

基础控制入口：

```powershell
power-control-host --config config/devices.local.yaml measure --device odp_01 --channel CH1
power-control-host --config config/devices.local.yaml set-voltage --device odp_01 --channel CH1 --value 5.0
power-control-host --config config/devices.local.yaml set-current --device odp_01 --channel CH1 --value 0.5
power-control-host --config config/devices.local.yaml output-on --device odp_01 --channel CH1
power-control-host --config config/devices.local.yaml output-off --device odp_01 --channel CH1
```

后续 UI 可用 `DeviceService.read_measurement()`、`set_voltage()`、`set_current()`、`output_on()`、`output_off()` 实现按钮和实时读数。

## 时序执行

单通道循环：

```powershell
power-control-host --config config/devices.local.yaml run-cycle --device odp_01 --channel CH1 --on-seconds 3 --off-seconds 2 --cycles 5
```

单设备多通道相对时序：

```powershell
power-control-host --config config/devices.local.yaml run-relative-cycle ^
  --device odp_01 --on-seconds 13 --off-seconds 2 --cycles 4 ^
  --channel-spec "CH1:voltage=12,current=1" ^
  --channel-spec "CH2:ref=CH1,on_delay=5,off_advance=5,voltage=5,current=0.5"
```

多设备 JSON 时序：

```powershell
power-control-host --config config/devices.local.yaml run-multi-device-timing --config-file my_timing.json
```

后续 UI 推荐直接构造 `MultiDeviceTimingSpec`，调用 `SequenceService.build_multi_device_timing_plan()` 预览计划，再调用 `execute_plan_with_pool()` 执行。

## 日志与结果展示

时序命令默认写入：

```text
runtime/sequence_logs/<plan_name>_<timestamp>.csv
```

UI 执行后建议展示：

| 字段 | 说明 |
|---|---|
| `plan_name` | 时序计划名称 |
| `step_count` | 已记录事件数 |
| `log_file` | CSV 日志路径 |
| `last_events` | 最近几条执行事件 |

`SequenceExecutionEvent` 包含 `timestamp`、`plan_name`、`step_index`、`device_id`、`channel`、`action`、`detail`，可直接用于 UI 表格。
