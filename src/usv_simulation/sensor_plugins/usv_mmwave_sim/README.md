# usv_mmwave_sim（毫米波仿真一体化）

> **与 `usv_sim_full` 主仿真**  
> 整机毫米波主链路：**URDF `gpu_ray`** → **`ros_gz_bridge`**（`…/points_gz`）→ 本包 **`mmwave_4d_cloud_node`** 发布最终 **`…/points`**（`x,y,z,doppler_velocity,rcs`）。  
> 同包内 **`FourDRadarPlugin`**（`libusv_4d_radar_plugin.so`，注册名 `usv_4d_radar_gz::FourDRadarPlugin`）用于 **独立验证 world / 对照**；新集成主链路请走 `sensor_config.yaml` + `main.launch.py`。详见 `docs/INTEGRATION_GUIDE_CN.md`。

面向 **USV 感知融合** 的 **Gazebo Sim（gz-sim）** 4D 毫米波雷达插件及配套资源。在 **ROS 2 + colcon** 工作空间中作为独立功能包使用，可与 **整体仿真系统**（统一 launch、自定义 world/URDF）合并部署：本包提供 **传感器插件库**、**可选验证场景** 与 **ROS 2 点云接口**；上层系统负责整机 world、机器人描述、导航与其它传感器，只需按本文 **集成说明** 挂载插件并配置环境变量。

> 跨项目挂载实操请见：`docs/INTEGRATION_GUIDE_CN.md`

- **License:** Apache-2.0  
- **ROS 2:** 以 `rclcpp` 发布 `sensor_msgs/PointCloud2`  
- **仿真后端:** Gazebo Sim 8、`gz-plugin2`、`gz-math7`（版本需与系统安装的 Gazebo 发行版一致）

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 4D 点云 | 字段 `x, y, z, doppler_velocity, rcs`；角向分辨率决定射线网格，**无命中则无点**（可与海杂波二选一占格） |
| 自车过滤 | 忽略与雷达所属 **同一顶层 model** 的碰撞体，避免自船体被误检为密集目标 |
| 感知与误差模型 | 感知距离上限、`min/max_range`；可选距离/方位测量误差（高斯，可开关） |
| 海杂波（可选） | 按角向格点概率占格，与几何回波互斥 |
| 验证资源 | `minimal` / `stable` 示例 world、RViz 配置、`minimal` launch 内含 TF 与参考 Marker |

---

## 依赖

**构建:** `ament_cmake`、`rclcpp`、`sensor_msgs`、`std_msgs`、`gz-cmake3`、`gz-plugin2`、`gz-sim8`、`gz-math7`  

**运行（launch 与 RViz 辅助）:** `tf2_ros`、`launch_ros`、`rclpy`、`visualization_msgs`、`geometry_msgs`  

请与 **整体仿真栈** 使用相同的 ROS 2 发行版与 Gazebo Sim 大版本，避免插件 ABI 不匹配。

---

## 与整体仿真系统合并

1. **放入同一 colcon 工作空间**  
   将本仓库置于工作空间 `src/` 下（或作为子模块 / 子目录），与其它仿真、控制、描述包一并 `colcon build`。

2. **让 gz-sim 加载插件**  
   启动仿真前必须将本包安装前缀下的 `lib` 加入 `GZ_SIM_SYSTEM_PLUGIN_PATH`，例如：
   ```bash
   export GZ_SIM_SYSTEM_PLUGIN_PATH=<ws>/install/usv_mmwave_sim/lib:$GZ_SIM_SYSTEM_PLUGIN_PATH
   ```
   **推荐**在 **顶层 launch** 中用 `SetEnvironmentVariable` 设置，保证与整机仿真一次启动即可加载；勿依赖个人绝对路径。

3. **世界与机器人**  
   - **使用自有 world：** 在对应 SDF 模型的雷达 link 上挂载与本包一致的 `<plugin filename="libusv_4d_radar_plugin.so" ...>`（参数见下文）。  
   - **使用自有 URDF/xacro：** 用 `<gazebo reference="雷达 link">` 注入相同插件块。  
   - 本包自带的 `worlds/*.sdf` 仅作 **单机验证** 参考，合并后通常由系统仓库提供主 world。

