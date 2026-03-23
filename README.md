# Power Control Host

可靠性电源上位机项目骨架。

当前目标不是一次性把全部功能写完，而是先把后续开发要走的路、代码分层、配置方式、阶段任务和验证入口搭清楚。项目默认按 `Python + 可扩展通信适配层` 组织，先支持 `ODP` 与 `PSW` 两类电源的 PoC 和后续扩展。

## 当前范围

- 建立统一的项目目录结构
- 建立配置、日志、设备抽象、传输层、调度层骨架
- 预留 `VISA`、`Socket`、`Serial` 三类通信方式
- 预留 `ODP` 与 `PSW` 两类设备驱动
- 写清楚第一阶段要准备什么、安装什么、先验证什么

## 项目结构

```text
power-control-host/
  config/
  docs/
  src/power_control_host/
  tests/
```

## 推荐启动方式

1. 创建虚拟环境
2. 安装依赖
3. 先核对并填写本地配置
4. 先执行配置检查，不急着连设备

```powershell
cd .\power-control-host
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m power_control_host show-plan
python -m power_control_host check-config --config .\config\devices.local.yaml
```

如果你现在还没装 Python、虚拟环境和 NI-VISA，先看：
`docs/09-environment-setup.md`

## PoC 常用命令

```powershell
python -m power_control_host list-visa-resources
python -m power_control_host probe-visa --resource "USB0::..."
python -m power_control_host probe-idn --config .\config\devices.local.yaml --device odp_01
python -m power_control_host probe-idn --config .\config\devices.local.yaml --device psw_01
python -m power_control_host set-voltage --config .\config\devices.local.yaml --device odp_01 --channel CH1 --value 12
python -m power_control_host set-current --config .\config\devices.local.yaml --device odp_01 --channel CH1 --value 1
python -m power_control_host output-on --config .\config\devices.local.yaml --device odp_01 --channel CH1
python -m power_control_host measure --config .\config\devices.local.yaml --device odp_01 --channel CH1
python -m power_control_host output-off --config .\config\devices.local.yaml --device odp_01 --channel CH1
```

详细步骤见 `docs/06-local-setup-and-poc.md`。
如需按顺序执行的正式说明，可直接看 `docs/07-operation-manual.md`。
如需先做 USB 第一次通信验证，可直接看 `docs/08-usb-first-contact.md`。
如需详细环境安装步骤，可直接看 `docs/09-environment-setup.md`。

## 第一阶段完成标准

- 已确认现场设备准确型号
- 已确认优先使用的通信接口
- 已具备最小联调环境
- 已跑通配置加载与工程启动
- 已能开始编写 `*IDN?`、设压、设流、开关输出的验证脚本

## 当前默认判断

- PoC 阶段优先走 `Python + PyVISA`
- 正式版本后续根据联调结果决定是否继续 Python，或转为 `C#/.NET`
- 若后续找回旧的 LabVIEW 工程，再重新评估是否接着旧工程改
