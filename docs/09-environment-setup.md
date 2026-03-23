# 开发环境安装说明

这份文档专门讲一件事情：把这套工程在 Windows 电脑上跑起来。

目标不是先连设备，而是先把下面这几样准备好：

- Python
- 虚拟环境
- 本项目依赖包
- NI-VISA
- 基础验证命令

完成这份文档后，你应该能做到：

- `python --version` 正常
- 虚拟环境可激活
- `pip install -e .` 正常
- `python -m power_control_host show-plan` 正常
- `python -m power_control_host list-visa-resources` 可以执行

## 1. 这台电脑需要安装什么

建议按下面顺序安装。

### 1.1 必装软件

1. `Python 3.11` 或 `Python 3.12`
2. `NI-VISA`
3. `VS Code`
4. `Git`

### 1.2 建议安装

1. `Excel`
2. ODP 厂家 PC 软件
3. PSW 厂家 PC 软件

说明：

- `Python` 用来运行工程和脚本
- `NI-VISA` 用来识别和访问仪器的 VISA 资源
- `VS Code` 用来查看和修改代码
- `Git` 用来版本管理
- 厂家软件可用来辅助判断设备是否已被系统识别

## 2. Python 怎么安装

### 2.1 推荐版本

建议安装：

- `Python 3.11.x`

或者：

- `Python 3.12.x`

本项目当前 `pyproject.toml` 要求：

- `Python >= 3.11`

### 2.2 安装时注意什么

安装 Python 时，建议注意这几点：

1. 勾选 `Add python.exe to PATH`
2. 使用默认安装即可
3. 安装完成后，重新打开 PowerShell

### 2.3 安装后怎么检查

打开 PowerShell，执行：

```powershell
python --version
pip --version
```

如果能看到版本号，说明 Python 安装成功。

如果 `python` 命令找不到：

1. 先关闭当前 PowerShell
2. 重新打开 PowerShell
3. 再执行一次 `python --version`
4. 如果还是不行，说明安装时没有加 PATH，需要重新安装或手动加环境变量

## 3. NI-VISA 怎么安装

### 3.1 为什么要装

如果你要先走：

- `USB + VISA`
- `LAN + VISA`

那 `NI-VISA` 基本就是必装的。

它的作用是：

- 让电脑识别仪器的 VISA 资源
- 让 `PyVISA` 能通过标准方式访问设备

### 3.2 安装建议

安装 `NI-VISA` 时，通常默认选项就可以。

装完以后，建议重启一次电脑，或者至少重开 PowerShell。

### 3.3 安装后怎么判断

后面你执行：

```powershell
python -m power_control_host list-visa-resources
```

如果电脑和设备都正常，命令就能列出 VISA 资源。

## 4. VS Code 和 Git 怎么装

这两个主要是开发用。

### 4.1 VS Code

安装完成后，你可以直接打开项目目录：

```text
D:\科大云盘\项目\可靠性电源原表自动上电上位机开发\power-control-host
```

### 4.2 Git

安装完成后，执行：

```powershell
git --version
```

能看到版本号即可。

## 5. 进入项目目录

打开 PowerShell，执行：

```powershell
cd D:\科大云盘\项目\可靠性电源原表自动上电上位机开发\power-control-host
```

确认当前目录正确后，再继续后面的步骤。

## 6. 创建虚拟环境

### 6.1 什么是虚拟环境

虚拟环境就是给这个项目单独准备一个独立的 Python 运行空间。

它的好处是：

- 不污染系统全局 Python
- 不容易和别的项目依赖打架
- 后面出问题也更容易排查

### 6.2 创建命令

在项目目录下执行：

```powershell
python -m venv .venv
```

执行成功后，项目目录下会多出一个：

- `.venv`

文件夹。

## 7. 激活虚拟环境

在 PowerShell 中执行：

```powershell
.\.venv\Scripts\Activate.ps1
```

激活成功后，命令行前面通常会出现：

```text
(.venv)
```

### 7.1 如果激活被拦截

有些 Windows / PowerShell 会提示脚本执行被禁用。

