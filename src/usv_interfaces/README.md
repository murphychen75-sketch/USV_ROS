# usv_interfaces

此包为 USV（无人水面车辆）目标融合与控制系统提供统一的 ROS 2 接口定义：自定义消息（msg）、服务（srv）、动作（action）以及 C++/Python 的话题与 frame 常量。

目的：为感知、融合、控制与任务管理模块提供一致的数据契约，便于多语言节点互操作、快速集成与系统级联调。

---

## 主要内容

- 自定义消息（msg）：描述雷达、视觉、AIS、船舶状态、控制偏差等融合后或控制所需的数据结构。
- 服务（srv）：对设备（例如灯、泵）下发控制命令并获取执行结果。
- 动作（action）：异步任务接口（例如执行航点任务，提供实时 feedback 与最终 result）。
- C++ 与 Python 常量：统一的 topic/frame 名称定义，便于在节点中复用。

## 仓库结构（简要）

- `CMakeLists.txt`：ROS 2（ament）构建脚本，使用 `rosidl_generate_interfaces` 生成接口代码。
- `package.xml`：包元信息与依赖声明（`std_msgs`、`geometry_msgs`、`nav_msgs`、`builtin_interfaces` 等）。
- `msg/`：
  - `AisData.msg` — AIS 信息（MMSI、位置、航向等）。
  - `ControlDeviation.msg` — 控制偏差（横向/航向误差、目标/当前速度等）。
  - `MmwRadarObject.msg` — 毫米波雷达目标（相对位置、速度、RCS 等）。
  - `NavRadarObject.msg` — 导航雷达目标（对地速度、估算绝对位置等）。
  - `VesselState.msg` — 船舶综合状态（GNSS/里程计/IMU 融合的 pose/twist、电池、姿态等）。
  - `VisualObject.msg` — 视觉检测结果（类别、bbox、置信度等）。
  - `OperationMode.msg` — 运行模式常量与当前模式字段。
- `srv/`：
  - `ControlDevice.srv` — 设备控制服务（请求 device_id/command/value，返回 success/message）。
- `action/`：
  - `ExecuteMission.action` — 执行任务的动作接口（goal/feedback/result）。
- `include/usv_interfaces/topics.hpp`：C++ 话题/frame 常量。
- `usv_interfaces/topics.py`：Python 话题/frame 常量（与 C++ 同步）。

## 消息/服务/动作 快速参考

- AisData
  - 字段：header、mmsi、timestamp_utc、latitude、longitude、sog、cog、heading、navigational_status
  - 用途：AIS 目标信息（目标融合／航迹管理）。

- ControlDeviation
  - 字段：header、cross_track_error、heading_error、distance_to_goal、target_speed、current_speed
  - 用途：控制器产生的偏差/误差信息，可用于闭环控制或监控。

- MmwRadarObject
  - 字段：header、id、position、velocity、range、azimuth、rcs
  - 用途：毫米波雷达检测结果（相对位置/速度/强度）。

- NavRadarObject
  - 字段：header、id、sog、cog、range、relative_bearing、position、area、is_moving
  - 用途：导航雷达目标，含对地速度与估算位置。

- VesselState
  - 字段：header、latitude、longitude、altitude、pose、velocity、roll/pitch/yaw、battery_*、leak_detected、cpu_temperature
  - 用途：融合后的本船状态，适用于控制、UI 与记录。

- VisualObject
  - 字段：header、id、class_name、bbox_{x,y,w,h}、relative_bearing、confidence
  - 用途：视觉检测/识别结果。

- OperationMode
  - 模式常量：MODE_MANUAL=0、MODE_AUTO_HEADING=1、MODE_SMART_PATH=2、MODE_AUTO_NAV=3
  - 字段：header、mode

- ControlDevice.srv
  - Request: device_id、command、value
  - Response: success、message

