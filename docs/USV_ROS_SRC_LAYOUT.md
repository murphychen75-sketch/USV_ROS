# USV_ROS 工作区源码结构（`src/` 以下）

**说明**：本仓库根目录为 **USV_ROS**（ROS 2 colcon 工作区）。源码集中在 **`src/`** 下；不存在名为 `usv_ros` 的单独顶层目录，本文自 **`src/`** 向下归纳目录与 ROS 包边界。

**生成目的**：快速对照「域 → 包 → 典型内容」。团队协作、分支、PR 与 `usv_simulation` 可选 submodule 策略见  
[`docs/GIT_WORKFLOW.md`](GIT_WORKFLOW.md)；详细仿真编排另见  
[`src/usv_simulation/docs/docs_v3/仿真仓库结构说明.md`](../src/usv_simulation/docs/docs_v3/仿真仓库结构说明.md)。

---

## 1. `src/` 顶层一览

| 目录 | 角色 |
|------|------|
| **`usv_interfaces`** | 全工程统一消息 / 服务 / 动作与 topic 常量（C++/Python） |
| **`usv_simulation`** | 可选仿真平台（submodule）：Gazebo、VRX、传感器插件、`usv_sim_full` 主入口、文档与 Docker 说明等 |
| **`usv_comm`** | 通信桥：MAVLink、MQTT 等 |
| **`usv_perception`** | 感知相关驱动与 AIS 子工程 |
| **`usv_monitor`** | 监控相关节点与 launch |
| **`usv_fusion`** | 融合相关子工程（含大型 `bev/`） |

---

## 2. `usv_interfaces`

```
usv_interfaces/
├── CMakeLists.txt
├── package.xml
├── msg/
├── srv/
├── action/
├── include/usv_interfaces/     # C++ 头文件（如 topics.hpp）
└── usv_interfaces/             # Python 模块（如 topics.py）
```

**职责**：跨包共享的接口定义；改 `.msg` / `.srv` 须同步 `CMakeLists.txt` 与下游引用。

---

## 3. `usv_comm`

```
usv_comm/
├── usv_mavlink_bridge/         # MAVROS / MAVLink 桥接（launch、config、节点）
│   ├── config/
│   ├── docs/
│   ├── launch/
│   └── usv_mavlink_bridge/
└── usv_mqtt_bridge/            # MQTT ↔ ROS 2
    ├── config/
    ├── docs/
    ├── launch/
    ├── scripts/
    └── usv_mqtt_bridge/
```

---

## 4. `usv_monitor`

```
usv_monitor/
├── config/
├── launch/
├── resource/
└── usv_monitor/
```

---

## 5. `usv_simulation`（可选仿真环境，子目录多）

```
usv_simulation/
├── docker/                     # 容器说明与 Dockerfile 等
├── docs/                       # docs_v1 / v2 / v3（QUICK_START、架构说明等）
├── notes/
├── ground_truth_sim/           # 场景真值、Gazebo 跟随等 ROS 包
├── env_panel/                  # 环境面板相关 C++ 包
├── sim_test/                   # 仿真调试与实验用工具包（Python 等）
├── usv_sim_full/               # **整机仿真编排入口包**（launch、config、URDF、session_manager）
├── sensor_plugins/
│   ├── gz_maritime_radar_plugin/
│   ├── radar_gz_bridge/
│   ├── gy_radar_driver-main/
│   └── usv_mmwave_sim/
├── third_party/
│   ├── marine_msgs/            # marine_acoustic_msgs / marine_sensor_msgs
│   └── foxglove-sdk/
└── vrx/                        # VRX 竞赛相关：vrx_gz、vrx_ros、wamv_*、vrx_gazebo 等
```

**要点**：

- 仿真「怎么跑、怎么配」以 **`usv_sim_full`** 与 **`docs/docs_v3/QUICK_START.md`** 为准。
- **`vrx/`** 内为多条独立 ROS 包（`vrx_gz`、`wamv_description` 等），通常随仿真依赖一并构建。
- **`sensor_plugins/`** 下各目录多为独立包（各自 `package.xml`）。
- `usv_simulation` 不属于实船运行必要依赖；已作为 submodule 指向 `murphychen75-sketch/USV_Simulation`，非仿真开发者可不初始化该目录。

