# 多设备时序功能实现计划

## 概述

本文档描述如何在现有单设备时序基础上，添加**跨设备多通道时序控制**功能，支持40台设备中任意7-8台设备的通道进行复杂时序编排。

## 需求回顾

### 功能需求
- **设备规模**: 40台电源（ODP + PSW混合）
- **并发执行**: 单次可运行7-8台设备的时序
- **跨设备时序**: 任意设备的通道可以相对另一台设备的通道设置时序关系
- **时序模型**: 每个通道指定绝对上电时刻和下电时刻（相对周期开始）
- **循环执行**: 支持指定循环次数或无限循环
- **设备命名**: 使用设备序列号（从*IDN?解析）作为显示名称

### 时序示例
```
周期时长: 60秒
循环次数: 10次

节点1: odp_01.CH1  上电=0s   下电=50s   (主电源，持续50秒)
节点2: odp_02.CH1  上电=5s   下电=45s   (延迟5秒上电，提前5秒下电)
节点3: psw_01.OUT  上电=10s  下电=40s   (延迟10秒上电，提前10秒下电)
```

### 非功能需求
- **向后兼容**: 现有4种CLI命令继续工作
- **最小改动**: 复用现有排序和执行逻辑
- **可测试**: 新功能可独立测试
- **可扩展**: 为后续GUI开发预留接口

---

## 实现阶段

### 阶段1: 核心数据模型 (1-2小时)

#### 1.1 新增数据模型

**文件**: `src/power_control_host/models.py`

添加以下dataclass:

```python
@dataclass(slots=True)
class TimingNode:
    """单个设备通道的时序节点"""
    device_id: str              # 设备ID（可以是序列号）
    channel: str                # 通道名 (CH1, CH2, OUT等)
    on_time_seconds: float      # 上电时刻（相对周期开始的绝对偏移）
    off_time_seconds: float     # 下电时刻（相对周期开始的绝对偏移）
    voltage: float | None = None
    current: float | None = None
    enabled: bool = True        # 是否启用
    description: str = ""       # 说明

@dataclass(slots=True)
class MultiDeviceTimingSpec:
    """多设备时序配置"""
    name: str                   # 配置名称
    nodes: list[TimingNode]     # 时序节点列表
    cycles: int = 1             # 循环次数（0=无限循环）
    cycle_period_seconds: float = 0.0  # 周期时长（0=自动计算）
```

**验证点**:
- [ ] 数据模型定义完成
- [ ] 类型提示正确
- [ ] 可以正常导入

---

### 阶段2: 多设备计划构建器 (2-3小时)

#### 2.1 添加 SequenceService 方法

**文件**: `src/power_control_host/services/sequence_service.py`

添加以下方法:

```python
def build_multi_device_timing_plan(
    self,
    *,
    spec: MultiDeviceTimingSpec,
    name: str | None = None,
) -> SequencePlan:
    """从多设备时序配置构建执行计划

    核心逻辑:
    1. 验证所有设备和通道存在
    2. 计算周期时长（如果未指定）
    3. 为每个启用的节点生成 on/off 动作
    4. 复用 _build_plan_from_actions() 排序和插入wait
    """
    pass

def _normalize_timing_nodes(self, nodes: list[TimingNode]) -> list[TimingNode]:
    """验证和规范化时序节点

    验证项:
    - 设备ID存在
    - 通道名合法
    - on_time >= 0
    - off_time > on_time
    """
    pass
```

**实现要点**:
- 复用现有的 `_build_channel_map()` 和 `_resolve_channel_name()`
- 复用现有的 `_build_setpoint_actions()` 生成电压/电流设置
- 复用现有的 `_build_plan_from_actions()` 进行排序和wait插入
- 周期时长自动计算: `max(node.off_time_seconds for node in enabled_nodes)`

**验证点**:
- [ ] 方法实现完成
- [ ] 单设备多通道测试通过
- [ ] 多设备单通道测试通过
- [ ] 多设备多通道测试通过
- [ ] 验证逻辑正确（设备不存在、通道不存在、时序非法）

---

### 阶段3: 连接池管理 (1-2小时)

#### 3.1 创建连接池类

**新文件**: `src/power_control_host/services/device_pool.py`

```python
class DeviceConnectionPool:
    """设备连接池 - 管理多个设备的持久连接"""

    def __init__(self, device_service: DeviceService):
        self.device_service = device_service
        self.connected_devices: dict[str, PowerSupplyDevice] = {}

    def connect_devices(self, device_ids: list[str]) -> None:
        """预连接所有需要的设备"""
        pass

    def get_device(self, device_id: str) -> PowerSupplyDevice:
        """获取已连接的设备"""
        pass

    def disconnect_all(self) -> None:
        """断开所有设备"""
        pass

    @contextmanager
    def managed_connections(self, device_ids: list[str]):
        """上下文管理器 - 自动连接和断开"""
        pass
```