- ExecuteMission.action
  - Goal: mission_file_name、forbidden_zone_file、loop_execution
  - Feedback: current_task_name、current_waypoint_index、mission_progress、status_text
  - Result: success、message

## 常量（C++ / Python）

统一话题与 frame 常量位于：

- C++：`include/usv_interfaces/topics.hpp`
- Python：`usv_interfaces/topics.py`

示例（部分）：

- `TOPIC_VESSEL_STATE = "/usv/state/vessel"`
- `TOPIC_CONTROL_DEVIATION = "/usv/control/deviation"`
- `TOPIC_SENSOR_GPS = "/sensors/gps/data"`

建议在节点中引用这些常量以避免硬编码字符串，便于统一管理与重映射。

## 构建与安装（ROS 2）

在 ROS 2 环境下（例如已 source `/opt/ros/<distro>/setup.bash`）：

```bash
# 从工作区根构建（若 package 在 workspace 中）
cd /home/cczh/USV_ROS
colcon build --packages-select usv_interfaces

# 构建完成后加载环境
source install/setup.bash
```

说明：`CMakeLists.txt` 已使用 `rosidl_generate_interfaces` 和 `ament_python_install_package`，构建将生成 C++/Python 绑定并安装 package。

## 使用示例（简要）

- Python 发布 `VesselState`（示意）：

```python
from rclpy.node import Node
from usv_interfaces.msg import VesselState
from usv_interfaces import topics

class StatePublisher(Node):
    def __init__(self):
        super().__init__('state_pub')
        self.pub = self.create_publisher(VesselState, topics.TOPIC_VESSEL_STATE, 10)
        # 填充消息并发布

```

- C++ 订阅 `ControlDeviation`（示意）：

```cpp
#include "rclcpp/rclcpp.hpp"
#include "usv_interfaces/msg/control_deviation.hpp"
#include "usv_interfaces/topics.hpp"

auto sub = node->create_subscription<usv_interfaces::msg::ControlDeviation>(
    usv_interfaces::TOPIC_CONTROL_DEVIATION, 10,
    [](const usv_interfaces::msg::ControlDeviation::SharedPtr msg){ /* 处理 */ });
```

- Python 调用 `ControlDevice` 服务（示意）：

```python
client = node.create_client(usv_interfaces.srv.ControlDevice, '/control/device')
req = usv_interfaces.srv.ControlDevice.Request()
req.device_id = "nav_light_left"
req.command = "ON"
req.value = 1.0
future = client.call_async(req)
```

关于 `ExecuteMission` action，请参考 ROS 2 的 action 客户端 API (`rclpy.action` / `rclcpp_action`) 获取完整范例。

## 测试与验证建议

- 为每个消息类型编写基本的发布/订阅测试（pytest + rclpy），验证序列化/字段正确性。
- 为 `ExecuteMission` 动作做集成测试（模拟伪执行器，检查 feedback/result）。
- 提供一个小型仿真 demo（将仿真传感器话题映射到本包的常量），用于端到端验证。

## 许可证与贡献

- 包版本（package.xml）：0.1.0
- 许可证：Apache-2.0

贡献指南：提交 PR 时请包含变更说明和最小可运行示例，修改消息时请考虑向后兼容或提供迁移说明。

## 后续建议（优先级）

1. 添加 `examples/`：包含 Python 与 C++ 的最小示例节点（publish/subscribe/service/action）。
2. 增加 CI：在 PR 中运行构建与简单通信测试（colcon build + pytest）。
3. 补充 `StandardDataTypes.md`，明确自定义消息和标准消息的映射与示例。
4. 添加文档生成流程（Sphinx 或其他）以产出在线 API 参考。

---

若需要，我可以另外：

- 在 `examples/` 下生成一个最小的 Python 发布者与订阅者示例。
- 为 README 添加更多示例截图或数据示例。

如果你希望我现在把 README 提交到仓库（已执行），我还可以同时创建示例并运行快速测试。
