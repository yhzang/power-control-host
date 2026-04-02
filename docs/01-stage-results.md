# 01 阶段性成果说明书

## 当前阶段定位（2026-03-31 更新）

- ODP 单台控制闭环已完成，4 种 cycle 命令均可用
- PSW 确认走 LAN socket，port 2268，驱动已完整，4 种 cycle 命令同样可直接使用
- 新增 `scan-devices`，并发扫描局域网自动发现 ODP / PSW
- 下一步：把 40 台设备都接上，跑通 PSW 现场联调

## 已确认的设备通信参数

| 设备 | 接口 | IP | Port | *IDN? 返回示例 |
|---|---|---|---|---|
| ODP3012 | TCP socket | 192.168.1.x | 4196 | `OWON,ODP3012,24320076,FV:V3.9.0` |
| PSW30-72 | TCP socket | 192.168.1.x | 2268 | `GW-INSTEK,PSW30-72,GEW161978,02.53.20220419` |

## 已确认的 ODP 命令

| 命令 | 状态 | 备注 |
|---|---|---|
| `*IDN?` | 确认 | 返回 `OWON,ODP3012,...` |
| `INST CH1` | 确认 | 通道切换正常 |
| `VOLT 5` | 确认 | 设电压正常 |
| `CURR 0.5` | 确认 | 设限流正常 |
| `OUTP ON/OFF` | 确认 | 输出开关正常 |
| `MEAS:VOLT?` | 确认 | 返回单浮点，例如 `4.999` |
| `MEAS:CURR?` | 确认 | 返回状态块，需按格式解析（见下） |

`MEAS:CURR?` 典型返回：

```
05.000,03.600,FF.FFF#00.500,01.000,FF.FFF#04.999,03.599,FF.FFF#00.000,00.000,FF.FFF#1,1,F,OF
```

结构：设定电压块 # 设定电流块 # 实测电压块 # 实测电流块 # 状态块

## 已实现的 CLI 功能

| 命令 | 说明 |
|---|---|
| `check-config` | 验证配置文件 |
| `show-devices` | 打印已配置设备 |
| `probe-idn` | 查询单台设备 *IDN? |
| `measure` | 读测量值 |
| `set-voltage` | 设电压 |
| `set-current` | 设限流 |
| `output-on` | 开输出 |
| `output-off` | 关输出 |
| `scan-devices` | 自动扫描局域网发现 ODP / PSW |
| `run-cycle` | 单通道循环上下电 |
| `run-parallel-cycle` | 多通道同起点独立循环 |
| `run-relative-cycle` | 多通道相对时序循环 |
| `run-staggered-cycle` | 双通道后上先下（兼容入口） |
| `socket-scpi` | 直接发单条 SCPI 命令 |
| `odp-socket-smoke` | ODP socket 冒烟测试 |

## PSW cycle 说明

PSW 可直接使用全部 4 种 cycle 命令，不需要额外开发。`sequence_service` 完全通过设备基类接口调用，对设备类型无感知。

示例：

```powershell
power-control-host --config config/devices.local.yaml run-cycle \
  --device psw_01 --channel OUT --on-seconds 5 --off-seconds 5 --cycles 3
```

## 自动测试覆盖范围

- channel-spec 参数解析
- 多通道时间线编译
- 相对时序依赖解析
- CLI 分发
- run-staggered-cycle 兼容映射

```powershell
python -m pytest tests/ -q
```

## PSW 现场验证建议顺序

1. `scan-devices --emit-yaml` 生成配置片段，粘进 `devices.local.yaml`
2. `probe-idn --device psw_01` 确认 IDN 返回
3. `set-voltage --device psw_01 --channel OUT --value 12`
4. `output-on --device psw_01 --channel OUT`
5. `measure --device psw_01 --channel OUT`
6. `output-off --device psw_01 --channel OUT`
7. `run-cycle --device psw_01 --channel OUT --on-seconds 3 --off-seconds 3 --cycles 3`

## 当前未做的内容

- PSW 现场联调（命令已就绪，等接线）
- 多设备并发执行
- 1 秒周期采样
- Excel 导出
- GUI

## 环境安装

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```
