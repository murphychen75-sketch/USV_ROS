# usv_interfaces

此包为 USV（无人水面车辆）目标融合与控制系统提供统一的 ROS 2 接口定义：包含自定义消息（msg）、服务（srv）、动作（action）以及 C++/Python 的话题与 Frame 常量定义。

目的：为感知、融合、控制与任务管理模块提供一致的数据契约，使用动态传感器模板技术管理多个同类型设备，从而解耦应用层与底层的通信，并方便随时增减设备。

---

## 主要内容与特性

- **自定义消息与服务**：描述雷达、视觉、AIS、船舶整体状态、控制偏差、动态航路点下发与设备服务等核心语义结构。
- **模板化传感器话题（Dynamic Topic Templates）**：通过加入 `{sensor_name}` 的占位符进行接口的动态扩展。
- **全局一致的接入点常量**：所有核心系统节点通信使用统一的常变量定义，杜绝硬编码话题字符串。

## 仓库结构

```text
usv_interfaces/
├── CMakeLists.txt        # 构建规则与消息生成配置
├── package.xml           # 节点依赖声明
├── msg/                  # 自定义 ROS 2 消息结构定义
│   ├── VesselState.msg           # 船综合状态 (GNSS+里程计+电池等)
│   ├── OperationMode.msg         # 运行模式
│   ├── ControlDeviation.msg      # 控制器偏差输出
│   ├── Waypoint.msg              # 新增：单航路点定义
│   ├── WaypointRoute.msg         # 新增：动态航路点集合
│   └── (各类目标追踪与检测 Array ...)
├── srv/                  
│   └── ControlDevice.srv         # 外部设备控制请求
├── action/               
│   └── ExecuteMission.action     # 任务管线异步执行动作
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
| `TOPIC_CONTROL_MODE` | `/usv/control/mode` | `usv_interfaces/OperationMode` | 当前作业模式 |
| `TOPIC_WAYPOINT_ROUTE` | `/usv/control/waypoint_route`| `usv_interfaces/WaypointRoute` | **[动态下发]** 局部路径点列表 |
| `TOPIC_CMD_VEL` | `/cmd_vel` | `geometry_msgs/Twist` | 速度控制协议 |
| `TOPIC_CMD_THRUSTER_LEFT`| `/wamv/thrusters/left_thrust/cmd_thrust`| `std_msgs/Float64MultiArray` | （底层控制保留）左侧推力指令 |

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

### 1. 动态航路点接口 (新增)
用于替代繁重的任务重载，使得规划算法可按需随时推送期望点序列：

**`Waypoint.msg`**
```yaml
float64 latitude           # 目标点纬度
float64 longitude          # 目标点经度
float64 heading_target     # 期望到达该点时的艏向角 (rad)
float32 speed_target       # 航段期望速度 (m/s)
```
**`WaypointRoute.msg`**
```yaml
std_msgs/Header header
usv_interfaces/Waypoint[] waypoints
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
#include <usv_interfaces/msg/waypoint_route.hpp>
#include <usv_interfaces/topics.hpp> // 引入宏定义常量

// ... 节点初始化略
// 1. 发布船舶状态，使用静态常量
auto state_pub_ = this->create_publisher<usv_interfaces::msg::VesselState>(
    usv_interfaces::TOPIC_VESSEL_STATE, 10);

// 2. 订阅动态航路点
auto wp_sub_ = this->create_subscription<usv_interfaces::msg::WaypointRoute>(
    usv_interfaces::TOPIC_WAYPOINT_ROUTE, 10,
    [](const usv_interfaces::msg::WaypointRoute::SharedPtr msg) {
        RCLCPP_INFO(rclcpp::get_logger("rclcpp"), "Received %zu waypoints", msg->waypoints.size());
    }
);
```

---

## 许可证与贡献指南
- **版本**：0.2.0
- **许可证**：Apache-2.0
- **修改须知**：当您需要增加传感器类型并在全局应用时，请首选在 `topics.py` / `topics.hpp` 中添加对应的 `TEMPLATE_` 字符串规则，并在桥接节点做好相应的桥接支持。
