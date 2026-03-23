# 本地配置与 PoC 执行说明

这份文档对应当前工程的第二步：把本地配置填好，并开始最小通信验证。

## 一、先准备什么

- ODP 电源 1 台
- PSW 电源 1 台
- Windows 开发电脑 1 台
- 交换机 1 台
- 网线 3 根
- 设备电源线
- ODP / PSW 编程手册

## 二、电脑要安装什么

### 1. 基础软件

- Python 3.11 或 3.12
- VS Code
- Git
- Excel
- 厂家 PC 软件
- NI-VISA

### 2. Python 环境

```powershell
cd D:\科大云盘\项目\可靠性电源原表自动上电上位机开发\power-control-host
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## 三、网络怎么接

推荐先走 LAN：

```text
电脑 --网线-- 交换机 --网线-- ODP
                |
                +--网线-- PSW
```

推荐固定 IP：

- 电脑：`192.168.1.10`
- ODP：`192.168.1.101`
- PSW：`192.168.1.102`
- 子网掩码：`255.255.255.0`

## 四、先改哪个文件

请先打开：

- `config/devices.local.yaml`

重点确认：

- `model` 是否与现场设备一致
- `resource` 是否与实际 IP 一致
- `logical_channels` 是否与实际通道一致
- 若设备不是 VISA 方式，就改成 `socket` 或 `serial`

## 五、先跑哪几个命令

### 1. 先看计划

```powershell
python -m power_control_host show-plan
```

### 2. 先检查配置

```powershell
python -m power_control_host check-config --config .\config\devices.local.yaml
python -m power_control_host show-devices --config .\config\devices.local.yaml
```

### 3. 先做身份查询

```powershell
python -m power_control_host probe-idn --config .\config\devices.local.yaml --device odp_01
python -m power_control_host probe-idn --config .\config\devices.local.yaml --device psw_01
```

### 4. 再做输出控制

ODP 示例：

```powershell
python -m power_control_host set-voltage --config .\config\devices.local.yaml --device odp_01 --channel CH1 --value 12
python -m power_control_host set-current --config .\config\devices.local.yaml --device odp_01 --channel CH1 --value 1
python -m power_control_host output-on --config .\config\devices.local.yaml --device odp_01 --channel CH1
python -m power_control_host measure --config .\config\devices.local.yaml --device odp_01 --channel CH1
python -m power_control_host output-off --config .\config\devices.local.yaml --device odp_01 --channel CH1
```

PSW 示例：

```powershell
python -m power_control_host set-voltage --config .\config\devices.local.yaml --device psw_01 --channel OUT --value 12
python -m power_control_host set-current --config .\config\devices.local.yaml --device psw_01 --channel OUT --value 1
python -m power_control_host output-on --config .\config\devices.local.yaml --device psw_01 --channel OUT
python -m power_control_host measure --config .\config\devices.local.yaml --device psw_01 --channel OUT
python -m power_control_host output-off --config .\config\devices.local.yaml --device psw_01 --channel OUT
```

## 六、如果 VISA 连不上怎么办

先别急着判断设备不支持。

请按这个顺序排查：

1. 先确认设备和电脑能互相 `ping` 通
2. 用厂家软件确认设备在线
3. 核对编程手册里的接口方式
4. 核对是不是应该用 `TCPIP0::...::INSTR`
5. 如果不是标准 VISA 资源，改走 `socket`
6. 如果设备实际接的是串口，改走 `serial`

## 七、这一阶段要留下什么

- 现场设备清单
- 设备铭牌照片
- 接口与 IP 记录
- `*IDN?` 返回结果
- 基础控制命令测试记录
- 遇到的问题与结论

## 八、下一步做什么

这一步完成后，就可以开始补第三步：

- 把 ODP / PSW 的命令细节按真实设备结果校正
- 增加批量轮询与 1 秒采样
- 开始做时序控制模型