**实现要点**:
- 使用 `dict[str, PowerSupplyDevice]` 存储已连接设备
- `connect_devices()` 批量连接，跳过已连接的
- `disconnect_all()` 忽略断开时的异常
- `managed_connections()` 使用 try/finally 保证清理

**验证点**:
- [ ] 类实现完成
- [ ] 可以连接多个设备
- [ ] 上下文管理器正确清理
- [ ] 异常情况下也能断开连接

---

### 阶段4: 执行引擎改造 (2-3小时)

#### 4.1 添加支持取消的执行方法

**文件**: `src/power_control_host/services/sequence_service.py`

修改 `__init__`:
```python
def __init__(self, ...):
    # 现有代码...
    self._cancel_flag = threading.Event()  # 取消标志
```

添加新方法:
```python
def execute_plan_with_pool(
    self,
    plan: SequencePlan,
    *,
    log_path: str | Path | None = None,
) -> list[SequenceExecutionEvent]:
    """使用连接池执行计划（支持多设备 + 取消）

    核心逻辑:
    1. 提取所有涉及的设备ID
    2. 创建连接池并预连接所有设备
    3. 执行步骤，每个wait分段检查取消标志
    4. finally块中断开所有连接
    """
    pass

def cancel_execution(self) -> None:
    """取消正在执行的计划"""
    self._cancel_flag.set()
```

**实现要点**:
- 使用 `threading.Event` 作为取消标志
- wait步骤分段sleep（每0.1秒检查一次）
- 取消后记录 "cancelled" 事件
- 保持现有 `execute_plan()` 不变（向后兼容）

**验证点**:
- [ ] 方法实现完成
- [ ] 多设备执行测试通过
- [ ] 取消功能测试通过
- [ ] 连接池正确清理
- [ ] 现有 `execute_plan()` 仍然工作

---

### 阶段5: 设备序列号支持 (1小时)

#### 5.1 添加序列号解析

**文件**: `src/power_control_host/services/device_service.py`

添加方法:
```python
def get_device_serial_number(self, device_id: str) -> str:
    """从*IDN?响应中提取序列号

    *IDN? 格式: MANUFACTURER,MODEL,SERIAL,FIRMWARE
    例如: OWON,ODP3012,24320076,FV:V3.9.0
    """
    pass

def list_devices_with_serial(self) -> list[dict[str, str]]:
    """列出所有设备及其序列号

    返回格式:
    [
        {"device_id": "odp_01", "model": "ODP3012", "serial_number": "24320076"},
        ...
    ]
    """
    pass
```

**实现要点**:
- 解析 *IDN? 响应的第3个字段（逗号分隔）
- 解析失败时返回 device_id 作为fallback
- 批量查询时捕获异常，标记为 "unknown"

**验证点**:
- [ ] 方法实现完成
- [ ] ODP序列号解析正确
- [ ] PSW序列号解析正确
- [ ] 解析失败时有fallback

---

### 阶段6: 配置持久化 (1-2小时)

#### 6.1 创建配置保存/加载模块

**新文件**: `src/power_control_host/services/timing_config.py`

```python
def save_timing_config(spec: MultiDeviceTimingSpec, path: Path) -> None:
    """保存时序配置到JSON文件"""
    pass

def load_timing_config(path: Path) -> MultiDeviceTimingSpec:
    """从JSON文件加载时序配置"""
    pass
```

**JSON格式示例**:
```json
{
  "name": "7设备交错上电测试",
  "cycles": 10,
  "cycle_period_seconds": 60.0,
  "nodes": [
    {
      "device_id": "odp_01",
      "channel": "CH1",
      "on_time_seconds": 0.0,
      "off_time_seconds": 50.0,
      "voltage": 12.0,
      "current": 1.0,
      "enabled": true,
      "description": "主电源"
    }
  ]
}
```

**实现要点**:
- 使用 `dataclasses.asdict()` 序列化
- 使用 `json.dump()` 保存，`indent=2, ensure_ascii=False`
- 加载时手动构造 TimingNode 和 MultiDeviceTimingSpec

**验证点**:
- [ ] 保存功能实现
- [ ] 加载功能实现
- [ ] 往返测试通过（save -> load -> 数据一致）
- [ ] 中文描述正确保存

---

### 阶段7: CLI命令 (1小时)

#### 7.1 添加新CLI命令

**文件**: `src/power_control_host/ui/cli.py`

添加子命令:
```python
multi_device_parser = subparsers.add_parser(
    "run-multi-device-timing",
    help="Run multi-device timing sequence from config file.",
)
multi_device_parser.add_argument("--config-file", required=True, help="Path to timing config JSON file.")
multi_device_parser.add_argument("--log-file", help="Optional CSV log path.")
```

