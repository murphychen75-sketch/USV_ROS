# usv_interfaces

此包为 USV（无人水面车辆）目标融合与控制系统提供统一的 ROS 2 接口定义：包含自定义消息（msg）、服务（srv）、动作（action）以及 C++/Python 的话题与 Frame 常量定义。

目的：为感知、融合、控制与任务管理模块提供一致的数据契约，使用动态传感器模板技术管理多个同类型设备，从而解耦应用层与底层的通信，并方便随时增减设备。

## 包边界

`usv_interfaces` 只承载协议无关的内部语义接口，不放置 MQTT、MAVLink、串口、UDP 等外部通信协议的桥接实现。

外部通信相关功能包统一放在 `src/usv_comm/` 下，例如：

- `usv_mqtt_bridge`
- `usv_mavlink_bridge`

这些通信包可以依赖 `usv_interfaces`，将内部 ROS 语义映射为外部协议格式；`usv_interfaces` 不反向依赖任何外部传输库或协议细节。

---

## 主要内容与特性

- **自定义消息/服务/动作**：覆盖感知、状态、控制、任务执行（含 MQTT task 进度/完成语义）等核心结构。
- **模板化传感器话题（Dynamic Topic Templates）**：通过加入 `{sensor_name}` 的占位符进行接口的动态扩展。
- **全局一致的接入点常量**：所有核心系统节点通信使用统一的常变量定义，杜绝硬编码话题字符串。

## MQTT 对齐说明（2026-05）

本次接口改造目标是让 `usv_interfaces` 能完整承载 `usv_mqtt_bridge` 协议侧语义，尤其是：

- 新增任务进度上报：`event/task_prog` <-> `TaskProgress.msg`
- 新增任务执行动作：`ExecuteAutoTask.action`
- 为 MQTT 下行 `service/*` 补齐内部强类型 `srv/*`（`EStop/Arm/SetMode/ManualControl/SetParams/IoControl/DiagRequest/VideoControl/RadarNavConfig`）
- 补齐一批上行状态类消息（如 `AlarmEvent`、`DiagResult`、`McuStatus`、`GpsStatus`、`BatteryStatus`、`FuelStatus`、`IoStatus`、`RadarNavScan`、`RadarNavMap` 等）

> 注意：`usv_interfaces` 只定义 ROS 语义，不直接定义 MQTT topic；具体协议映射在 `usv_comm/usv_mqtt_bridge/docs/message_contract.md`。

## 仓库结构

```text
usv_interfaces/
├── CMakeLists.txt        # 构建规则与消息生成配置
├── package.xml           # 节点依赖声明
├── msg/                  # 自定义 ROS 2 消息结构定义
│   ├── VesselState.msg
│   ├── TaskProgress.msg          # 新增：任务进度（event/task_prog 对齐）
│   ├── AlarmEvent.msg / DiagResult.msg
│   ├── JetsonStatus.msg / McuStatus.msg
│   ├── GpsStatus.msg / WeatherStatus.msg / DepthStatus.msg
│   ├── BatteryStatus.msg / FuelStatus.msg / IoStatus.msg / AisRaw.msg
│   ├── RadarNavScan.msg / RadarNavMap.msg / RadarMmObstacles.msg
│   └── ...（其余消息见 CMakeLists.txt 的 MSG_FILES）
├── srv/                  
│   ├── EStop.srv / Arm.srv / SetMode.srv
│   ├── ManualControl.srv / SetParams.srv
│   ├── IoControl.srv / DiagRequest.srv
│   └── VideoControl.srv / RadarNavConfig.srv
├── action/               
│   └── ExecuteAutoTask.action    # MQTT auto_task 对齐动作
├── include/usv_interfaces/
│   └── topics.hpp        # C++ 端统一 Topics与Templates 常量头文件
└── usv_interfaces/
    └── topics.py         # Python 端统一 Topics与Templates 常量库
```

---

## 常量定义与话题分配 (Topics & Frames)

系统全面去除了传感器的话题硬编码。我们将它们分为了两类：**系统核心状态话题** 与 **动态模板型传感器话题**。两者常量已在 C++ 侧的 `topics.hpp` 及 Python 侧的 `topics.py` 提供。

### 1. 系统核心常量枚举

我们在 `topics.py` 中定义了一系列全局统一接入点：

| 变量名称 | 实际发布的话题路径 | 消息类型 (ROS Type) | 作用说明 |
| :--- | :--- | :--- | :--- |
| `TOPIC_VESSEL_STATE` | `/usv/state/vessel` | `usv_interfaces/VesselState` | USV整体融合状态 |
| `TOPIC_CONTROL_DEVIATION`| `/usv/control/deviation` | `usv_interfaces/ControlDeviation` | 当前控制偏误与状态 |
| `TOPIC_TASK_PROGRESS` | `/usv/task/progress` | `usv_interfaces/TaskProgress` | MQTT `event/task_prog` 对齐 |
| `ACTION_EXECUTE_AUTO_TASK` | `/usv/task/execute_auto_task` | `usv_interfaces/action/ExecuteAutoTask` | MQTT `service/auto_task` 对齐 |
| `SERVICE_ESTOP` | `/usv/service/estop` | `usv_interfaces/srv/EStop` | 急停服务 |
| `SERVICE_SET_MODE` | `/usv/service/set_mode` | `usv_interfaces/srv/SetMode` | 模式切换服务 |
| `SERVICE_DIAG_REQUEST` | `/usv/service/diag_request` | `usv_interfaces/srv/DiagRequest` | 自检请求服务 |

