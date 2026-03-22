from __future__ import annotations

import argparse
from pathlib import Path

from power_control_host.app import create_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Reliability power host skeleton")
    parser.add_argument(
        "--config",
        default="config/devices.example.yaml",
        help="Path to YAML configuration file.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show-plan", help="Show the stage-1 checklist.")
    subparsers.add_parser("check-config", help="Validate config and print a summary.")
    subparsers.add_parser("show-devices", help="Print configured devices.")
    probe_parser = subparsers.add_parser("probe-idn", help="Query *IDN? from one device.")
    probe_parser.add_argument("--device", required=True, help="Configured device id.")

    measure_parser = subparsers.add_parser("measure", help="Read voltage/current from one device.")
    measure_parser.add_argument("--device", required=True, help="Configured device id.")
    measure_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")

    set_voltage_parser = subparsers.add_parser("set-voltage", help="Set output voltage.")
    set_voltage_parser.add_argument("--device", required=True, help="Configured device id.")
    set_voltage_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")
    set_voltage_parser.add_argument("--value", required=True, type=float, help="Target voltage.")

    set_current_parser = subparsers.add_parser("set-current", help="Set output current.")
    set_current_parser.add_argument("--device", required=True, help="Configured device id.")
    set_current_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")
    set_current_parser.add_argument("--value", required=True, type=float, help="Target current.")

    output_on_parser = subparsers.add_parser("output-on", help="Turn output on.")
    output_on_parser.add_argument("--device", required=True, help="Configured device id.")
    output_on_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")

    output_off_parser = subparsers.add_parser("output-off", help="Turn output off.")
    output_off_parser.add_argument("--device", required=True, help="Configured device id.")
    output_off_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")

    args = parser.parse_args()
    config_path = Path(args.config)

    if args.command == "show-plan":
        print_stage_1_plan()
        return 0

    app = create_app(config_path)

    if args.command == "check-config":
        print_config_summary(app)
        return 0

    if args.command == "show-devices":
        for item in app.device_service.list_devices():
            print(item)
        return 0

    if args.command == "probe-idn":
        identity = app.device_service.identify(args.device)
        print(f"{identity.device_id} ({identity.model}) -> {identity.identity}")
        return 0

    if args.command == "measure":
        sample = app.device_service.read_measurement(args.device, args.channel)
        print_measurement(sample)
        return 0

    if args.command == "set-voltage":
        channel = app.device_service.set_voltage(args.device, args.channel, args.value)
        print(f"已下发设压命令: device={args.device}, channel={channel}, voltage={args.value}")
        return 0

    if args.command == "set-current":
        channel = app.device_service.set_current(args.device, args.channel, args.value)
        print(f"已下发设流命令: device={args.device}, channel={channel}, current={args.value}")
        return 0

    if args.command == "output-on":
        channel = app.device_service.output_on(args.device, args.channel)
        print(f"已下发开输出命令: device={args.device}, channel={channel}")
        return 0

    if args.command == "output-off":
        channel = app.device_service.output_off(args.device, args.channel)
        print(f"已下发关输出命令: device={args.device}, channel={channel}")
        return 0

    return 0


def print_stage_1_plan() -> None:
    lines = [
        "第一阶段目标：先把设备打通，不急着做完整 GUI。",
        "",
        "建议顺序：",
        "1. 确认 ODP / PSW 现场型号、固件、接口照片",
        "2. 优先搭 LAN，准备交换机和网线",
        "3. 安装 Python、NI-VISA、厂家软件",
        "4. 复制并填写 devices.local.yaml",
        "5. 先跑配置检查",
        "6. 再写 *IDN?、设压、设流、开关输出验证",
        "",
        "第一批代码重点：",
        "- 配置加载",
        "- 传输层选择",
        "- ODP / PSW 设备对象",
        "- 最小通信验证脚本",
    ]
    print("\n".join(lines))


def print_config_summary(app) -> None:
    settings = app.settings
    print(f"应用名称: {settings.name}")
    print(f"运行环境: {settings.environment}")
    print(f"项目根目录: {settings.base_dir}")
    print(f"日志目录: {settings.directories.log_dir}")
    print(f"导出目录: {settings.directories.export_dir}")
    print(f"运行目录: {settings.directories.runtime_dir}")
    print("")
    print("设备清单:")
    for device in settings.devices:
        print(
            f"- {device.id} | vendor={device.vendor} | model={device.model} "
            f"| transport={device.transport.type}"
        )


def print_measurement(sample) -> None:
    print(f"device_id: {sample.device_id}")
    print(f"channel: {sample.channel}")
    print(f"voltage: {sample.voltage}")
    print(f"current: {sample.current}")
    if sample.raw:
        print(f"raw: {sample.raw}")
