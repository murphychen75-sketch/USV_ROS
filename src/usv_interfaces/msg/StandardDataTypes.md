# 原始传感器数据类型对照表

为了保持与 ROS 2 生态的兼容性，本系统中的**原始传感器数据**直接使用 ROS 2 标准消息 (`sensor_msgs`)，不进行自定义封装。

## 当前仿真话题参考

| 数据源 | 话题名称 (Code Constant) | 消息类型 (ROS Type) | 说明 |
| :--- | :--- | :--- | :--- |
| **GPS/GNSS** | `TOPIC_SENSOR_GPS` | `sensor_msgs/NavSatFix` | 包含经纬度、海拔及协方差 |
| **IMU** | `TOPIC_SENSOR_IMU` | `sensor_msgs/Imu` | 包含四元数姿态、角速度、线加速度 |
| **激光雷达** | `TOPIC_SENSOR_LIDAR` | `sensor_msgs/PointCloud2` | 前激光雷达点云数据 |
| **摄像头** | `TOPIC_SENSOR_CAMERA` | `sensor_msgs/Image` | 前摄像头图像数据 |
| **摄像头内参** | `TOPIC_SENSOR_CAMERA_INFO` | `sensor_msgs/CameraInfo` | 前摄像头内参信息 |
| **里程计** | `TOPIC_MODEL_ODOMETRY` | `nav_msgs/Odometry` | WAM-V里程计数据 |
| **位姿** | `TOPIC_MODEL_POSE` | `tf2_msgs/TFMessage` | WAM-V位姿数据 |
| **关节状态** | `TOPIC_MODEL_JOINT_STATE` | `sensor_msgs/JointState` | WAM-V关节状态 |
| **坐标变换** | `TOPIC_TF` | `tf2_msgs/TFMessage` | 坐标变换 |

**注意**：自定义的 `.msg` 文件（如 `VesselState.msg`）用于描述融合后的高级状态信息。

## /sensors/radar/nav/sector — 雷达扇区数据（推荐）

话题: `/sensors/radar/nav/sector`

消息类型: `marine_sensor_msgs/RadarSector`

用途: 海事雷达的“扇区/叶片（sector/spoke）”级别回波序列，适用于导航雷达数据的订阅、可视化与目标检测/融合前处理。

关键字段（以 `marine_sensor_msgs/RadarSector` 常见定义为准，版本差异请以安装的包为准）：
- `std_msgs/Header header` — 时间戳与 `frame_id`（例如 `nav_radar_link`）
- `float64 angle_start` — 扇区起始角（rad）
- `float64 angle_increment` — 每个角度采样的增量（rad）
- `builtin_interfaces/Duration time_increment` — 每个样本之间的时间间隔（可为 0）
- `builtin_interfaces/Duration scan_time` — 完整扫描周期（例如 2.5s）
- `float32 range_min` — 最小测距（m）
- `float32 range_max` — 最大测距（m）
- `marine_sensor_msgs/RadarEcho[] intensities` — 回波强度数组（或按具体定义为 nested 列表，例如每个角度对应一个 echoes 列表）

映射说明（与 Gazebo 插件输出的 `gz.msgs.Float_V` 对应关系）:
- `gz.msgs.Float_V.data[0]` -> `angle_start`
- `gz.msgs.Float_V.data[1]` -> `angle_increment`
- `gz.msgs.Float_V.data[2]` -> `range_bin_resolution`（需结合 `range_min`/`range_max` 计算实际 bin index）
- `gz.msgs.Float_V.data[3...N]` -> `intensities` 中的强度序列（需按 `range_min`/`range_max` 与 `range_bin_resolution` 进行重塑）

部署/本地安装建议（确保构建后本包可以直接引用 `marine_sensor_msgs` 类型）:
1. 将 `marine_msgs`（包含 `marine_sensor_msgs`）源码克隆到你的工作区 `src` 下：

```bash
cd /home/cczh/USV_ROS/src
git clone -b ros2 https://github.com/apl-ocean-engineering/marine_msgs.git
```

2. 构建消息包（在工作区根）：

```bash
cd /home/cczh/USV_ROS
colcon build --packages-select marine_sensor_msgs
source install/setup.bash
```

3. 我已在本包的 `package.xml` 与 `CMakeLists.txt` 中添加了对 `marine_sensor_msgs` 的依赖声明（以便在编译时和运行时能直接引用该消息类型）。如果你在一个新的 workspace 中使用此包，请确保在同一 workspace 下包含 `marine_msgs` 源码或通过 apt 安装对应的二进制包。

注意：不同版本的 `marine_sensor_msgs` 其字段结构可能稍有差异，桥接器（如 `radar_gz_bridge`）会把 `gz.msgs.Float_V` 映射到 `RadarSector` 的实际字段。请以你构建的 `marine_sensor_msgs/msg/RadarSector.msg` 为准并在桥接器配置中保持一致。