4. **ROS 2 接口约定**  
   - 默认点云话题在示例中为 `/radar/points_4d`，可在 SDF/URDF 的 `<topic>` 中修改；合并时建议与 **系统命名空间 / remap** 统一（例如在顶层 launch 中 `remappings`）。  
   - 点云 `frame_id` 需与 **系统 TF** 一致；若整栈以 `map`/`odom` 为根，请自行发布相应静态或动态 TF，**不要**假设仅依赖本包示例里的 `map`→`world`。

5. **可选验证节点**  
   `minimal_4d_radar_validation.launch.py` 会启动 `validation_world_markers`（`/radar/validation_models`），几何与 **minimal 专用** SDF 对齐。合并到大地图仿真时一般 **不启动** 该节点，或由系统侧提供统一可视化。

---

## 编译与安装

```bash
cd <ws>   # 你的 colcon 工作空间根目录
colcon build --packages-select usv_mmwave_sim
source install/setup.bash
```

安装路径提示：

- 插件：`<ws>/install/usv_mmwave_sim/lib/libusv_4d_radar_plugin.so`（另有 `libusv_reciprocating_targets_plugin.so` 供 stable 场景）  
- 节点：`mmwave_4d_cloud_node` 安装于 `lib/usv_mmwave_sim/`  
- 共享资源：`<ws>/install/usv_mmwave_sim/share/usv_mmwave_sim/{worlds,rviz,launch}/`

---

## ROS 2 发布话题（本包节点）

| 话题 | 类型 | 来源 |
|------|------|------|
| 可配置，示例为 `/radar/points_4d` | `sensor_msgs/msg/PointCloud2` | `FourDRadarPlugin`（由 SDF/URDF `<topic>` 指定） |
| `/radar/validation_models` | `visualization_msgs/msg/MarkerArray` | `validation_world_markers`（**仅** `minimal` launch） |

**Launch 附带：** `static_transform_publisher` 发布 `map` → `world`（单位变换），供 **本包示例 RViz** 使用；合并到整机时若不再使用该 RViz 配置，可由系统 TF 替代。

自检：

```bash
source <ws>/install/setup.bash
ros2 topic list | grep -E '^/radar|^/tf_static'
```

---

## 单机快速验证（可选）

在已 `source` 工作空间且已设置 `GZ_SIM_SYSTEM_PLUGIN_PATH` 的前提下：

```bash
ros2 launch usv_mmwave_sim minimal_4d_radar_validation.launch.py
```

或仅开 Gazebo（需自行 export 插件路径）：

```bash
gz sim -r $(ros2 pkg prefix usv_mmwave_sim)/share/usv_mmwave_sim/worlds/minimal_4d_radar_validation.sdf
```

**稳定场景**（低动态、往复目标插件、零重力等）：

```bash
ros2 launch usv_mmwave_sim stable_4d_radar_validation.launch.py
```

---

## 包内目录结构

```
usv_mmwave_sim/
├── CMakeLists.txt
├── package.xml
├── scripts/validation_world_markers.py   # 安装为 lib/.../validation_world_markers
├── include/usv_4d_radar_gz/4d_radar_plugin.hpp   # 插件头路径（与注册命名空间一致）
├── src/
│   ├── 4d_radar_plugin.cpp
│   ├── reciprocating_targets_plugin.cpp
│   └── mmwave_4d_cloud_node.cpp
├── worlds/
│   ├── minimal_4d_radar_validation.sdf
│   └── stable_4d_radar_validation.sdf
├── launch/
│   ├── minimal_4d_radar_validation.launch.py
│   └── stable_4d_radar_validation.launch.py
└── rviz/4d_radar_minimal.rviz
```

---

## 在 URDF / xacro 中挂载插件

插件注册名：`usv_4d_radar_gz::FourDRadarPlugin`，库文件名：`libusv_4d_radar_plugin.so`。  
将 `<gazebo reference="雷达 link">` 置于 **真实雷达安装 link**，保证射线原点与朝向正确；`ego_link_name` 一般填底盘 `base_link` 用于多普勒补偿。

示例（参数可按系统标定修改）：

