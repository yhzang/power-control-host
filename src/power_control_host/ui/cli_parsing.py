from __future__ import annotations

from power_control_host.models import ChannelCycleSpec, RelativeChannelSpec


def parse_parallel_channel_specs(raw_specs: list[str]) -> list[ChannelCycleSpec]:
    return [parse_parallel_channel_spec(item) for item in raw_specs]


def parse_parallel_channel_spec(raw_spec: str) -> ChannelCycleSpec:
    channel, options = _split_channel_spec(raw_spec, allow_empty_options=False)
    spec = ChannelCycleSpec(
        channel=channel,
        on_seconds=_pop_float(options, "on", raw_spec, required=True),
        off_seconds=_pop_float(options, "off", raw_spec, required=True),
        cycles=_pop_int(options, "cycles", raw_spec, required=True),
        voltage=_pop_float(options, "voltage", raw_spec),
        current=_pop_float(options, "current", raw_spec),
    )
    _raise_on_unknown_options(options, raw_spec)
    return spec


def parse_relative_channel_specs(raw_specs: list[str]) -> list[RelativeChannelSpec]:
    return [parse_relative_channel_spec(item) for item in raw_specs]


def parse_relative_channel_spec(raw_spec: str) -> RelativeChannelSpec:
    channel, options = _split_channel_spec(raw_spec, allow_empty_options=True)
    spec = RelativeChannelSpec(
        channel=channel,
        reference_channel=_pop_text(options, "ref", raw_spec),
        on_delay_seconds=_pop_float(options, "on_delay", raw_spec, default=0.0),
        off_advance_seconds=_pop_float(options, "off_advance", raw_spec, default=0.0),
        voltage=_pop_float(options, "voltage", raw_spec),
        current=_pop_float(options, "current", raw_spec),
    )
    _raise_on_unknown_options(options, raw_spec)
    return spec


def _split_channel_spec(
    raw_spec: str,
    *,
    allow_empty_options: bool,
) -> tuple[str, dict[str, str]]:
    text = raw_spec.strip()
    if not text:
        raise ValueError("channel spec 不能为空")

    if ":" in text:
        channel_text, options_text = text.split(":", 1)
    else:
        if not allow_empty_options:
            raise ValueError(f"channel spec 缺少 ':' 分隔符: {raw_spec}")
        channel_text, options_text = text, ""

    channel = channel_text.strip().upper()
    if not channel:
        raise ValueError(f"channel spec 缺少通道名: {raw_spec}")

    if not options_text.strip():
        if allow_empty_options:
            return channel, {}
        raise ValueError(f"channel spec 缺少参数: {raw_spec}")

    options: dict[str, str] = {}
    for item in options_text.split(","):
        token = item.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"channel spec 参数格式错误，需为 key=value: {raw_spec}")
        key_text, value_text = token.split("=", 1)
        key = key_text.strip().lower().replace("-", "_")
        value = value_text.strip()
        if not key or not value:
            raise ValueError(f"channel spec 参数格式错误，需为 key=value: {raw_spec}")
        if key in options:
            raise ValueError(f"channel spec 存在重复参数 {key}: {raw_spec}")
        options[key] = value

    if not options and not allow_empty_options:
        raise ValueError(f"channel spec 缺少参数: {raw_spec}")

    return channel, options


def _pop_float(
    options: dict[str, str],
    key: str,
    raw_spec: str,
    *,
    required: bool = False,
    default: float | None = None,
) -> float | None:
    if key not in options:
        if required:
            raise ValueError(f"channel spec 缺少参数 {key}: {raw_spec}")
        return default

    raw_value = options.pop(key)
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"channel spec 参数 {key} 不是合法数字: {raw_spec}") from exc

    return value


def _pop_int(
    options: dict[str, str],
    key: str,
    raw_spec: str,
    *,
    required: bool = False,
    default: int | None = None,
) -> int | None:
    if key not in options:
        if required:
            raise ValueError(f"channel spec 缺少参数 {key}: {raw_spec}")
        return default

    raw_value = options.pop(key)
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"channel spec 参数 {key} 不是合法整数: {raw_spec}") from exc

    return value


def _pop_text(
    options: dict[str, str],
    key: str,
    raw_spec: str,
) -> str | None:
    if key not in options:
        return None
    value = options.pop(key).strip().upper()
    if not value:
        raise ValueError(f"channel spec 参数 {key} 不能为空: {raw_spec}")
    return value


def _raise_on_unknown_options(options: dict[str, str], raw_spec: str) -> None:
    if options:
        unknown = ", ".join(sorted(options))
        raise ValueError(f"channel spec 包含未知参数 {unknown}: {raw_spec}")
