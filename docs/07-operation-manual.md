# 电源上位机第一阶段操作说明书

## 1. 文档目的

本说明书用于指导第一阶段的实际操作，目标是完成以下事情：

- 搭建本地开发环境
- 接好 ODP 与 PSW 设备
- 完成本地配置文件填写
- 跑通最小通信验证
- 为后续批量控制、日志采集和时序功能开发打基础

当前阶段不追求完整 GUI，也不追求一次性做完全部功能，重点是先把设备通信跑通。

当前建议顺序是：

1. 先用 `USB + VISA` 做第一次通信验证
2. 跑通 `*IDN?`
3. 再填写 YAML 配置
4. 再切换到 `LAN + VISA` 做后续扩展

## 2. 适用范围

本说明书适用于当前工程：

- 项目目录：`D:\科大云盘\项目\可靠性电源原表自动上电上位机开发\power-control-host`

当前默认支持两类设备：

- ODP 系列电源
- PSW 系列电源

当前第一次通信默认优先采用：

- `USB + VISA`

后续扩展阶段优先采用：

- `LAN + VISA`

如现场设备并非使用 VISA 资源方式，后续可改为：

- `Socket`
- `Serial`

## 3. 需要准备的东西

### 3.1 硬件

- ODP 电源 1 台
- PSW 电源 1 台
- Windows 开发电脑 1 台
- 交换机 1 台
- 网线 3 根
- 设备电源线
- USB 线 1 根
- 如需备用调试，可准备串口线

### 3.2 资料

- ODP 编程手册
- PSW 编程手册
- 设备用户手册
- 现有软件需求说明

### 3.3 软件

- Python 3.11 或 3.12
- VS Code
- Git
- NI-VISA
- Excel
- 厂家 PC 软件

## 4. 目录说明

本阶段重点关注以下文件：

- 项目总说明：`README.md`
- 本地配置文件：`config/devices.local.yaml`
- 本地 PoC 说明：`docs/06-local-setup-and-poc.md`
- USB 首次通信说明：`docs/08-usb-first-contact.md`
- 本文档：`docs/07-operation-manual.md`

## 5. 推荐执行顺序

建议不要一开始就直接配置 LAN 和批量设备，而是按下面顺序推进：

1. 先装 Python、NI-VISA 和基础依赖
2. 先用 USB 连 1 台设备
3. 先执行 `list-visa-resources`
4. 再执行 `probe-visa` 发送 `*IDN?`
5. 确认设备支持 VISA 后，再填写 `devices.local.yaml`
6. 再测试 `probe-idn`、设压、设流、开输出、关输出
7. 最后再切到 LAN 和多设备扩展

## 6. 硬件连接步骤

### 6.1 第一次通信推荐方式

第一次通信推荐先用 USB。

```text
电脑 --USB线-- 设备
```

### 6.2 后续扩展推荐方式

后续扩展再切到 LAN。

连接结构如下：

```text
电脑 --网线-- 交换机 --网线-- ODP
                |
                +--网线-- PSW
```

### 6.3 接线步骤

1. 给 ODP 接好电源线并开机
2. 给 PSW 接好电源线并开机
3. 用一根网线把电脑接到交换机
4. 用一根网线把 ODP 接到交换机
5. 用一根网线把 PSW 接到交换机
6. 确认交换机指示灯和设备网口指示灯正常

## 7. 网络配置步骤

### 7.1 推荐固定 IP

- 电脑：`192.168.1.10`
- ODP：`192.168.1.101`
- PSW：`192.168.1.102`
- 子网掩码：`255.255.255.0`

### 7.2 操作要求

1. 在电脑网卡中设置固定 IP
2. 在 ODP 面板或配套软件中设置设备 IP
3. 在 PSW 面板或配套软件中设置设备 IP
4. 确保三者位于同一网段

### 7.3 联通性检查

在 PowerShell 中执行：

```powershell
ping 192.168.1.101
ping 192.168.1.102
```

如果能收到响应，说明基础网络已联通。

## 8. 软件安装步骤

如果你希望按更细的安装说明一步一步来，请优先看：

- `docs/09-environment-setup.md`

### 8.1 安装基础软件

依次安装：

1. Python 3.11 或 3.12
2. VS Code
3. Git
4. NI-VISA
5. Excel
6. 厂家 PC 软件

### 8.2 建立 Python 虚拟环境

进入项目目录后执行：

```powershell
cd D:\科大云盘\项目\可靠性电源原表自动上电上位机开发\power-control-host
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### 8.3 安装完成后的检查

执行以下命令确认 Python 已可用：

```powershell
python --version
pip --version
```

## 9. 配置文件填写步骤

### 9.1 打开文件

编辑以下文件：

- `config/devices.local.yaml`

### 9.2 需要填写和核对的内容

每台设备重点检查以下字段：

- `id`
- `vendor`
- `model`
- `transport.type`
- `transport.resource`
- `logical_channels`

### 9.3 默认示例说明

当前默认配置中：

- `odp_01` 使用 `192.168.1.101`
- `psw_01` 使用 `192.168.1.102`

如果你现在还没确认 LAN，只需要先记住一件事：

- `resource` 可以先不手写猜，等 `list-visa-resources` 和 `probe-visa` 成功后，直接把成功的资源字符串粘贴进去。

如果现场 IP 或型号不同，再改成真实值。

### 9.4 常见配置方式

#### VISA 方式

```yaml
transport:
  type: visa
  resource: TCPIP0::192.168.1.101::INSTR
  timeout_ms: 3000
  write_termination: "\n"
  read_termination: "\n"
