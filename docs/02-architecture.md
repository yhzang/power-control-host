# 架构说明

## 分层思路

```text
UI / CLI
    |
Application
    |
Services
    |
Devices
    |
Transports
```

## 各层职责

### UI / CLI

- 提供最小的命令行入口
- 后续可替换为 PySide6 GUI

### Application

- 统一启动流程
- 统一装配配置、日志、服务

### Services

- 组织业务流程
- 管理设备列表
- 管理时序计划、日志导出

### Devices

- 抽象不同品牌和型号的电源行为
- 屏蔽上层对设备协议细节的感知

### Transports

- 提供 VISA、Socket、Serial 三种传输能力
- 让设备驱动只关心“发什么命令”，不关心“底层怎么发”

## 设备抽象原则

统一向上暴露：

- identify
- set_voltage
- set_current
- output_on
- output_off
- read_voltage
- read_current

这样未来增加新品牌时，只需补新的设备驱动，不必改业务层。