添加处理逻辑:
```python
if args.command == "run-multi-device-timing":
    from power_control_host.services.timing_config import load_timing_config

    config_path = Path(args.config_file)
    spec = load_timing_config(config_path)

    plan = app.sequence_service.build_multi_device_timing_plan(spec=spec)
    log_path = resolve_sequence_log_path(args.log_file, plan.name)

    print(f"执行多设备时序: {spec.name}")
    print(f"涉及设备: {len(set(n.device_id for n in spec.nodes if n.enabled))} 台")
    print(f"时序节点: {len([n for n in spec.nodes if n.enabled])} 个")
    print(f"循环次数: {spec.cycles}")

    events = app.sequence_service.execute_plan_with_pool(plan, log_path=log_path)
    print_sequence_summary(plan.name, events, log_path)
    return 0
```

#### 7.2 修改 show-devices 命令

显示设备序列号:
```python
if args.command == "show-devices":
    devices_info = app.device_service.list_devices_with_serial()
    for info in devices_info:
        print(f"{info['device_id']} ({info['model']}) - SN: {info['serial_number']}")
    return 0
```

**验证点**:
- [ ] CLI命令添加完成
- [ ] 可以从JSON加载配置
- [ ] 可以执行多设备时序
- [ ] show-devices显示序列号

---

### 阶段8: 测试 (2-3小时)

#### 8.1 单元测试

**新文件**: `tests/test_multi_device_timing.py`

测试用例:
```python
def test_build_multi_device_timing_plan_single_device():
    """测试单设备多通道"""
    pass

def test_build_multi_device_timing_plan_multi_device():
    """测试多设备单通道"""
    pass

def test_build_multi_device_timing_plan_complex():
    """测试多设备多通道复杂时序"""
    pass

def test_timing_node_validation():
    """测试时序节点验证逻辑"""
    pass

def test_device_pool_connection():
    """测试连接池管理"""
    pass

def test_execution_cancellation():
    """测试取消功能"""
    pass

def test_config_persistence():
    """测试配置保存/加载"""
    pass
```

#### 8.2 集成测试

**新文件**: `manual-tests/multi_device_timing_manual.ipynb`

测试场景:
1. 创建3设备时序配置
2. 保存配置到JSON
3. 加载配置
4. 执行时序（使用mock设备）
5. 验证事件日志

**验证点**:
- [ ] 所有单元测试通过
- [ ] 集成测试notebook可运行
- [ ] 现有测试仍然通过（回归测试）

---

### 阶段9: 文档更新 (1小时)

#### 9.1 更新README

**文件**: `README.md`

添加章节:
- 多设备时序功能说明
- 配置文件格式
- CLI使用示例

#### 9.2 更新架构文档

**文件**: `docs/02-architecture-roadmap.md`

添加:
- 连接池层说明
- 多设备时序流程图

#### 9.3 更新变更日志

**文件**: `docs/03-changelog.md`

记录:
- 新增功能
- 新增文件
- 修改文件

**验证点**:
- [ ] README更新完成
- [ ] 架构文档更新完成
- [ ] 变更日志更新完成

---

## 配置文件示例

### timing_config_example.json

```json
{
  "name": "7设备交错上电测试",
  "cycles": 10,
  "cycle_period_seconds": 60.0,
  "nodes": [
    {
      "device_id": "odp_01",
      "channel": "CH1",
      "on_time_seconds": 0.0,
      "off_time_seconds": 50.0,
      "voltage": 12.0,
      "current": 1.0,
      "enabled": true,
      "description": "主电源"
    },
    {
      "device_id": "odp_02",
      "channel": "CH1",
      "on_time_seconds": 5.0,
      "off_time_seconds": 45.0,
      "voltage": 5.0,
      "current": 2.0,
      "enabled": true,
      "description": "延迟5秒上电，提前5秒下电"
    },
    {
      "device_id": "odp_03",
      "channel": "CH2",
      "on_time_seconds": 10.0,
      "off_time_seconds": 40.0,
      "voltage": 24.0,
      "enabled": true,
      "description": "延迟10秒上电，提前10秒下电"
    },
    {
      "device_id": "psw_01",
      "channel": "OUT",
      "on_time_seconds": 15.0,
      "off_time_seconds": 35.0,
      "voltage": 48.0,
      "enabled": true,
      "description": "延迟15秒上电"
    },
    {
      "device_id": "odp_04",
      "channel": "CH1",
      "on_time_seconds": 20.0,
      "off_time_seconds": 30.0,
      "voltage": 3.3,
      "current": 3.0,
      "enabled": false,
      "description": "禁用的节点"
    }
  ]
}
```

---

## 使用示例

### 1. 准备配置文件

