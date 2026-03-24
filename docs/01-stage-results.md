# 01 阶段性成果说明书

## 1. 当前范围

当前阶段只做最基础的真实设备通信验证，范围收敛为：

- 只联调 `1 台 ODP`
- 先不联调 `PSW`
- 先不做 GUI
- 先不做多设备调度
- 先不做 `1 秒采样`、`Excel 导出`、时序控制

当前阶段目标只有一个：先把这台 `ODP` 的最基础通信链路跑清楚。

## 2. 当前已经确认的事实

截至当前版本，已经确认或先按实测结果固化下来的结论如下：

- 当前这台 `ODP` 通过 `TCP socket` 通信
- `*IDN?` 返回 `OWON,ODP3012,24320076,FV:V3.9.0`
- 当前本地配置地址为 `192.168.1.1:4196`
- 当前默认逻辑通道为 `CH1`
- 当前本地配置文件为 [`config/devices.local.yaml`](../config/devices.local.yaml)
- 当前联调入口为 [`manual-tests/odp_socket_probe.ipynb`](../manual-tests/odp_socket_probe.ipynb)

这意味着当前版本的主任务不是“把所有设备都接上”，而是先确认：

- `*IDN?`
- `INST CH1`
- `VOLT`
- `CURR`
- `OUTP ON/OFF`
- `MEAS:VOLT?`
- `MEAS:CURR?`

这些最小命令链是否成立。

当前第一轮实测结果已经确认：

- `INST CH1` 可用
- `VOLT 5` 可用
- `CURR 0.5` 可用
- `OUTP ON/OFF` 可用
- `MEAS:VOLT?` 返回单值，例如 `4.999`
- `MEAS:CURR?` 返回的是整机状态块，不是单个浮点数

当前 `MEAS:CURR?` 的典型返回如下：

```text
05.000,03.600,FF.FFF#00.500,01.000,FF.FFF#04.999,03.599,FF.FFF#00.000,00.000,FF.FFF#1,1,F,OF
```

按当前判断，这串数据更接近下面这种结构：

```text
设定电压块   -> 05.000,03.600,FF.FFF
设定电流块   -> 00.500,01.000,FF.FFF
实测电压块   -> 04.999,03.599,FF.FFF
实测电流块   -> 00.000,00.000,FF.FFF
状态信息块   -> 1,1,F,OF
```

这说明：

- `CURR` 命令当前更像是在设置限流值
- 当前没有负载时，实测电流为 `0.000` 是合理现象
- 代码层需要按状态块解析，而不是把 `MEAS:CURR?` 直接当成单值

## 3. 当前环境与安装项

### 操作系统

- `Windows 10` 或 `Windows 11`

### Python 环境

- `Python 3.11` 或 `Python 3.12`
- 建议使用项目根目录下的虚拟环境 `.venv`

