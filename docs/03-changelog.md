# 03 变更记录

## 2026-03-31

### 本次做了什么

1. **确认 PSW 通信方式**：PSW 走 LAN socket，port 2268，与 ODP（port 4196）同样方式直连。
2. **新增 `discovery.py`**：设备自动扫描模块。
3. **新增 CLI 子命令 `scan-devices`**：扫描局域网发现 ODP / PSW。
4. **更新 README**：精简重写，去掉 AI 对话口吻，增加 PSW cycle 说明和设备发现说明。
5. **更新 `docs/01-stage-results.md`**：记录当前阶段成果，增加 PSW 通信参数、PSW cycle 验证流程。
6. **更新 `docs/02-architecture-roadmap.md`**：增加发现层说明，更新已完成阶段列表，补全路线表。

---

### 新增文件

#### `src/power_control_host/discovery.py`

功能：
- 并发扫描指定子网（默认 `192.168.1.1-254`）的 ODP port 4196 和 PSW port 2268
- 对每个响应发送 `*IDN?`，按返回内容识别设备类型（OWON → ODP，GW-INSTEK → PSW）
- 自动推断 `suggested_id`（`odp_01`、`psw_01` 等递增编号）
- 自动推断逻辑通道（ODP3012 → CH1/CH2，ODP3032/3033 → CH1/CH2/CH3，PSW → OUT）
- `scan_subnet()` 返回 `DiscoveredDevice` 列表
- `devices_to_yaml()` 把列表转成可直接粘贴的 `devices.yaml` 片段

关联文件：
- `src/power_control_host/ui/cli.py`（`scan-devices` 子命令调用此模块）

---

### 修改文件

#### `src/power_control_host/ui/cli.py`

- 新增 `from power_control_host.discovery import devices_to_yaml, scan_subnet`
- 新增子命令 `scan-devices`，参数：`--subnet`、`--timeout-ms`、`--workers`、`--emit-yaml`
- 新增对应处理分支，打印发现结果，`--emit-yaml` 时追加输出 YAML 片段

---

### PSW cycle 现状说明

PSW 无需额外开发即可直接使用全部 4 种 cycle 命令：

- `run-cycle`
- `run-parallel-cycle`
- `run-relative-cycle`
- `run-staggered-cycle`

原因：`sequence_service.py` 通过 `PowerSupplyDevice` 基类接口调用，对设备类型无感知。`psw.py` 已实现所有必要方法。

传参示例：

```powershell
power-control-host --config config/devices.local.yaml run-cycle \
  --device psw_01 --channel OUT --on-seconds 5 --off-seconds 5 --cycles 3
```

---

### 如何测试 scan-devices

```powershell
# 安装依赖
pip install -e .[dev]

# 基础扫描
power-control-host scan-devices

# 超时调整（网络慢时用）
power-control-host scan-devices --timeout-ms 1500

# 输出 YAML 配置片段
power-control-host scan-devices --emit-yaml
```

预期输出：

```
Scanning 192.168.1.1-254 (timeout=1000ms, workers=100) ...
Found N device(s):
  odp_01  192.168.1.1:4196  OWON,ODP3012,24320076,FV:V3.9.0
  psw_01  192.168.1.x:2268  GW-INSTEK,PSW30-72,GEW161978,02.53.20220419
```

如果网络上没有设备，输出 `No devices found.`，属于正常。

自动化测试（语法 + 逻辑）：

```powershell
python -m pytest tests/ -q
```

---

### 修复：device_scan_manual.ipynb 统计单元

`d.vendor` 存储为小写 `'owon'` / `'gwinstek'`，统计单元比对字符串已修正为小写。
关联文件：`manual-tests/device_scan_manual.ipynb` cell-8

---

### 下一步

1. 同步到另一台电脑，安装 venv 跑通测试
2. `scan-devices --emit-yaml` 生成 40 台设备配置
3. 逐台 `probe-idn` 确认连通
4. PSW 现场 `run-cycle` 验证
