# USB 首次通信操作

这份文档只做一件事情：先不管 LAN，也先不急着写 YAML，先用 USB 验证设备是否能通过 VISA 被识别，并成功返回 `*IDN?`。

## 1. 这一步要达到什么结果

完成这一步后，你应该拿到两样东西：

- 设备在电脑上的 VISA 资源名
- 设备对 `*IDN?` 的真实返回结果

只要这两样拿到了，后面再填 `devices.local.yaml` 就容易很多。

## 2. 先准备什么

- 1 台要测试的设备
- 1 根对应的 USB 线
- Windows 开发电脑
- 已安装 Python
- 已安装 NI-VISA

## 3. 先连接设备

1. 给设备接电并开机
2. 用 USB 线把设备和电脑连起来
3. 等 Windows 识别设备
4. 如厂家要求安装 USB 驱动，请先装好驱动

## 4. 进入项目目录

```powershell
cd D:\科大云盘\项目\可靠性电源原表自动上电上位机开发\power-control-host
```

如果还没建虚拟环境，请先执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## 5. 先列出 VISA 资源

执行：

```powershell
python -m power_control_host list-visa-resources
```

如果设备已被识别，你会看到类似下面的输出：

```text
当前可见 VISA 资源:
- USB0::0x1234::0x5678::INSTR
```

请把这条完整资源字符串记下来。

## 6. 直接发送 `*IDN?`

把上一步拿到的资源字符串原样带入：

```powershell
python -m power_control_host probe-visa --resource "USB0::0x1234::0x5678::INSTR"
```

默认发送的是 `*IDN?`。

如果成功，输出会类似：

```text
resource: USB0::0x1234::0x5678::INSTR
command: *IDN?
response: OWON,ODP3122,...
```

## 7. 成功后再填 YAML

如果 `probe-visa` 成功，再去改：

- `config/devices.local.yaml`

你只需要重点改这一行：

```yaml
resource: "这里替换成 probe-visa 成功的那条完整资源字符串"
```

也就是说，不需要自己猜资源名，直接把命令输出原样粘进去就可以。

## 8. 常见情况

### 8.1 `list-visa-resources` 什么都没有

说明设备还没有被 VISA 正确识别。优先检查：

1. USB 线是否正常
2. 设备是否开机
3. 驱动是否安装
4. NI-VISA 是否安装
5. 厂家软件是否能识别设备

### 8.2 能列出资源，但 `probe-visa` 失败

说明设备被识别了，但当前通信参数还没完全对上。优先检查：

1. 设备是否真的支持 USB VISA
2. 编程手册是否要求特殊终止符
3. 是否需要厂商驱动
4. 是否有设备被其他软件占用

### 8.3 `*IDN?` 成功了，下一步是什么

顺序建议是：

1. 把成功的资源名写进 `devices.local.yaml`
2. 用 `probe-idn --device ...` 再走一遍项目配置流程
3. 再测试 `set-voltage`
4. 再测试 `set-current`
5. 再测试 `output-on` / `output-off`
6. 最后再切到 LAN