建议命令：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -e .
pip install notebook ipykernel
```

### 当前 Python 依赖

当前 [`pyproject.toml`](../pyproject.toml) 中已经纳入的核心依赖：

- `PyYAML`
- `pyvisa`
- `pyvisa-py`
- `pyserial`
- `pandas`
- `openpyxl`

说明：

- `pyvisa` / `pyvisa-py` 主要为后续 `PSW` 或其他 `VISA` 设备预留
- 当前这台 `ODP` 的最基础验证按 `socket` 走，即使暂时不用 `VISA`，也不影响保留这套依赖
- notebook 联调需要额外安装 `notebook` 或 `jupyterlab`，当前文档按最简单的 `notebook` 写

### 当前阶段需要的外部安装项

- `Python 3.11+`
- `VS Code` 或 Jupyter 环境
- `Git`
- `notebook` / `ipykernel`

当前阶段如果只做 `ODP socket` 联调，`NI-VISA` 不是必须项。  
但后续恢复 `PSW` 联调时，建议补装 `NI-VISA`。

## 4. 当前配置文件结论

当前联调配置已刻意收敛为最小规模，见 [`config/devices.local.yaml`](../config/devices.local.yaml)。

核心结论如下：

- 当前只保留 `odp_01`
- `vendor` 固定写成 `owon`
- `model` 当前记录为 `ODP3012`
- `transport.type` 为 `socket`
- `host` 为 `192.168.1.1`
- `port` 为 `4196`
- `timeout_ms` 为 `3000`
- `write_termination` 和 `read_termination` 先按 `\\n` 处理
- `logical_channels` 先只写 `CH1`

本阶段的原则是：

- 优先改配置文件
- 不要一上来把多台设备、多个品牌都塞回本地配置
- 不要在没有实测的情况下扩大范围

## 5. 当前代码已收敛的内容

### 5.1 配置解析

[`src/power_control_host/settings.py`](../src/power_control_host/settings.py) 已做的处理：

- `vendor` 大小写更宽容，例如 `OWON` / `owon`
- `transport.type` 更宽容，例如 `socket` / `Socket`
- `port` 会按整数解析
- 空字符串会清洗为 `None`

这部分的目的，是避免因为配置书写风格不同导致程序在启动前就报错。

### 5.2 socket 收发

[`src/power_control_host/transports/socket_transport.py`](../src/power_control_host/transports/socket_transport.py) 已从“只读一次 `recv()`”改成“按结束符或超时持续读取”。

这样做是为了避免后续遇到：

- 响应分包
- 一次 `recv()` 没收全
- 查询命令偶发只收到半截返回

### 5.3 ODP 命令层

[`src/power_control_host/devices/odp.py`](../src/power_control_host/devices/odp.py) 当前先按常见 `SCPI` 风格预留：

- `INST {channel}`
- `VOLT {value}`
- `CURR {value}`
- `OUTP ON`
- `OUTP OFF`
- `MEAS:VOLT?`
- `MEAS:CURR?`

这一层目前仍然以“待现场逐条校正”为准，不把它当成最终结论。

### 5.4 当前联调入口

当前已经准备了两种联调入口：

- [`manual-tests/odp_socket_probe.ipynb`](../manual-tests/odp_socket_probe.ipynb)
  适合在另一台电脑上一块一块运行
- [`src/power_control_host/ui/cli.py`](../src/power_control_host/ui/cli.py)
  适合命令行直接发单条 `SCPI`

当前也已经补上了两类顺序控制入口：

- 单通道循环上电 / 下电
- 双通道“后上先下”延时循环

## 6. 当前建议的验证顺序

当前建议先按下面顺序验证：

1. `*IDN?`
2. `INST CH1`
3. `VOLT 5`
4. `CURR 0.5`
5. `OUTP ON`
6. `MEAS:VOLT?`
7. `MEAS:CURR?`
8. `OUTP OFF`

每一步都应记录：

- 命令
- 是否成功
- 原始返回内容
- 设备面板上是否有对应变化

## 7. 当前阶段已交付的产物

- 项目代码骨架
- `ODP / PSW` 设备层占位
- `socket / VISA / serial` 传输层占位
- 面向当前阶段的本地配置文件
- 面向真实设备的 notebook 联调入口
- 根 `README`
- 当前阶段成果文档
- 架构与路线文档

## 8. 当前阶段尚未完成的事情

下面这些事情仍待继续验证或补完：

- `ODP` 各条命令是否与现场设备完全一致
- `MEAS` 返回格式是否稳定
- `OUTP` 是否有额外状态前提
- `PSW` 实际通信方式是否仍按 `VISA`
- 多设备同时连接的稳定性
- `1 秒采样` 和 `Excel 导出`
- 时序控制逻辑

## 9. 下一步重点

当前最合理的下一步不是做保存测量文件，而是先把单台 `ODP` 的控制闭环做出来。

优先顺序如下：

1. 单通道循环
   例如 `CH1` 上电 `1s`、下电 `1s`、循环 `N` 次
2. 双通道延时循环
   例如 `CH1` 先上，延时后 `CH2` 再上；下电时 `CH2` 先下，延时后 `CH1` 再下
3. 保存动作日志
   当前先保存“执行了哪些动作、每步时间戳”，而不是先保存测量曲线
4. 带负载后再验证实测电流

## 10. 本阶段的结论

当前版本已经不再是“纯骨架”，而是进入“围绕真实设备结果收口”的阶段。

本阶段最重要的结论不是界面，而是：

- 当前先只做 `1 台 ODP`
- 当前这台 `ODP` 走 `socket`
- 当前本地配置已收敛
- 当前已具备可直接执行的 notebook 联调入口

后续所有扩展，都应建立在这条最小通信链已经被真实设备确认的前提之上。
