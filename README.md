# Power Control Host

可靠性电源自动上电上位机项目代码仓库。

## 当前阶段

- 当前主线：只联调 `1 台 ODP`。
- 当前结论：这台 `ODP` 当前通过 `TCP socket` 通信，不按 `VISA` 走。
- 当前本地配置：[`config/devices.local.yaml`](config/devices.local.yaml) 只保留 `odp_01`，当前地址为 `192.168.1.1:4196`，通道为 `CH1`。
- 当前目标：先把最基础通信和 `ODP` 驱动跑稳，再逐步补回 `PSW`、多设备、`1 秒采样`、`Excel 导出` 和 `时序控制`。

## 阅读顺序

建议先按下面顺序看项目：

1. [`docs/01-stage-results.md`](docs/01-stage-results.md)
2. [`config/devices.local.yaml`](config/devices.local.yaml)
3. [`manual-tests/README.md`](manual-tests/README.md)
4. [`manual-tests/odp_socket_probe.ipynb`](manual-tests/odp_socket_probe.ipynb)
5. [`src/power_control_host/transports/socket_transport.py`](src/power_control_host/transports/socket_transport.py)
6. [`src/power_control_host/devices/odp.py`](src/power_control_host/devices/odp.py)
7. [`src/power_control_host/ui/cli.py`](src/power_control_host/ui/cli.py)

## 仓库结构

```text
config/
docs/
manual-tests/
src/power_control_host/
tests/
README.md
pyproject.toml
```

### `config/`

放项目配置文件。

- [`config/devices.local.yaml`](config/devices.local.yaml)
  当前真实联调配置。现在只保留 `1 台 ODP`，用于最简单通信验证。
- [`config/devices.example.yaml`](config/devices.example.yaml)
  未来扩展到 `PSW`、多设备和 `40 台` 时的参考模板。

如果要改 `IP`、端口、型号、通道、备注，优先改这里，不要先改代码。

### `docs/`

放正式说明文档。当前只保留两份长期有价值的文档：

- [`docs/01-stage-results.md`](docs/01-stage-results.md)
  当前阶段成果说明书，记录已经确认的环境、配置、通信方式和阶段结论。
- [`docs/02-architecture-roadmap.md`](docs/02-architecture-roadmap.md)
  当前代码架构、扩展思路和后续路线。

### `manual-tests/`

放真实设备人工联调文件，不是自动化测试。

- [`manual-tests/README.md`](manual-tests/README.md)
  说明这个目录怎么用。
- [`manual-tests/odp_socket_probe.ipynb`](manual-tests/odp_socket_probe.ipynb)
  当前最重要的联调入口。按块运行，逐条验证 `ODP socket` 命令链。

### `src/power_control_host/`

这是正式代码目录。

#### `src/power_control_host/devices/`

放设备驱动层。

- `odp.py`：`ODP` 的高层命令封装。
- `psw.py`：`PSW` 的高层命令封装。
- `base.py`：设备抽象基类。
- `registry.py`：根据配置选择设备驱动和底层传输。

这里解决的是“这类设备应该发什么命令”。

如果出现下面这些问题，通常改这里：

- `INST CH1` 写法不对
- `VOLT` / `CURR` 命令不对
- `MEAS:VOLT?` / `MEAS:CURR?` 返回格式需要特殊处理
- 新增一个设备品牌或型号

#### `src/power_control_host/services/`

放业务层。

- `device_service.py`：设备操作总入口。
- `sequence_service.py`：后续上电时序、循环控制会放这里。
- `log_export_service.py`：后续日志导出、Excel 导出会放这里。

这里解决的是“多个设备操作如何组织成业务流程”。

如果后续要做下面这些能力，主要改这里：

- 多设备轮询
- `1 秒采样`
- `Excel` 导出
- 时序调度
- 循环上下电

#### `src/power_control_host/transports/`

放底层通信层。

- `socket_transport.py`：`TCP socket` 收发。
- `visa_transport.py`：`VISA` 收发。
- `serial_transport.py`：串口收发。
- `base.py`：传输抽象基类。

这里解决的是“命令如何发出去、返回如何收回来”。

如果出现下面这些问题，通常改这里：

- socket 连不上
- 端口不对
- 换行符不对
- 响应没有读全
- `VISA` 资源打不开
- 串口参数不匹配

#### `src/power_control_host/ui/`

放入口层。

- `cli.py`：当前命令行入口。

这里主要负责：

- 暴露临时联调命令
- 暴露配置检查命令
- 后续接正式 GUI 前，先作为最小可操作入口

如果要新增一个临时联调命令，通常改这里。

### `tests/`

这是自动化测试目录，不是当前真实设备联调入口。

以后会放：

- 配置解析测试
- 驱动命令格式测试
- 业务流程回归测试

当前真实设备联调以 [`manual-tests/`](manual-tests/) 为主。

### 其他核心文件

- [`src/power_control_host/models.py`](src/power_control_host/models.py)
  放枚举、数据模型、采样结构、时序结构。
- [`src/power_control_host/settings.py`](src/power_control_host/settings.py)
  负责读取和解析 `YAML` 配置。
- [`src/power_control_host/app.py`](src/power_control_host/app.py)
  负责把配置、驱动、服务组装起来。
- [`src/power_control_host/logging_config.py`](src/power_control_host/logging_config.py)
  负责日志初始化。
- [`src/power_control_host/__main__.py`](src/power_control_host/__main__.py)
  让 `python -m power_control_host` 可以直接启动。

## 改哪里

如果你后面要改功能，可以按这个映射找文件：

- 改设备地址、端口、通道、型号：[`config/devices.local.yaml`](config/devices.local.yaml)
- 改 `ODP` 命令格式：[`src/power_control_host/devices/odp.py`](src/power_control_host/devices/odp.py)
- 改 `PSW` 命令格式：[`src/power_control_host/devices/psw.py`](src/power_control_host/devices/psw.py)
- 改 socket/VISA/串口收发逻辑：[`src/power_control_host/transports/`](src/power_control_host/transports/)
- 新增联调命令：[`src/power_control_host/ui/cli.py`](src/power_control_host/ui/cli.py)
- 做多设备采样、导出、时序：[`src/power_control_host/services/`](src/power_control_host/services/)
- 写自动化回归测试：[`tests/`](tests/)

## 当前阶段重点产出

当前这版不是 GUI 版本，而是“把最基础通信事实收清楚”的版本。重点产出是：

- `ODP` 当前走 `socket`
- 本地配置已收敛到 `1 台 ODP`
- 已有人工联调 notebook，可逐块跑命令
- 配置解析已兼容 `vendor` / `transport.type` 的大小写和空格差异
- socket 收发已从“只读一次”改成“按结束符或超时持续读取”

## 面向 40 台的提前约束

虽然当前只做 `1 台 ODP`，但代码结构已经按后续扩展预留了边界：

- 设备配置用 `devices` 列表，后续可以逐步扩到多台
- 设备驱动和通信层分离，`ODP` 与 `PSW` 可以走不同传输方式
- 业务层已预留 `sequence_service` 和 `log_export_service`
- 当前阶段先不做 GUI，优先把通信、超时、采样和调度边界收清楚

## 当前阶段的详细说明

详细环境、阶段结论和后续路线，请看：

- [`docs/01-stage-results.md`](docs/01-stage-results.md)
- [`docs/02-architecture-roadmap.md`](docs/02-architecture-roadmap.md)
- [`manual-tests/README.md`](manual-tests/README.md)
