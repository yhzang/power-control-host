# 02 架构与后续路线

## 1. 分层设计

| 层 | 目录 | 职责 |
|---|---|---|
| 配置层 | `config/` + `settings.py` | 设备清单、地址、端口、通道、超时 |
| 传输层 | `transports/` | socket / VISA / serial 底层收发，不关心业务语义 |
| 设备驱动层 | `devices/` | 把传输封装成设备命令，隔离 ODP / PSW 差异 |
| 业务层 | `services/` | 时序编译与执行、采样、导出 |
| 入口层 | `ui/` + `manual-tests/` | CLI 和 notebook 联调入口 |
| 发现层 | `discovery.py` | 局域网设备扫描，按端口和 IDN 自动识别类型 |

分层的目的是改一处不影响其他层：
- 改通信问题 → `transports/`
- 改命令格式 → `devices/`
- 改业务流程 → `services/`
- 改扫描逻辑 → `discovery.py`
- 改 CLI → `ui/cli.py`

## 2. 当前已完成的阶段

### 阶段 1-2：ODP 通信验证与驱动收口
- socket 通信链路确认
- 所有基础命令验证（VOLT / CURR / OUTP / MEAS）
- MEAS:CURR? 返回格式按状态块解析

### 阶段 3：PSW 接入
- 确认 PSW 走 LAN socket，port 2268
- `psw.py` 驱动完整实现
- 确认 4 种 cycle 命令对 PSW 直接可用（service 层对设备类型无感知）

### 阶段 4-5：业务能力与时序控制
- 4 种 cycle 入口全部实现：`run-cycle` / `run-parallel-cycle` / `run-relative-cycle` / `run-staggered-cycle`
- 动作事件日志（CSV）
- 自动化回归测试

### 阶段 5.5：设备自动发现（2026-03-31）
- `discovery.py`：并发探测 192.168.1.1-254，ODP port 4196 / PSW port 2268
- 自动识别设备类型，推断 ID 和通道
- `scan-devices --emit-yaml` 输出可直接粘贴的 YAML 配置

## 3. 下一阶段：40 台设备接入

### 3.1 步骤
1. `scan-devices --emit-yaml` 生成全部设备配置
2. 逐台 `probe-idn` 确认连通
3. PSW 现场 cycle 验证（命令已就绪）
4. 配齐 `devices.local.yaml`，覆盖所有 40 台

### 3.2 扩展到 40 台的关键边界

**设备清单配置化**
不把地址写死在代码里，全部通过 `devices.local.yaml` 管理。

**多设备并发超时隔离**
某台超时或断开不能拖死全局，业务层需围绕隔离、重试、超时控制来设计。

**采样与控制解耦**
后续会同时存在输出控制、周期采样、时序调度，这三条流程不能写在一起。`services/` 已提前拆分，继续沿用。

## 4. 后续待做

| 能力 | 状态 |
|---|---|
| PSW 现场 cycle 验证 | 待做（命令已就绪） |
| 40 台设备全部接入配置 | 待做 |
| 多设备并发执行 | 待做 |
| 1 秒周期采样 | 待做 |
| Excel 导出 | 待做 |
| GUI | 待做 |

## 5. 文件索引

| 需要改什么 | 找哪个文件 |
|---|---|
| 设备地址 / 端口 / 通道 | `config/devices.local.yaml` |
| ODP 命令解析 | `src/power_control_host/devices/odp.py` |
| PSW 命令解析 | `src/power_control_host/devices/psw.py` |
| 设备自动扫描 | `src/power_control_host/discovery.py` |
| 时序编译与执行 | `src/power_control_host/services/sequence_service.py` |
| CLI 入口 | `src/power_control_host/ui/cli.py` |
| channel-spec 解析 | `src/power_control_host/ui/cli_parsing.py` |
| 自动化测试 | `tests/` |
