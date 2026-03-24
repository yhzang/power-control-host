from __future__ import annotations

import argparse
from pathlib import Path

from power_control_host.app import create_app
from power_control_host.devices.odp import OdpPowerSupply
from power_control_host.models import DeviceVendor, TransportType
from power_control_host.settings import DeviceConfig, TransportConfig
from power_control_host.transports.socket_transport import (
    SocketTransport,
    run_socket_command,
)
from power_control_host.transports.visa_transport import (
    list_visa_resources,
    probe_visa_resource,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reliability power host skeleton")
    parser.add_argument(
        "--config",
        default="config/devices.local.yaml",
        help="Path to YAML configuration file.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("show-plan", help="Show the current checklist.")
    subparsers.add_parser("check-config", help="Validate config and print a summary.")
    subparsers.add_parser("show-devices", help="Print configured devices.")
    subparsers.add_parser(
        "list-visa-resources",
        help="List VISA resources currently visible on this computer.",
    )

    probe_visa_parser = subparsers.add_parser(
        "probe-visa",
        help="Send *IDN? or a custom command to a raw VISA resource without YAML config.",
    )
    probe_visa_parser.add_argument(
        "--resource",
        required=True,
        help="Exact VISA resource string, for example USB0::...::INSTR",
    )
    probe_visa_parser.add_argument(
        "--scpi",
        default="*IDN?",
        help="SCPI command to send. Defaults to *IDN?",
    )
    probe_visa_parser.add_argument(
        "--timeout-ms",
        type=int,
        default=3000,
        help="Timeout in milliseconds.",
    )

    socket_parser = subparsers.add_parser(
        "socket-scpi",
        help="Send one SCPI command directly to a TCP socket.",
    )
    socket_parser.add_argument("--host", required=True, help="Socket host or device IP.")
    socket_parser.add_argument("--port", required=True, type=int, help="Socket port.")
    socket_parser.add_argument("--scpi", required=True, help="SCPI command to send.")
    socket_parser.add_argument(
        "--timeout-ms",
        type=int,
        default=3000,
        help="Timeout in milliseconds.",
    )
    socket_parser.add_argument(
        "--write-only",
        action="store_true",
        help="Only send the command, do not wait for a response.",
    )

    odp_smoke_parser = subparsers.add_parser(
        "odp-socket-smoke",
        help="Run a guided ODP socket smoke test without YAML config.",
    )
    odp_smoke_parser.add_argument("--host", required=True, help="ODP IP address.")
    odp_smoke_parser.add_argument("--port", required=True, type=int, help="ODP socket port.")
    odp_smoke_parser.add_argument("--channel", default="CH1", help="ODP logical channel.")
    odp_smoke_parser.add_argument(
        "--timeout-ms",
        type=int,
        default=3000,
        help="Timeout in milliseconds.",
    )
    odp_smoke_parser.add_argument(
        "--voltage",
        type=float,
        help="If provided, send the voltage set command.",
    )
    odp_smoke_parser.add_argument(
        "--current",
        type=float,
        help="If provided, send the current set command.",
    )
    odp_smoke_parser.add_argument(
        "--output-on",
        action="store_true",
        help="Turn output on after optional setpoint commands.",
    )
    odp_smoke_parser.add_argument(
        "--measure",
        action="store_true",
        help="Query measurement after optional setpoint/output commands.",
    )
    odp_smoke_parser.add_argument(
        "--output-off",
        action="store_true",
        help="Turn output off at the end.",
    )

    probe_parser = subparsers.add_parser("probe-idn", help="Query *IDN? from one configured device.")
    probe_parser.add_argument("--device", required=True, help="Configured device id.")

    measure_parser = subparsers.add_parser("measure", help="Read voltage/current from one configured device.")
    measure_parser.add_argument("--device", required=True, help="Configured device id.")
    measure_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")

    set_voltage_parser = subparsers.add_parser("set-voltage", help="Set output voltage on one configured device.")
    set_voltage_parser.add_argument("--device", required=True, help="Configured device id.")
    set_voltage_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")
    set_voltage_parser.add_argument("--value", required=True, type=float, help="Target voltage.")

    set_current_parser = subparsers.add_parser("set-current", help="Set output current on one configured device.")
    set_current_parser.add_argument("--device", required=True, help="Configured device id.")
    set_current_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")
    set_current_parser.add_argument("--value", required=True, type=float, help="Target current.")

    output_on_parser = subparsers.add_parser("output-on", help="Turn output on for one configured device.")
    output_on_parser.add_argument("--device", required=True, help="Configured device id.")
    output_on_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")

    output_off_parser = subparsers.add_parser("output-off", help="Turn output off for one configured device.")
    output_off_parser.add_argument("--device", required=True, help="Configured device id.")
    output_off_parser.add_argument("--channel", help="Logical channel name. Defaults to first configured channel.")

    args = parser.parse_args()

    if args.command == "show-plan":
        print_stage_1_plan()
        return 0

    if args.command == "list-visa-resources":
        resources = list_visa_resources()
        if not resources:
            print("没有发现 VISA 资源。请先检查设备、驱动和 NI-VISA。")
            return 0
        print("当前可见 VISA 资源:")
        for item in resources:
            print(f"- {item}")
        return 0

    if args.command == "probe-visa":
        response = probe_visa_resource(
            resource=args.resource,
            command=args.scpi,
            timeout_ms=args.timeout_ms,
        )
        print(f"resource: {args.resource}")
        print(f"command: {args.scpi}")
        print(f"response: {response}")
        return 0

    if args.command == "socket-scpi":
        response = run_socket_command(
            host=args.host,
            port=args.port,
            command=args.scpi,
            timeout_ms=args.timeout_ms,
            expect_response=not args.write_only,
        )
        print(f"host: {args.host}")
        print(f"port: {args.port}")
        print(f"command: {args.scpi}")
        if args.write_only:
            print("result: sent")
        else:
            print(f"response: {response}")
        return 0

    if args.command == "odp-socket-smoke":
        run_odp_socket_smoke(args)
        return 0

    config_path = Path(args.config)
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
        "当前第一阶段目标：先把 ODP 单机 socket 链路跑稳，不急着做 GUI 和多设备。",
        "",
        "建议顺序：",
        "1. 固定 ODP 的型号、IP、端口、通道名",
        "2. 用 socket-scpi 跑通 *IDN?",
        "3. 逐条验证 INST / VOLT / CURR / OUTP / MEAS",
        "4. 用 odp-socket-smoke 再走一遍高层命令链",
        "5. 确认 ODP 驱动里的命令格式",
        "6. ODP 稳定后再补回 PSW",
        "7. 最后再进入 40 台设备的调度和采样设计",
        "",
        "当前代码重点：",
        "- ODP socket 原始命令入口",
        "- ODP 高层驱动命令校正",
        "- 配置大小写兼容",
        "- 多设备扩展预留",
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


def run_odp_socket_smoke(args) -> None:
    device = _build_temp_odp_device(
        host=args.host,
        port=args.port,
        channel=args.channel,
        timeout_ms=args.timeout_ms,
    )
    print(f"host: {args.host}")
    print(f"port: {args.port}")
    print(f"channel: {args.channel}")

    device.connect()
    try:
        identity = device.identify()
        print(f"idn: {identity}")

        if args.voltage is not None:
            device.set_voltage(args.channel, args.voltage)
            print(f"set_voltage: ok ({args.voltage})")

        if args.current is not None:
            device.set_current(args.channel, args.current)
            print(f"set_current: ok ({args.current})")

        if args.output_on:
            device.output_on(args.channel)
            print("output_on: ok")

        if args.measure:
            sample = device.read_measurement(args.channel)
            print("measure: ok")
            print_measurement(sample)

        if args.output_off:
            device.output_off(args.channel)
            print("output_off: ok")
    finally:
        device.disconnect()


def _build_temp_odp_device(
    *,
    host: str,
    port: int,
    channel: str,
    timeout_ms: int,
) -> OdpPowerSupply:
    transport_config = TransportConfig(
        type=TransportType.SOCKET,
        host=host,
        port=port,
        timeout_ms=timeout_ms,
        write_termination="\n",
        read_termination="\n",
    )
    device_config = DeviceConfig(
        id="odp_socket_tmp",
        vendor=DeviceVendor.OWON,
        model="ODP",
        transport=transport_config,
        logical_channels=[channel],
    )
    return OdpPowerSupply(device_config, SocketTransport(transport_config))
