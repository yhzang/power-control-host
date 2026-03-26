# Power Control Host

可靠性电源自动上电上位机项目代码仓库。

## 当前阶段定位

当前阶段不是 GUI 版，也不是多设备完整版，而是“单台 `ODP` 的最小可用控制闭环”版本。

本阶段聚焦：

- 只联调 `1 台 ODP`
- 当前按 `TCP socket` 通信，不按 `VISA` 走
- 先把基础控制、循环时序、动作日志和回归测试补齐
- 暂不做 `PSW`、多设备执行、`1 秒采样`、`Excel` 导出、正式 GUI

当前本地配置见 [`config/devices.local.yaml`](config/devices.local.yaml)，设备为 `odp_01`，地址 `192.168.1.1:4196`，当前配置了 `CH1`、`CH2` 两个逻辑通道。

## 这阶段做了什么

本阶段已经完成的能力：

- 完成 `ODP3012` 的基础 `socket` 通信验证：
  - `*IDN?`
  - `INST CHx`
  - `VOLT`
  - `CURR`
  - `OUTP ON/OFF`
  - `MEAS:VOLT?`
  - `MEAS:CURR?`
- 落地了命令行联调入口，可直接做：
  - 配置检查
  - 设备识别
  - 设电压 / 设电流
  - 开输出 / 关输出
  - 单通道循环
  - 多通道同起点独立循环
  - 多通道相对时序循环
  - 兼容旧的双通道“后上先下”入口
- 动作事件日志已打通，默认输出到 `runtime/sequence_logs/*.csv`
- 自动化回归测试已补齐，覆盖：
  - `channel-spec` 参数解析
  - 多通道时间线编译
  - 相对时序依赖解析
  - CLI 分发
  - 旧 `run-staggered-cycle` 兼容映射

## 当前已实现的功能

### 1. 基础设备操作

当前 CLI 已支持：

- `check-config`
- `show-devices`
- `probe-idn`
- `measure`
- `set-voltage`
- `set-current`
- `output-on`
- `output-off`

### 2. 时序执行

当前 CLI 已支持 4 类控制入口：

- `run-cycle`
  单通道循环上电 / 下电
- `run-parallel-cycle`
  多个通道同一时刻启动，但每个通道按各自参数独立循环
- `run-relative-cycle`
  多个通道共享同一组组级循环参数，但每个通道可相对另一通道设置开机延后 / 关机提前
- `run-staggered-cycle`
  兼容入口，本质上是 `run-relative-cycle` 的双通道特例

说明：

- 这里的“同步”指“同一调度起点开始”，不是硬件级绝对同时触发
- 当前仍只针对单台电源执行，多设备并行还未实现

### 3. 日志输出

每次执行时序命令后，都会生成动作日志 CSV，默认路径：

```text
runtime/sequence_logs/<plan_name>_<timestamp>.csv
```

日志会记录：

- 时间戳
- 计划名
- 步骤序号
- 设备 ID
- 通道
- 动作
- 细节

## 如何安装与启动

