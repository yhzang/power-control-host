# Manual Tests

这个目录放的是真实设备人工联调文件，不是自动化测试。

## 这个目录做什么

- 放 `ipynb` 或一次性的联调脚本
- 用来连真实设备，手动一块一块验证
- 记录当前阶段最重要的命令链

## 和 `tests/` 的区别

- `manual-tests/`
  面向真实设备人工联调
- `tests/`
  面向后续自动化回归测试

当前项目里：

- `tests/` 还是自动化测试占位目录
- 真实设备联调入口先放在这里

## 当前可用文件

- [`odp_socket_probe.ipynb`](odp_socket_probe.ipynb)

这个 notebook 专门用于：

- 验证 `ODP` 的 `socket` 连接
- 一块一块执行 `*IDN? / INST / VOLT / CURR / OUTP / MEAS`
- 把结果记录下来，再据此收口设备驱动

## 当前建议的使用顺序

1. 先改 notebook 第一块里的 `HOST / PORT / CHANNEL`
2. 先运行辅助函数块，确认 `send_scpi()` 正常
3. 按顺序运行：
   - `*IDN?`
   - `INST CH1`
   - `VOLT 5`
   - `CURR 0.5`
   - `OUTP ON`
   - `MEAS:VOLT?`
   - `MEAS:CURR?`
   - `OUTP OFF`
4. 记录每一步是否成功、返回了什么、设备面板是否变化

## 后续扩展

如果后面补回 `PSW` 或多设备联调，可以继续在这个目录下新增：

- `psw_visa_probe.ipynb`
- `multi_device_smoke.ipynb`
