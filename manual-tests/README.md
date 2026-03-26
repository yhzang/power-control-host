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

- `tests/` 放自动化回归测试
- 真实设备联调入口放在这里

## 当前可用文件

- [`odp_socket_probe.ipynb`](odp_socket_probe.ipynb)
  用于底层 `SCPI` 探针联调：
  - 验证 `ODP` 的 `socket` 连接
  - 一块一块执行 `*IDN? / INST / VOLT / CURR / OUTP / MEAS`
  - 把结果记录下来，再据此收口设备驱动
- [`odp_sequence_manual.ipynb`](odp_sequence_manual.ipynb)
  用于上层时序功能联调：
  - 默认读取当前仓库的 `config/devices.local.yaml`
  - 默认联调设备 `odp_01`
  - 按块手动测试 `run-cycle / run-parallel-cycle / run-relative-cycle / run-staggered-cycle`
  - 预览计划后再真实执行，并把日志写到 `runtime/sequence_logs/`

## 当前建议的使用顺序

### 1. 先做底层命令确认

先打开 [`odp_socket_probe.ipynb`](odp_socket_probe.ipynb)：

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

### 2. 再做上层时序验证

然后打开 [`odp_sequence_manual.ipynb`](odp_sequence_manual.ipynb)：

1. 先运行参数与初始化单元
2. 对每一种时序，先执行“预览计划”单元，再执行“真实运行”单元
3. 建议顺序：
   - 单通道循环
   - 双通道同起点独立循环
   - 双通道相对时序循环
   - 双通道后上先下兼容入口
4. 每次执行后检查：
   - 设备面板状态
   - 两个通道的开关顺序
   - `runtime/sequence_logs/` 下生成的 CSV

## 后续扩展

如果后面补回 `PSW` 或多设备联调，可以继续在这个目录下新增：

- `psw_visa_probe.ipynb`
- `multi_device_smoke.ipynb`
