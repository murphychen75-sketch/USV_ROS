# mmwave_radar

## 功能概述

`mmwave_radar` 目录即 ROS2 包 **`mmw_radar`**（ament_cmake），用于接入毫米波雷达驱动并对外提供话题输出。

主要功能：

- 通过 UDP 组播接收雷达原始报文并解析点云、目标列表数据。
- 发布感知结果话题（点云、目标列表、目标框）供下游融合/显示模块使用。
- 订阅 `Odometry`、`TwistStamped`、`Imu`，生成 `0xAA31` 注入包并通过 UDP 单播回传雷达。
- 支持通过 YAML 参数文件配置网络端点、话题名称、坐标系和端口范围。

说明：该功能包负责协议解析与桥接，不负责目标检测/跟踪算法计算。

## 目录结构

```text
mmwave_radar/                 # 目录名；ROS 包名 mmw_radar（见 package.xml）
├── package.xml
├── CMakeLists.txt
├── src/
│   ├── ra223f_node.cpp
│   └── udp_interface.*
├── launch/
│   ├── launch.py
│   └── sim_publish.launch.py
├── config/
│   ├── mmw_radar_params.yaml
│   └── mmw_radar_sim_params.yaml
├── scripts/
│   └── mmw_radar_sim_publisher.py
├── 原版_使用说明.md
└── README.md
```

## 输入输出接口

- 输入话题：
  - `odom_topic` -> `nav_msgs/msg/Odometry`
  - `vehicle_speed_topic` -> `geometry_msgs/msg/TwistStamped`
  - `imu_topic` -> `sensor_msgs/msg/Imu`

- 输出话题（默认，方案 A，见 `mmw_radar_params.yaml`）：
  - `raw_pointcloud_topic` -> `/mmw_radar/raw_pointcloud_topic`（`sensor_msgs/msg/PointCloud2`，完整点云）
  - `raw_object_topic` -> `/mmw_radar/raw_objectList_topic`（`sensor_msgs/msg/PointCloud2`，完整目标列表）
  - `target_array_topic` -> `/perception/radar/mmw/objects`（`usv_interfaces/msg/MmwaveTargetArray`）
  - `object_marker_topic` -> `/mmw_radar/object_marker`（`visualization_msgs/msg/MarkerArray`）

## 输出话题字段说明

两个话题均使用 `sensor_msgs/msg/PointCloud2` 承载数据：**每个检测点/每个目标对应一行点**（`height=1`，`width=点数/目标数`）。  
`header.frame_id` 由参数 `frame_id` 指定（默认 `mmw_radar`）；`header.stamp` 来自雷达报文内 PTP 时间（点云帧头解析后，目标列表复用同一时间戳）。

坐标系约定（与驱动源码一致）：

- **点云**：由球坐标（`range` + `azimuth_deg` + `elevation_deg`）换算到雷达坐标系笛卡尔坐标。
- **目标**：雷达 VCS（车体/雷达坐标系），`x` 为纵向、`y` 为横向、`z` 为垂直；`heading_angle` 为航向角，**左正右负**（度）。

### `raw_pointcloud_topic`（`/mmw_radar/raw_pointcloud_topic`）

| 字段名 | 类型 | 单位 | 含义 |
| --- | --- | --- | --- |
| `x` | float32 | m | 笛卡尔 X，由 `range`、方位角、俯仰角换算：`range·cos(elev)·cos(azim)` |
| `y` | float32 | m | 笛卡尔 Y：`range·cos(elev)·sin(azim)` |
| `z` | float32 | m | 笛卡尔 Z：`range·sin(elev)` |
| `range` | float32 | m | 径向距离（协议原始量 ×0.01） |
| `amb_rangerate` | float32 | m/s | 模糊径向速度（多普勒模糊未完全解开时的速度估计） |
| `unamb_rangerate` | float32 | m/s | 非模糊径向速度（解模糊后的径向速度，下游优先使用） |
| `rangerate` | float32 | m/s | 与 `unamb_rangerate` 相同，保留用于兼容旧消费端 |
| `azimuth_deg` | float32 | deg | 方位角（协议 ×0.01） |
| `elevation_deg` | float32 | deg | 俯仰角（协议 ×0.01） |
| `snr` | float32 | — | 距离-多普勒（RD）域信噪比（协议 ×0.01，无量纲比值类指标） |
| `rcs` | float32 | — | 雷达散射截面相关量（协议 ×0.0039，反映目标反射强度） |
| `confidence` | float32 | — | 点置信度（协议 ×0.01，0~1 量级） |
| `unamb_rangeratemask` | float32 | 枚举码 | 速度解模糊状态（协议 uint8，以 float 发布）：`0` 成功，`1` 不确定，`2` 失败 |
| `snr_azi` | float32 | — | 方位维信噪比（协议 ×0.01） |