这时可以执行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

执行后，关闭并重新打开 PowerShell，再重新执行：

```powershell
.\.venv\Scripts\Activate.ps1
```

### 7.2 不想改执行策略怎么办

也可以改用 `cmd` 的激活脚本：

```powershell
.\.venv\Scripts\activate.bat
```

## 8. 升级基础打包工具

激活虚拟环境后，建议先执行：

```powershell
python -m pip install --upgrade pip setuptools wheel
```

这一步不是绝对必须，但可以减少安装依赖时的兼容性问题。

## 9. 安装项目依赖

### 9.1 最推荐的安装方式

在项目目录下执行：

```powershell
pip install -e .
```

这条命令会做两件事：

1. 安装项目自身
2. 安装 `pyproject.toml` 里声明的依赖包

### 9.2 如果你还想安装开发工具

执行：

```powershell
pip install -e .[dev]
```

这会额外安装：

- `pytest`
- `ruff`

## 10. 这个项目会安装哪些 Python 包

当前项目主依赖如下。

### 10.1 运行依赖

- `PyYAML`
- `pyvisa`
- `pyvisa-py`
- `pyserial`
- `pandas`
- `openpyxl`

### 10.2 每个包是做什么的

- `PyYAML`
  读取 `devices.local.yaml` 这种配置文件
- `pyvisa`
  通过 VISA 访问仪器
- `pyvisa-py`
  纯 Python 的 VISA backend，某些场景可作为补充
- `pyserial`
  后面如果用串口通信，需要它
- `pandas`
  后面做数据整理和导出时会用到
- `openpyxl`
  后面做 Excel 导出时会用到

### 10.3 开发依赖

- `pytest`
  后面写测试时用
- `ruff`
  后面做代码检查时用

## 11. 安装完成后怎么验证

请按这个顺序执行。

### 11.1 验证 Python

```powershell
python --version
pip --version
```

### 11.2 验证项目能启动

```powershell
python -m power_control_host show-plan
```

### 11.3 验证配置能读取

```powershell
python -m power_control_host check-config --config .\config\devices.local.yaml
```

### 11.4 验证 VISA 命令入口可执行

```powershell
python -m power_control_host list-visa-resources
```

即使这时还没接设备，这条命令也应该能运行，只是可能列不出设备资源。

## 12. 安装完成后的推荐顺序

环境装好以后，不要立刻改很多代码，建议按下面顺序：

1. 先接 1 台设备的 USB
2. 先执行 `list-visa-resources`
3. 再执行 `probe-visa --resource "..."`
4. 拿到成功的 `*IDN?` 结果后，再改 YAML
5. 再进入 `probe-idn`、设压、设流、开输出
6. 最后再切到 LAN

## 13. 常见问题

### 13.1 `python` 找不到

原因通常是：

- Python 没装
- PATH 没加
- PowerShell 没重开

### 13.2 `pip install -e .` 失败

优先检查：

1. 当前是否已经进入项目目录
2. 虚拟环境是否已激活
3. 网络是否正常
4. Python 版本是否为 3.11 或 3.12

### 13.3 `list-visa-resources` 报错

优先检查：

1. NI-VISA 是否安装
2. 虚拟环境是否已激活
3. `pip install -e .` 是否成功

### 13.4 已接 USB 设备，但资源列表为空

优先检查：

1. 设备是否开机
2. USB 线是否正常
3. 设备驱动是否安装
4. 厂家软件能否识别设备
5. 设备是否支持 USB VISA

## 14. 你现在最该执行的命令

如果你准备从头开始装环境，最直接的一组命令就是：

```powershell
cd D:\科大云盘\项目\可靠性电源原表自动上电上位机开发\power-control-host
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -e .
python --version
python -m power_control_host show-plan
python -m power_control_host list-visa-resources
```

## 15. 下一步看哪份文档

环境装好后，建议继续看：

- `docs/08-usb-first-contact.md`

等 USB 第一次通信成功后，再继续看：

- `docs/07-operation-manual.md`
