# Power Control Host

可靠性电源自动上电上位机。

## 当前进度

- ODP 单台控制闭环已完成（socket 通信、时序执行、动作日志、回归测试）
- PSW 驱动已就绪，确认走 LAN socket port 2268
- 新增 `scan-devices`，并发扫描局域网自动发现 ODP / PSW
- 未做：多设备并发执行、1 秒采样、Excel 导出、GUI

本地配置：[`config/devices.local.yaml`](config/devices.local.yaml)

## 安装

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

## 设备发现

```powershell
# 扫描并打印
power-control-host scan-devices

# 同时输出 YAML 片段，粘进 devices.local.yaml 即可用
power-control-host scan-devices --emit-yaml
```

典型输出：

```
Scanning 192.168.1.1-254 ...
Found 3 device(s):
  odp_01  192.168.1.1:4196  OWON,ODP3012,24320076,FV:V3.9.0
  odp_02  192.168.1.2:4196  OWON,ODP3012,24320077,FV:V3.9.0
  psw_01  192.168.1.3:2268  GW-INSTEK,PSW30-72,GEW161978,02.53.20220419
```

端口固定：ODP `4196`，PSW `2268`。
通道自动推断：ODP3012 → CH1/CH2，ODP3032/3033 → CH1/CH2/CH3，PSW → OUT。

## 基础操作

```powershell
power-control-host --config config/devices.local.yaml check-config
power-control-host --config config/devices.local.yaml show-devices
power-control-host --config config/devices.local.yaml probe-idn --device odp_01
power-control-host --config config/devices.local.yaml measure --device odp_01 --channel CH1
power-control-host --config config/devices.local.yaml set-voltage --device odp_01 --channel CH1 --value 5.0
power-control-host --config config/devices.local.yaml output-on --device odp_01 --channel CH1
power-control-host --config config/devices.local.yaml output-off --device odp_01 --channel CH1
```

## 时序执行

ODP 和 PSW 均可用，传对应 `--device` 和 `--channel` 即可。
"同步"指同一调度起点，不是硬件级绝对同时触发。

### 单通道循环

```powershell
power-control-host --config config/devices.local.yaml run-cycle \
  --device odp_01 --channel CH1 --on-seconds 3 --off-seconds 2 --cycles 5 --voltage 5 --current 0.5
```

PSW 示例：

```powershell
power-control-host --config config/devices.local.yaml run-cycle \
  --device psw_01 --channel OUT --on-seconds 5 --off-seconds 5 --cycles 3
```

### 多通道同起点独立循环

```powershell
power-control-host --config config/devices.local.yaml run-parallel-cycle \
  --device odp_01 \
  --channel-spec "CH1:on=10,off=5,cycles=3,voltage=12,current=1" \
  --channel-spec "CH2:on=8,off=2,cycles=2,voltage=5,current=0.5"
```

`channel-spec` 格式：`CH1:on=10,off=5,cycles=3[,voltage=12][,current=1]`

### 多通道相对时序循环

```powershell
power-control-host --config config/devices.local.yaml run-relative-cycle \
  --device odp_01 --on-seconds 13 --off-seconds 2 --cycles 4 \
  --channel-spec "CH1:voltage=12,current=1" \
  --channel-spec "CH2:ref=CH1,on_delay=5,off_advance=5,voltage=5,current=0.5"
```

`channel-spec` 格式：`CH2:ref=CH1,on_delay=5,off_advance=5[,voltage=5][,current=0.5]`
`ref` 省略表示该通道是根通道。

### 双通道后上先下（兼容入口）

```powershell
power-control-host --config config/devices.local.yaml run-staggered-cycle \
  --device odp_01 --lead-channel CH1 --lag-channel CH2 \
  --delay-seconds 5 --hold-seconds 3 --rest-seconds 2 --cycles 4
```

本质是 `run-relative-cycle` 的双通道特例。

### 日志

所有时序命令默认写 `runtime/sequence_logs/<plan_name>_<timestamp>.csv`，也可指定：

```powershell
--log-file runtime/sequence_logs/ch1_smoke.csv
```

## 测试

```powershell
python -m pytest tests/ -q
```

覆盖：channel-spec 解析、多通道时间线编译、相对时序依赖解析、CLI 分发、staggered 兼容映射。

## 文件索引

| 需要改什么 | 找哪个文件 |
|---|---|
| 设备地址 / 端口 / 通道 | `config/devices.local.yaml` |
| ODP 命令与返回解析 | `src/power_control_host/devices/odp.py` |
| PSW 命令与返回解析 | `src/power_control_host/devices/psw.py` |
| 设备自动扫描逻辑 | `src/power_control_host/discovery.py` |
| 时序编译与执行 | `src/power_control_host/services/sequence_service.py` |
| CLI 入口 | `src/power_control_host/ui/cli.py` |
| channel-spec 解析 | `src/power_control_host/ui/cli_parsing.py` |
| 自动化测试 | `tests/` |
| 手动联调 notebook | `manual-tests/` |