```xml
<gazebo reference="radar_front_link">
  <plugin filename="libusv_4d_radar_plugin.so" name="usv_4d_radar_gz::FourDRadarPlugin">
    <topic>/radar/points_4d</topic>
    <frame_id>radar_front_link</frame_id>
    <ego_link_name>base_link</ego_link_name>
    <horizontal_fov_deg>100.0</horizontal_fov_deg>
    <vertical_fov_deg>30.0</vertical_fov_deg>
    <azimuth_resolution_deg>1.0</azimuth_resolution_deg>
    <elevation_resolution_deg>1.0</elevation_resolution_deg>
    <min_range>0.8</min_range>
    <max_range>120.0</max_range>
    <update_rate_hz>10.0</update_rate_hz>
    <base_rcs>12.0</base_rcs>
    <rcs_distance_decay>0.01</rcs_distance_decay>
    <enable_sea_clutter>false</enable_sea_clutter>
    <sea_clutter_probability>0.0</sea_clutter_probability>
    <sea_clutter_amplitude>0.0</sea_clutter_amplitude>
    <perception_range_limit_m>300.0</perception_range_limit_m>
    <enable_range_measurement_error>false</enable_range_measurement_error>
    <enable_azimuth_measurement_error>false</enable_azimuth_measurement_error>
    <range_error_at_reference_m>0.66</range_error_at_reference_m>
    <range_error_reference_m>300.0</range_error_reference_m>
    <azimuth_error_std_deg>0.5</azimuth_error_std_deg>
  </plugin>
</gazebo>
```

### 插件参数表

| 标签 | 含义 |
|------|------|
| `topic` | PointCloud2 话题名 |
| `frame_id` | 点云 `header.frame_id`（与 TF 一致） |
| `ego_link_name` | 读取线/角速度用于多普勒补偿的 link |
| `horizontal_fov_deg` / `vertical_fov_deg` | 水平 / 垂直视场（°） |
| `azimuth_resolution_deg` / `elevation_resolution_deg` | 方位 / 俯仰分辨率（°）；射线数 ≈ floor(视场/分辨率) |
| `min_range` / `max_range` | 距离门（m） |
| `update_rate_hz` | 发布频率（Hz） |
| `base_rcs` / `rcs_distance_decay` | RCS 经验参数 |
| `enable_sea_clutter` 等 | 海杂波开关与强度 |
| `perception_range_limit_m` | 感知上限（m）；有效最大距离 = `min(max_range, 本值)` |
| `enable_range_measurement_error` | 距离测量误差开关 |
| `enable_azimuth_measurement_error` | 方位测量误差开关 |
| `range_error_at_reference_m` | 参考距离处距离噪声 1σ（m） |
| `range_error_reference_m` | 距离误差缩放参考距离（m） |
| `azimuth_error_std_deg` | 方位噪声 1σ（°） |

示例 SDF 将插件写在 `<model>` 下时，需保证与 `base_link` 位姿关系正确；**通用机器人务必用 `reference` 指向雷达 link**。

---

## 示例场景说明（参考）

- **minimal：** 静态自车、三艘静态金属目标（名称含 `metal` 以利 RCS）、默认关闭海杂波；launch 含 RViz、`map`→`world`、参考 Marker。  
- **stable：** 静态自车、零重力、往复目标插件、无参考 Marker；用于可重复性基线测试。

**行为摘要：** 多普勒含自运动补偿 \(v_\text{sensor} = v_\text{ego} + \omega_\text{ego} \times r_\text{sensor}\)。海杂波按格点占坑，与几何回波互斥。  
**RViz：** `4d_radar_minimal.rviz` 中点云以 **`rcs`** 做 **Intensity** 着色（彩虹表示相对强弱）；对比度不够时可关 Autocompute 并手设 Min/Max。

---

## 常见问题

1. **点云在 RViz 不可见：** 查 TF（`frame_id` 到 Fixed Frame）、话题是否有数据、QoS（示例为 Best Effort）。  
2. **gz 报找不到插件：** 检查 `GZ_SIM_SYSTEM_PLUGIN_PATH` 是否包含 `install/usv_mmwave_sim/lib`。  
3. **合并后话题冲突：** 使用命名空间或 launch `remappings` 统一约定。

---

## 维护与版本

版本与维护者见 `package.xml`。提交合并请求或对接整机仿真时，请同步更新 **依赖版本** 与 **顶层 launch 中的插件路径** 说明。
