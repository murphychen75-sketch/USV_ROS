# usv_mmwave_sim 跨仿真环境挂载指南（含 FourDRadarPlugin）

## 0. 推荐路径（本仓库 `usv_sim_full` 整机仿真）

毫米波在 **主仿真** 中已 **不依赖** 本文下文所述的 `FourDRadarPlugin` + `GZ_SIM_SYSTEM_PLUGIN_PATH` 流程，改为：

1. `full_config.yaml` 中配置 `type: mmwave_radar` 与 `override_topic: /sensors/mmwave/{name}/points`（不含船名前缀，规则与激光一致）。  
2. `sensor_macros.xacro` 使用 **`gpu_ray`**，`session_manager` 生成 **`ros_gz_bridge`**：`gz …/points` → ROS **`/{robot}/…/points_gz`**。  
3. `main.launch.py` 在配置含毫米波传感器时自动启动 **`usv_mmwave_sim::mmwave_4d_cloud_node`**，订阅 `points_gz`，发布最终 **`/{robot}/…/points`**（五字段点云）。  
4. 海杂波、测距/方位误差、多普勒与简化 RCS 由 **`sensor_config.yaml` → `mmwave.default`** 驱动节点参数；**按实体 material 的 RCS 缩放** 在纯 ROS 侧未复现。

**本节为默认集成方式。** 若你维护 **独立 SDF/URDF** 且仍要内嵌 `libusv_4d_radar_plugin.so`，可继续阅读下文（legacy）。

---

本文给出将本包内 **`FourDRadarPlugin`**（库 `libusv_4d_radar_plugin.so`）挂载到其它 Gazebo Sim / ROS 2 仿真环境的标准步骤与排障方法（**legacy / 验证场景**）。

## 1. 前置条件

- 目标环境使用 **Gazebo Sim（gz-sim）**，且大版本与本包编译依赖一致（当前为 `gz-sim8`）。
- 工作空间可正常 `colcon build`。
- 你有可编辑的机器人模型（SDF 或 URDF/xacro）与顶层 launch。

## 2. 合并到工作空间

```bash
cd <ws>/src
# 拷贝/子模块引入本包（路径按你的仓库布局调整）
cd <ws>
colcon build --packages-select usv_mmwave_sim
source install/setup.bash
```

## 3. 配置插件搜索路径（必须）

Gazebo 通过 `GZ_SIM_SYSTEM_PLUGIN_PATH` 查找 `libusv_4d_radar_plugin.so`：

```bash
export GZ_SIM_SYSTEM_PLUGIN_PATH=<ws>/install/usv_mmwave_sim/lib:$GZ_SIM_SYSTEM_PLUGIN_PATH
```

建议在你的**顶层 launch**中统一设置，避免每次手工 export。

## 4. 在模型中挂载插件

### 4.1 SDF 场景（推荐）

将插件放在 `<model>` 下，避免放在 `<link>` 下触发 SDF warning。

```xml
<model name="your_vehicle">
  <!-- 已有 base_link 与 radar_link -->
  <plugin filename="libusv_4d_radar_plugin.so" name="usv_4d_radar_gz::FourDRadarPlugin">
    <topic>/radar/points_4d</topic>
    <frame_id>radar_link</frame_id>
    <sensor_link_name>radar_link</sensor_link_name>
    <ego_link_name>base_link</ego_link_name>
    <output_in_sensor_frame>true</output_in_sensor_frame>

    <horizontal_fov_deg>100.0</horizontal_fov_deg>
    <vertical_fov_deg>30.0</vertical_fov_deg>
    <azimuth_resolution_deg>1.0</azimuth_resolution_deg>
    <elevation_resolution_deg>1.0</elevation_resolution_deg>

    <min_range>0.8</min_range>
    <max_range>120.0</max_range>
    <perception_range_limit_m>300.0</perception_range_limit_m>
    <update_rate_hz>10.0</update_rate_hz>

    <base_rcs>12.0</base_rcs>
    <rcs_distance_decay>0.01</rcs_distance_decay>

    <enable_sea_clutter>false</enable_sea_clutter>
    <sea_clutter_probability>0.0</sea_clutter_probability>
    <sea_clutter_amplitude>0.0</sea_clutter_amplitude>

    <enable_range_measurement_error>false</enable_range_measurement_error>
    <enable_azimuth_measurement_error>false</enable_azimuth_measurement_error>
    <range_error_at_reference_m>0.66</range_error_at_reference_m>
    <range_error_reference_m>300.0</range_error_reference_m>
    <azimuth_error_std_deg>0.5</azimuth_error_std_deg>
  </plugin>
</model>
```

### 4.2 URDF/xacro

通过 `<gazebo reference="radar_link">` 或模型级插件注入，核心参数同上，尤其是：

- `frame_id`
- `sensor_link_name`
- `ego_link_name`
- `output_in_sensor_frame`

## 5. TF 与坐标系建议

建议采用以下约定：

- 点云消息头：`frame_id=radar_link`
- 发布点坐标：`output_in_sensor_frame=true`（点以雷达局部坐标输出）
- 系统 TF 里保证 `base_link -> radar_link` 存在（固定或动态）

若你仍用 `output_in_sensor_frame=false`，则点坐标是世界系/仿真系坐标，`frame_id` 应与实际坐标系一致，避免“看起来漂移”。

## 6. 并行多传感器注意项

- 话题名不要冲突（建议命名空间化，如 `/veh1/radar/points_4d`）。
- 每个传感器用独立 `frame_id`。
- 高分辨率多雷达并发会拉低实时率（RTF），先降分辨率和更新率再调高。

## 7. 启动后验证

```bash
source <ws>/install/setup.bash
ros2 topic list | grep radar
ros2 topic echo /radar/points_4d --once
```

重点检查：

- `header.frame_id` 是否为你期望值（如 `radar_link`）
- `width` 在无目标时可为 `0`
- RViz Fixed Frame 与 TF 可达性是否正确

## 8. 常见问题与处理

1. **`libusv_4d_radar_plugin.so` 找不到**
   - 检查 `GZ_SIM_SYSTEM_PLUGIN_PATH` 是否包含 `<ws>/install/usv_mmwave_sim/lib`。

2. **SDF warning: plugin under link not defined**
   - 把插件移到 `<model>` 下，并通过 `sensor_link_name` 指定真实雷达 link。

3. **RViz 有话题但看不到点**
   - 检查 `frame_id` 与 TF 是否匹配。
   - 检查显示器 QoS、点大小和颜色映射（`rcs` 强度）。

4. **看起来每条射线都有点**
   - 确认是否把自车碰撞体误当目标；当前插件已按顶层 model 过滤自车。
   - 确认 `enable_sea_clutter` 是否已关闭。

## 9. 建议的上线流程

1. 先在 `frame_linked_4d_radar_validation` 场景自检参数。
2. 迁移到你的整机 world/URDF，仅替换模型路径与 topic 名。
3. 加入顶层 launch 的统一命名空间与 remap。
4. 最后做多传感器并发压测（RTF、话题频率、RViz/算法订阅稳定性）。