布局：`point_step = 56` 字节（14×float32）。一帧内点数由雷达 `0xAA80` 帧头中的 `pointcloud_num` 决定。

### `raw_object_topic`（`/mmw_radar/raw_objectList_topic`）

雷达端已完成目标检测/跟踪，本话题为 **航迹列表**（协议 `0xAA90` + `0xAA91`），非本节点从点云二次计算。每个目标一行点。

| 字段名 | 类型 | 单位 | 含义 |
| --- | --- | --- | --- |
| `x` | float32 | m | 目标中心纵向位置（VCS，协议 ×0.01） |
| `y` | float32 | m | 目标中心横向位置（VCS，协议 ×0.01） |
| `z` | float32 | m | 目标中心垂直位置（VCS，协议 ×0.01） |
| `width` | float32 | m | 包围盒宽度（横向尺寸，协议 ×0.01） |
| `length` | float32 | m | 包围盒长度（纵向尺寸，协议 ×0.01） |
| `height` | float32 | m | 包围盒高度（垂直尺寸，协议 ×0.01） |
| `xvel_abs` | float32 | m/s | 纵向绝对速度（协议 ×0.01） |
| `yvel_abs` | float32 | m/s | 横向绝对速度（协议 ×0.01） |
| `xacc_abs` | float32 | m/s² | 纵向绝对加速度（协议 ×0.01） |
| `yacc_abs` | float32 | m/s² | 横向绝对加速度（协议 ×0.01） |
| `heading_angle` | float32 | deg | 航向角，左正右负（协议 ×0.01） |
| `classify_type` | float32 | 枚举码 | 目标分类（协议 uint8，以 float 发布）：`0` 未知，`1` 行人，`2` 自行车，`3` 小汽车，`4` 大卡车 |
| `classify_prob` | float32 | — | 分类置信度/概率（协议 uint8 原值，未额外缩放） |
| `objmotion_status` | float32 | 枚举码 | 动静状态（协议 uint16，以 float 发布）：`0` 静止，`1` 运动 |
| `obstacle_prob` | float32 | — | 障碍物概率（协议 uint16 原值） |
| `track_id` | float32 | — | 航迹 ID（协议 uint8，以 float 发布，同一 ID 表示同一跟踪目标） |

布局：`point_step = 64` 字节（16×float32）。目标个数由雷达 `0xAA90` 帧头中的 `object_num` 决定。

### `target_array_topic`（`/perception/radar/mmw/objects`）

`usv_interfaces/msg/MmwaveTargetArray`，由 `raw_object` 同源数据映射，字段见下文「`raw_object` ↔ `MmwaveTarget`」表。与 `raw_object_topic` 同帧发布。

### 与 `object_marker` 的关系

`/mmw_radar/object_marker` 为 `visualization_msgs/msg/MarkerArray`，与 `raw_object_topic` 同帧发布。下游目标消费请使用 `target_array_topic`；需要协议全字段时请使用 `raw_object_topic`。

### 读取示例（Python）

```python
from sensor_msgs_py import point_cloud2

for p in point_cloud2.read_points(msg, field_names=("x", "y", "range", "unamb_rangerate"), skip_nans=True):
    x, y, rng, v_radial = p
```

## 与 `usv_interfaces` 映射表（已实现）