创建 `my_timing.json`:
```json
{
  "name": "测试时序",
  "cycles": 5,
  "cycle_period_seconds": 30.0,
  "nodes": [
    {
      "device_id": "odp_01",
      "channel": "CH1",
      "on_time_seconds": 0.0,
      "off_time_seconds": 20.0,
      "voltage": 12.0,
      "enabled": true,
      "description": "主电源"
    },
    {
      "device_id": "odp_02",
      "channel": "CH1",
      "on_time_seconds": 5.0,
      "off_time_seconds": 15.0,
      "voltage": 5.0,
      "enabled": true,
      "description": "从电源"
    }
  ]
}
```

### 2. 查看设备序列号

```bash
python -m power_control_host --config config/devices.local.yaml show-devices
```

输出:
```
odp_01 (ODP3012) - SN: 24320076
odp_02 (ODP3012) - SN: 24320077
psw_01 (PSW30-72) - SN: GEW161978
```

### 3. 执行多设备时序

```bash
python -m power_control_host --config config/devices.local.yaml \
    run-multi-device-timing --config-file my_timing.json
```

输出:
```
执行多设备时序: 测试时序
涉及设备: 2 台
时序节点: 2 个
循环次数: 5
plan_name: multi_device_测试时序
step_count: 45
log_file: runtime/sequence_logs/multi_device_测试时序_20260409_143022.csv
```

### 4. 查看执行日志

```bash
cat runtime/sequence_logs/multi_device_测试时序_20260409_143022.csv
```

---

## 技术要点

### 1. 为什么复用 _build_plan_from_actions()?

现有的排序和wait插入逻辑已经非常成熟:
- 按 (time_offset, priority, channel) 三级排序
- 自动计算wait步骤
- 支持多设备（device_id在SequenceStep中）

只需要构造正确的 `_ScheduledAction` 列表，就能生成正确的执行计划。

### 2. 为什么需要连接池?

现有 `execute_plan()` 每次切换设备都断开旧连接:
```python
if current_device.config.id != device.config.id:
    current_device.disconnect()  # 断开
    device.connect()              # 重连
```

7-8台设备频繁切换，每次断开/连接有几百ms延迟，时序精度会很差。

连接池预连接所有设备，执行时直接使用，保证时序精度。

### 3. 为什么需要取消功能?

多设备时序可能运行很长时间（几十分钟甚至几小时），需要能够中途停止。

使用 `threading.Event` 作为标志，wait步骤分段检查，既能快速响应取消，又不影响时序精度。

### 4. 为什么用JSON而不是YAML?

- JSON更简单，Python标准库支持
- 配置文件由程序生成（后续GUI），不需要手写
- 数据结构简单，不需要YAML的高级特性

---

## 风险和注意事项

### 1. 设备通信超时

多设备并发时，某个设备通信超时会阻塞整个时序。

**缓解措施**:
- 配置合理的超时时间（3秒）
- 连接池预连接时检测设备可用性
- 执行前验证所有设备在线

### 2. 时序精度

Python的 `time.sleep()` 精度有限（Windows上约15ms）。

**缓解措施**:
- 使用9位小数精度存储时间
- wait步骤尽量合并（现有逻辑已实现）
- 关键时序点使用硬件触发（后续考虑）

### 3. 设备状态不一致

执行中途取消或异常，设备可能处于未知状态。

**缓解措施**:
- finally块保证断开连接
- 记录所有执行事件到日志
- 提供设备状态查询命令

### 4. 配置文件错误

用户手写JSON可能有语法错误或逻辑错误。

**缓解措施**:
- 加载时验证JSON格式
- 构建计划时验证设备和通道
- 提供配置文件模板和示例

---

## 总工作量估算

| 阶段 | 工作量 | 优先级 |
|------|--------|--------|
| 1. 核心数据模型 | 1-2小时 | P0 |
| 2. 多设备计划构建器 | 2-3小时 | P0 |
| 3. 连接池管理 | 1-2小时 | P0 |
| 4. 执行引擎改造 | 2-3小时 | P0 |
| 5. 设备序列号支持 | 1小时 | P1 |
| 6. 配置持久化 | 1-2小时 | P0 |
| 7. CLI命令 | 1小时 | P0 |
| 8. 测试 | 2-3小时 | P0 |
| 9. 文档更新 | 1小时 | P1 |
| **总计** | **12-18小时** | |

建议分2-3天完成，每天4-6小时。

---

## 下一步行动

1. **立即开始**: 阶段1（数据模型）
2. **第一天完成**: 阶段1-4（核心功能）
3. **第二天完成**: 阶段5-7（辅助功能）
4. **第三天完成**: 阶段8-9（测试和文档）

完成后即可支持多设备时序，为后续GUI开发打好基础。