建议使用 `Python 3.11+`。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -e .
pip install -e .[dev]
```

安装完成后，可以直接用入口命令：

```powershell
power-control-host --config config/devices.local.yaml show-devices
```

也可以用模块方式启动：

```powershell
python -m power_control_host --config config/devices.local.yaml show-devices
```

## 这部分功能怎么用

### 1. 先检查配置

```powershell
power-control-host --config config/devices.local.yaml check-config
power-control-host --config config/devices.local.yaml show-devices
power-control-host --config config/devices.local.yaml probe-idn --device odp_01
```

### 2. 单通道循环

示例：`CH1` 上电 `3s`，下电 `2s`，循环 `5` 次，并在执行前预设 `5V / 0.5A`

```powershell
power-control-host --config config/devices.local.yaml run-cycle --device odp_01 --channel CH1 --on-seconds 3 --off-seconds 2 --cycles 5 --voltage 5 --current 0.5
```

### 3. 多通道同起点独立循环

示例：`CH1`、`CH2` 同时起跑，但各自按自己的循环参数执行

```powershell
power-control-host --config config/devices.local.yaml run-parallel-cycle --device odp_01 --channel-spec "CH1:on=10,off=5,cycles=3,voltage=12,current=1" --channel-spec "CH2:on=8,off=2,cycles=2,voltage=5,current=0.5"
```

`--channel-spec` 语法：

```text
CH1:on=10,off=5,cycles=3,voltage=12,current=1
```

其中：

- `on` / `off` / `cycles` 必填
- `voltage` / `current` 可选

### 4. 多通道相对时序循环

示例：`CH1` 作为基准通道，`CH2` 相对 `CH1` 晚开 `5s`、早关 `5s`

```powershell
power-control-host --config config/devices.local.yaml run-relative-cycle --device odp_01 --on-seconds 13 --off-seconds 2 --cycles 4 --channel-spec "CH1:voltage=12,current=1" --channel-spec "CH2:ref=CH1,on_delay=5,off_advance=5,voltage=5,current=0.5"
```

`--channel-spec` 语法：

```text
CH2:ref=CH1,on_delay=5,off_advance=5,voltage=5,current=0.5
```

其中：

- `ref` 可选，未写表示该通道是根通道
- `on_delay` / `off_advance` 可选，默认 `0`
- `voltage` / `current` 可选

### 5. 旧的双通道后上先下兼容入口

```powershell
power-control-host --config config/devices.local.yaml run-staggered-cycle --device odp_01 --lead-channel CH1 --lag-channel CH2 --delay-seconds 5 --hold-seconds 3 --rest-seconds 2 --cycles 4 --lead-voltage 12 --lag-voltage 5
```

### 6. 指定日志文件

所有时序命令都支持 `--log-file`：

```powershell
power-control-host --config config/devices.local.yaml run-cycle --device odp_01 --channel CH1 --on-seconds 1 --off-seconds 1 --cycles 3 --log-file runtime/sequence_logs/ch1_smoke.csv
```

## 如何测试功能有无做好

建议分两层验证。

### 第一层：自动化测试

先跑自动化测试，确认参数解析、时间线编译和 CLI 分发没有回退：

```powershell
python -m pytest tests/test_sequence_service.py tests/test_cli.py -q
```

如果要跑全部自动化测试：

```powershell
python -m pytest -q
```

### 第二层：真实设备联调

建议按下面顺序验证：

1. 配置与设备连通性
   - `check-config`
   - `show-devices`
   - `probe-idn`
2. 单点控制
   - `set-voltage`
   - `set-current`
   - `output-on`
   - `measure`
   - `output-off`
3. 单通道循环
   - `run-cycle`
4. 双通道同起点独立循环
   - `run-parallel-cycle`
5. 双通道后上先下
   - `run-relative-cycle` 或 `run-staggered-cycle`
6. 日志检查
   - 打开 `runtime/sequence_logs/*.csv`
   - 检查动作顺序、通道、时间间隔是否与命令参数一致

### 真实设备验证通过的最低标准

你至少要确认下面几点：

- 命令执行过程中设备面板状态变化正确
- `CH1`、`CH2` 的开关顺序符合命令参数
- 最后一段 `off/rest` 时间也被正确保留
- 生成了对应的 CSV 日志
- 日志中的 `wait` / `output_on` / `output_off` 顺序正确
- 相对时序模式下，引用关系没有跑反

## 测试代码在哪里

自动化测试代码在 [`tests/`](tests/) 下，当前重点文件是：

- [`tests/test_sequence_service.py`](tests/test_sequence_service.py)
  覆盖时序编译、时间线排序、依赖解析和失败场景
- [`tests/test_cli.py`](tests/test_cli.py)
  覆盖 `channel-spec` 参数解析、CLI 命令分发和旧入口兼容

真实设备人工联调入口在 [`manual-tests/`](manual-tests/) 下：

- [`manual-tests/README.md`](manual-tests/README.md)
- [`manual-tests/odp_socket_probe.ipynb`](manual-tests/odp_socket_probe.ipynb)
- [`manual-tests/odp_sequence_manual.ipynb`](manual-tests/odp_sequence_manual.ipynb)

## 当前目录重点映射

如果后面继续改功能，建议按下面映射找文件：

- 改设备地址、端口、通道、型号：[`config/devices.local.yaml`](config/devices.local.yaml)
- 改 `ODP` 命令与返回解析：[`src/power_control_host/devices/odp.py`](src/power_control_host/devices/odp.py)
- 改时序编译与执行逻辑：[`src/power_control_host/services/sequence_service.py`](src/power_control_host/services/sequence_service.py)
- 改 CLI 入口：[`src/power_control_host/ui/cli.py`](src/power_control_host/ui/cli.py)
- 改 `channel-spec` 解析：[`src/power_control_host/ui/cli_parsing.py`](src/power_control_host/ui/cli_parsing.py)
- 写或补自动化测试：[`tests/`](tests/)

## 当前未做的内容

下面这些能力还没有进入本轮实现范围：

- `PSW` 现场联调
- 多设备一起执行
- `1 秒采样`
- `Excel` 导出
- 正式 GUI

## 阅读顺序

建议先按下面顺序看项目：

1. [`README.md`](README.md)
2. [`docs/01-stage-results.md`](docs/01-stage-results.md)
3. [`config/devices.local.yaml`](config/devices.local.yaml)
4. [`manual-tests/README.md`](manual-tests/README.md)
5. [`manual-tests/odp_socket_probe.ipynb`](manual-tests/odp_socket_probe.ipynb)
6. [`manual-tests/odp_sequence_manual.ipynb`](manual-tests/odp_sequence_manual.ipynb)
7. [`src/power_control_host/services/sequence_service.py`](src/power_control_host/services/sequence_service.py)
8. [`src/power_control_host/ui/cli.py`](src/power_control_host/ui/cli.py)