原始数据走 `raw_*` 的 `PointCloud2`；系统目标走 `target_array_topic` 的 `MmwaveTargetArray`（`TOPIC_PERCEPTION_MMW`）。

### 话题映射（方案 A）

| 参数 | 默认话题 | 消息类型 |
| --- | --- | --- |
| `raw_pointcloud_topic` | `/mmw_radar/raw_pointcloud_topic` | `sensor_msgs/PointCloud2` |
| `raw_object_topic` | `/mmw_radar/raw_objectList_topic` | `sensor_msgs/PointCloud2` |
| `target_array_topic` | `/perception/radar/mmw/objects` | `usv_interfaces/MmwaveTargetArray` |
| `object_marker_topic` | `/mmw_radar/object_marker` | `visualization_msgs/MarkerArray` |

迁移：原 `/mmw_radar/objectList_topic`（PointCloud2）→ `raw_object_topic`；业务目标 → `target_array_topic`。

### `raw_object` ↔ `MmwaveTarget` 字段映射

| `raw_object` 字段 | `MmwaveTarget` 字段 | 对齐状态 |
| --- | --- | --- |
| `x` | `x` | 已覆盖 |
| `y` | `y` | 已覆盖 |
| `xvel_abs` | `v_x` | 已覆盖 |
| `yvel_abs` | `v_y` | 已覆盖 |
| `width` | `size_w` | 已覆盖 |
| `length` | `size_l` | 已覆盖 |
| `height` | `size_h` | 已覆盖 |
| `objmotion_status` | `objmotion_status` | 已覆盖（0 静止 / 1 运动） |
| `track_id` | `track_id` | 已覆盖 |
| `z`、`xacc_abs`、`yacc_abs`、`heading_angle`、`classify_*`、`obstacle_prob` | — | 仅保留在 `raw_object` PointCloud2 |

枚举参考（驱动侧，写入接口时建议改为整型字段）：

| 驱动字段 | 取值 | 含义 |
| --- | --- | --- |
| `classify_type` | 0 | 未知 |
| | 1 | 行人 |
| | 2 | 自行车 |
| | 3 | 小汽车 |
| | 4 | 大卡车 |
| `objmotion_status` | 0 | 静止 |
| | 1 | 运动 |

### 点云字段

点云仅在 `raw_pointcloud_topic` 发布，`snr` 等字段不进入 `MmwaveTarget`（接口侧已删除 `snr`）。

## 参数配置

默认参数文件：`config/mmw_radar_params.yaml`

重点参数：

- 网络参数：`multicast_ip`、`multicast_port`、`unicast_ip`、`unicast_port`、`multicast_interface_ip`
- 输入源参数：`odom_topic`、`vehicle_speed_topic`、`imu_topic`
- 输出参数：`raw_pointcloud_topic`、`raw_object_topic`、`target_array_topic`、`object_marker_topic`、`frame_id`
- 运行参数：`run_mode`、`local_port_start`、`local_port_end`

## 构建与运行

在工作区根目录执行：

```bash
# mmw_radar 依赖 usv_interfaces（MmwaveTarget 等），须先编接口包或一并编译
colcon build --packages-select usv_interfaces mmw_radar --symlink-install
# 等价：colcon build --packages-up-to mmw_radar --symlink-install
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
ros2 topic list | rg -e 'mmw_radar|perception/radar/mmw'
ros2 topic echo /perception/radar/mmw/objects --once
```

无雷达联调（独立仿真脚本，默认 **15Hz**）：

```bash
ros2 launch mmw_radar sim_publish.launch.py
# 或
ros2 run mmw_radar mmw_radar_sim_publisher.py --ros-args \
  --params-file $(ros2 pkg prefix mmw_radar)/share/mmw_radar/config/mmw_radar_sim_params.yaml
```

参数文件：`config/mmw_radar_sim_params.yaml`（`publish_rate_hz: 15.0`）。

## 备注

- 旧 `launch_pkg` 已并入 `mmw_radar`，请统一使用 `ros2 launch mmw_radar launch.py`。
- 若为多网卡环境，建议显式设置 `multicast_interface_ip`，避免组播收包失败。