---

## 6. `usv_perception`

```
usv_perception/
├── mmwave_radar/               # 毫米波雷达驱动与解析节点
└── ROS_AIS_ws-main/            # AIS 子工作区式目录
    ├── bag_files/
    └── src/
        ├── ais_interfaces/
        ├── ais_launch/
        ├── ais_nodes/
        └── ais_reports_interfaces/
```

**要点**：

- **`ROS_AIS_ws-main/src/*`** 为独立接口与节点包；与主栈 **`usv_interfaces`** 区分，集成时注意话题与依赖边界。
- `mmwave_radar/` 目录名与包名可能不一致，构建时以 `package.xml` 中的包名为准。

---

## 7. `usv_fusion`

```
usv_fusion/
└── bev/                        # BEV 融合相关（含 mmdetection3d、bevfusion 等大体积子树）
```

**要点**：

- **`bev/`** 体量极大，通常不作为实船最小构建集或仿真最小构建集；按需单独编译或排除。

---

## 8. ROS 2 包清单（`src/` 内 `package.xml`）

下列包可直接用于 `colcon build --packages-select <name>`（路径相对 `src/`）：

| 包名 | 路径 |
|------|------|
| `usv_interfaces` | `usv_interfaces/` |
| `usv_mavlink_bridge` | `usv_comm/usv_mavlink_bridge/` |
| `usv_mqtt_bridge` | `usv_comm/usv_mqtt_bridge/` |
| `usv_monitor` | `usv_monitor/` |
| `ground_truth_sim` | `usv_simulation/ground_truth_sim/` |
| `usv_sim_full` | `usv_simulation/usv_sim_full/` |
| `sim_test` | `usv_simulation/sim_test/` |
| `usv_mmwave_sim` | `usv_simulation/sensor_plugins/usv_mmwave_sim/` |
| `radar_gz_bridge` | `usv_simulation/sensor_plugins/radar_gz_bridge/` |
| `gz_maritime_radar_plugin` | `usv_simulation/sensor_plugins/gz_maritime_radar_plugin/` |
| `gy_radar_driver` | `usv_simulation/sensor_plugins/gy_radar_driver-main/` |
| `env_panel` | `usv_simulation/env_panel/` |
| `marine_sensor_msgs` | `usv_simulation/third_party/marine_msgs/marine_sensor_msgs/` |
| `marine_acoustic_msgs` | `usv_simulation/third_party/marine_msgs/marine_acoustic_msgs/` |
| `vrx_ros` | `usv_simulation/vrx/vrx_ros/` |
| `vrx_gz` | `usv_simulation/vrx/vrx_gz/` |
| `wamv_description` | `usv_simulation/vrx/vrx_urdf/wamv_description/` |
| `wamv_gazebo` | `usv_simulation/vrx/vrx_urdf/wamv_gazebo/` |
| `vrx_gazebo` | `usv_simulation/vrx/vrx_urdf/vrx_gazebo/` |
| `ais_interfaces` | `usv_perception/ROS_AIS_ws-main/src/ais_interfaces/` |
| `ais_launch` | `usv_perception/ROS_AIS_ws-main/src/ais_launch/` |
| `ais_nodes` | `usv_perception/ROS_AIS_ws-main/src/ais_nodes/` |
| `ais_reports_interfaces` | `usv_perception/ROS_AIS_ws-main/src/ais_reports_interfaces/` |

> **`usv_fusion/bev/`**：内含大型第三方子树（如 `mmdetection3d`、`bevfusion`），是否作为独立 ROS 包构建取决于子目录是否含 `package.xml`；通常不作为仿真最小集。

---

## 9. 维护说明

- 增删包或迁移目录后，请同步更新本文件中的 **树形片段** 与 **§8 表格**。
- 仿真目录深度展开易与 git 子模块/大量资源冲突，本文只保留 **稳定层级**；需要文件级清单可用：  
  `find src -maxdepth 4 -type d | sort`

---

*文档路径：`docs/USV_ROS_SRC_LAYOUT.md`（相对仓库根 USV_ROS）。*