## 去重执行结论（已执行）

本包已按 MQTT 对齐策略直接移除旧重复接口，不再保留兼容入口：

- 已删除 `ControlDevice.srv`（由 `IoControl/VideoControl/DiagRequest/...` 专用服务替代）
- 已删除 `ExecuteMission.action`（由 `ExecuteAutoTask.action` 替代）
- 已移除旧常量 `TOPIC_CONTROL_MODE`、`TOPIC_WAYPOINT_ROUTE`

保留原则：

1. 控制请求统一走 `srv/*` 或 `action/*`。  
2. 状态/进度统一走专用 `msg` topic（如 `TOPIC_TASK_PROGRESS`）。  
3. MQTT 映射唯一基准为 `usv_mqtt_bridge/docs/message_contract.md`。  

### 2. 传感器动态模板 (Dynamic Templates) - **重要**

为应对“无限个”且动态挂载的传感器支持，原有的静态路径（如 `/sensors/lidar/front/points`）被改为模板化接口。常量名以 `TEMPLATE_` 为前缀，在实际运行时通过注入 `sensor_name` 获取真实话题名。

**可用模板列表：**
- `TEMPLATE_CAMERA = "/sensors/camera/{sensor_name}/image_raw"`
- `TEMPLATE_LIDAR = "/sensors/lidar/{sensor_name}/points"`
- `TEMPLATE_GPS = "/sensors/gps/{sensor_name}/fix"`
- `TEMPLATE_IMU = "/sensors/imu/{sensor_name}/data"`

**示例 - Python中实例化模板话题：**
```python
from usv_interfaces import topics

# 假设我们在 YAML 文件中配置了一个叫 main_cam 的摄像头
my_camera_name = "main_cam"

# 此处将生成真实的ROS话题: "/sensors/camera/main_cam/image_raw"
real_topic = topics.TEMPLATE_CAMERA.format(sensor_name=my_camera_name)

self.sub = self.create_subscription(Image, real_topic, self.img_callback, 10)
```
*在底层，仿真器的 `session_manager.py` 也在使用该方法动态配置与Gazebo的 ros_gz_bridge。*

---

## 核心消息接口字段 (Messages Reference)

### 1. 任务执行接口
用于统一承载 MQTT `service/auto_task` 的请求/反馈/结果语义：

**`ExecuteAutoTask.action`（新增）**
```yaml
# Goal
string task_id
string command
usv_interfaces/Waypoint[] waypoints
string mode
bool loop_execution
---
# Result
bool success
int32 code
uint8 final_state
string task_id
int32 error_code
string message
---
# Feedback
string task_id
uint8 state
float32 progress_percent
uint32 current_waypoint_index
string status_text
int32 error_code
uint64 start_time_ms
uint64 end_time_ms
```

### 2. USV 全局状态结构
在数字孪生与控制侧，我们将多路传感器的数据归约在同一个包中下发。

**`VesselState.msg`**
```yaml
std_msgs/Header header
float64 latitude            # 经地理融合的纬度
float64 longitude           # 经地理融合的经度
geometry_msgs/Pose pose     # 局部的位置(x,y,z)及姿态四元数
geometry_msgs/Twist velocity# 线速度与角速度
float32 roll / pitch / yaw  # [衍生辅助] 欧拉角方便上层业务使用
float32 battery_voltage     # 电量监控
bool leak_detected          # 故障报警：漏水探测
```

### 3. 操作模式枚举
**`OperationMode.msg`**
```yaml
std_msgs/Header header
uint8 mode                  # 当前模式 (0:手动, 1:定循, 2:避障, 3:自主)
# 附带的常量... (MODE_MANUAL=0, ...)
```

---

## 构建与使用引入

### 构建流程
需确保环境在 ROS 2（例如 Humble/Iron / Foxy等）中。
```bash
cd ~/USV_ROS
colcon build --packages-select usv_interfaces
source install/setup.bash
```
*依赖声明：编译时依赖 `geometry_msgs`, `nav_msgs`, `std_msgs` 以及雷达扩展所需的 `marine_sensor_msgs`。*

### C++ 使用快速示例
```cpp
#include <rclcpp/rclcpp.hpp>
#include <usv_interfaces/msg/vessel_state.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <usv_interfaces/action/execute_auto_task.hpp>
#include <usv_interfaces/topics.hpp> // 引入宏定义常量

// ... 节点初始化略
// 1. 发布船舶状态，使用静态常量
auto state_pub_ = this->create_publisher<usv_interfaces::msg::VesselState>(
    usv_interfaces::TOPIC_VESSEL_STATE, 10);

// 2. 发送自动任务 Action Goal（示意）
using ExecuteAutoTask = usv_interfaces::action::ExecuteAutoTask;
auto action_client = rclcpp_action::create_client<ExecuteAutoTask>(
    node, usv_interfaces::ACTION_EXECUTE_AUTO_TASK);
```

---

## 许可证与贡献指南
- **版本**：0.2.0
- **许可证**：Apache-2.0
- **修改须知**：当您需要增加传感器类型并在全局应用时，请首选在 `topics.py` / `topics.hpp` 中添加对应的 `TEMPLATE_` 字符串规则，并在桥接节点做好相应的桥接支持。