```

#### Socket 方式

```yaml
transport:
  type: socket
  host: 192.168.1.101
  port: 5025
  timeout_ms: 3000
  write_termination: "\n"
  read_termination: "\n"
```

#### Serial 方式

```yaml
transport:
  type: serial
  serial_port: COM3
  baudrate: 9600
  timeout_ms: 3000
  write_termination: "\n"
  read_termination: "\n"
```

注意：`Socket` 端口号和 `Serial` 参数必须以现场设备和手册为准。

## 10. 工程启动步骤

### 10.1 查看阶段计划

```powershell
python -m power_control_host show-plan
```

### 10.2 检查配置文件

```powershell
python -m power_control_host check-config --config .\config\devices.local.yaml
```

### 10.3 查看当前设备列表

```powershell
python -m power_control_host show-devices --config .\config\devices.local.yaml
```

如果以上命令可以正常输出，说明项目启动和配置加载正常。

## 11. 最小通信验证步骤

### 11.1 先不依赖 YAML 的第一次 USB 验证

```powershell
python -m power_control_host list-visa-resources
python -m power_control_host probe-visa --resource "把上一步列出来的完整资源名原样填到这里"
```

只要 `probe-visa` 成功返回 `*IDN?`，就说明第一次基础通信已经打通。

### 11.2 身份查询

先验证设备是否可识别：

```powershell
python -m power_control_host probe-idn --config .\config\devices.local.yaml --device odp_01
python -m power_control_host probe-idn --config .\config\devices.local.yaml --device psw_01
```

成功时应返回设备身份字符串。

### 11.3 ODP 基础输出测试

```powershell
python -m power_control_host set-voltage --config .\config\devices.local.yaml --device odp_01 --channel CH1 --value 12
python -m power_control_host set-current --config .\config\devices.local.yaml --device odp_01 --channel CH1 --value 1
python -m power_control_host output-on --config .\config\devices.local.yaml --device odp_01 --channel CH1
python -m power_control_host measure --config .\config\devices.local.yaml --device odp_01 --channel CH1
python -m power_control_host output-off --config .\config\devices.local.yaml --device odp_01 --channel CH1
```

### 11.4 PSW 基础输出测试

```powershell
python -m power_control_host set-voltage --config .\config\devices.local.yaml --device psw_01 --channel OUT --value 12
python -m power_control_host set-current --config .\config\devices.local.yaml --device psw_01 --channel OUT --value 1
python -m power_control_host output-on --config .\config\devices.local.yaml --device psw_01 --channel OUT
python -m power_control_host measure --config .\config\devices.local.yaml --device psw_01 --channel OUT
python -m power_control_host output-off --config .\config\devices.local.yaml --device psw_01 --channel OUT
```

## 12. 常见问题排查

### 12.1 `python` 命令无法识别

说明电脑尚未安装 Python，或环境变量未配置完成。请先安装 Python，并重新打开 PowerShell。

### 12.2 `probe-idn` 失败

按以下顺序排查：

1. 先检查网线和交换机
2. 检查设备是否已开机
3. 检查设备与电脑 IP 是否同网段
4. 检查 `ping` 是否能通
5. 检查 `devices.local.yaml` 的 `resource` 是否正确
6. 检查 NI-VISA 是否已安装
7. 用厂家软件确认设备是否在线

### 12.3 `list-visa-resources` 没有设备

优先检查：

1. 设备是否通过 USB 正常接入
2. 设备是否已开机
3. USB 线是否正常
4. 驱动是否安装
5. NI-VISA 是否安装
6. 厂家软件是否能识别设备

### 12.4 VISA 连不上但设备能 ping 通

说明网络是通的，但接口方式可能不是当前配置。

此时应：

1. 查编程手册确认是否支持标准 VISA 资源
2. 确认资源格式是否正确
3. 如不是标准 VISA，改为 `socket`
4. 如现场走串口，改为 `serial`

### 12.5 输出命令已发送但设备无反应

可能原因包括：

- 实际命令格式与默认骨架不同
- 通道名与现场设备不一致
- 设备处于保护状态
- 输出未满足设备允许条件

此时应对照编程手册和设备返回结果逐条修正命令。

## 13. 当前阶段完成标准

本阶段完成时，应达到以下结果：

- 已确认 ODP 与 PSW 实际型号
- 已至少完成 1 台设备的 USB 首次通信验证
- 已完成硬件接线与网络联通
- 已装好 Python、NI-VISA 和依赖
- 已填写本地配置文件
- 已跑通 `probe-idn`
- 已至少验证一组设压、设流、开输出、关输出、读测量命令

## 14. 下一阶段工作

第一阶段完成后，下一步进入设备命令校正和业务功能开发，包括：

- 校正 ODP / PSW 的真实 SCPI 命令细节
- 增加批量设备轮询
- 增加 1 秒采样记录
- 增加 Excel 导出
- 增加上下电时序模型

## 15. 建议记录内容

每次联调建议记录以下内容：

- 日期
- 设备型号
- 固件版本
- IP 地址
- 连接方式
- 执行命令
- 返回结果
- 是否成功
- 异常现象
- 处理结论

这样后面从 PoC 走到正式开发时，很多问题就不用重复摸索。
