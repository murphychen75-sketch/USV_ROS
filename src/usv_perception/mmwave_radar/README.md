# mmwave_radar

## 功能概述

`mmwave_radar` 用于接入毫米波雷达驱动并对外提供 ROS2 话题输出，当前核心功能包为 `mmw_radar`。

主要功能：

- 通过 UDP 组播接收雷达原始报文并解析点云、目标列表数据。
- 发布感知结果话题（点云、目标列表、目标框）供下游融合/显示模块使用。
- 订阅 `Odometry`、`TwistStamped`、`Imu`，生成 `0xAA31` 注入包并通过 UDP 单播回传雷达。
- 支持通过 YAML 参数文件配置网络端点、话题名称、坐标系和端口范围。

说明：该功能包负责协议解析与桥接，不负责目标检测/跟踪算法计算。

## 目录结构

```text
mmwave_radar/
├── src/
│   └── ra223f_pkg/          # ROS2 包（包名：mmw_radar）
│       ├── src/
│       │   ├── ra223f_node.cpp
│       │   └── udp_interface.*
│       ├── launch/launch.py
│       ├── config/mmw_radar_params.yaml
│       ├── CMakeLists.txt
│       ├── package.xml
│       └── README.md
├── 原版_使用说明.md
└── README.md
```

## 输入输出接口

- 输入话题：
  - `odom_topic` -> `nav_msgs/msg/Odometry`
  - `vehicle_speed_topic` -> `geometry_msgs/msg/TwistStamped`
  - `imu_topic` -> `sensor_msgs/msg/Imu`

- 输出话题（默认）：
  - `/mmw_radar/pointcloud_topic` -> `sensor_msgs/msg/PointCloud2`
  - `/mmw_radar/objectList_topic` -> `sensor_msgs/msg/PointCloud2`
  - `/mmw_radar/object_marker` -> `visualization_msgs/msg/MarkerArray`

## 参数配置

默认参数文件：`src/ra223f_pkg/config/mmw_radar_params.yaml`

重点参数：

- 网络参数：`multicast_ip`、`multicast_port`、`unicast_ip`、`unicast_port`、`multicast_interface_ip`
- 输入源参数：`odom_topic`、`vehicle_speed_topic`、`imu_topic`
- 输出参数：`pointcloud_topic`、`object_topic`、`object_marker_topic`、`frame_id`
- 运行参数：`run_mode`、`local_port_start`、`local_port_end`

## 构建与运行

在工作区根目录执行：

```bash
colcon build --packages-select mmw_radar --symlink-install
source install/setup.bash
ros2 launch mmw_radar launch.py
```

使用自定义参数文件：

```bash
ros2 launch mmw_radar launch.py params_file:=/absolute/path/to/mmw_radar_params.yaml
```

## 快速检查

```bash
ros2 param list /mmw_radar_node
ros2 topic list | rg mmw_radar
```

## 备注

- 旧 `launch_pkg` 已并入 `mmw_radar`，请统一使用 `ros2 launch mmw_radar launch.py`。
- 若为多网卡环境，建议显式设置 `multicast_interface_ip`，避免组播收包失败。
