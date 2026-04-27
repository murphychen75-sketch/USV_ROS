# usv_mavlink_bridge 使用说明

本包用于在 ROS 2 与 MAVLink 之间做协议桥接，并已按 `usv_interfaces` 完成主链路对齐。  
实现方式为多节点拆分 + 单一映射源（`ros2_mav_demo/topic_contract.py`）。

## 1. 功能概览

- 上行遥测：
  - `sensor_msgs/Imu@/sensors/imu/data` -> `HIGHRES_IMU(105)`
  - `sensor_msgs/NavSatFix@/sensors/gps/data` + `geometry_msgs/TwistStamped@/usv/state/velocity`
    -> `GPS_RAW_INT(24)` + `GLOBAL_POSITION_INT(33)`
- 下行控制：
  - `MANUAL_CONTROL(69)` -> `geometry_msgs/Twist@/usv/control/manual/raw`
- 连接维持：
  - 心跳 `HEARTBEAT(0)` 与参数握手响应

## 2. 统一映射与兼容策略

- 主链路（默认）使用 `usv_interfaces` 常量话题：
  - `/sensors/imu/data`
  - `/sensors/gps/data`
  - `/usv/state/velocity`
  - `/usv/control/manual/raw`
- 旧链路（兼容）可按参数开启：
  - `/imu/data`
  - `/comm/gps`、`/comm/gpsr`
  - `/control/manual_control_raw`

参数文件：`config/bridge_topics.yaml`

## 3. 运行方式

### 3.1 一键启动演示链路

```bash
ros2 launch ros2_mav_demo demo_launch.py
```

该 launch 默认启动：
- `imu_sim`
- `gps_sim`
- `heartbeat`
- `imu_bridge`
- `gps_bridge`
- `rc_bridge`

### 3.2 单独启动摇杆桥接

```bash
ros2 run ros2_mav_demo rc_bridge
```

### 3.3 QGC 观测建议

启动后打开 QGC，进入 Analyze Tools 的 MAVLink Inspector，可查看发送消息。

## 4. 节点说明

### `imu_sim`
- 作用：模拟 IMU 数据
- 主发布：`sensor_msgs/Imu@/sensors/imu/data`
- 兼容开关：`publish_legacy_imu_topic`

### `gps_sim`
- 作用：模拟 GPS 与速度数据
- 主发布：
  - `sensor_msgs/NavSatFix@/sensors/gps/data`
  - `geometry_msgs/TwistStamped@/usv/state/velocity`
- 兼容开关：`publish_legacy_gps_topics`

### `heartbeat`
- 作用：周期发送心跳并处理参数握手
- MAVLink：`HEARTBEAT(0)`

### `imu_bridge`
- 作用：订阅 IMU 并编码发送 MAVLink IMU
- MAVLink：`HIGHRES_IMU(105)`
- 兼容开关：`use_legacy_imu_topic`

### `gps_bridge`
- 作用：订阅 GPS+速度并编码发送 MAVLink 位置/速度
- MAVLink：`GPS_RAW_INT(24)`、`GLOBAL_POSITION_INT(33)`
- 兼容开关：`use_legacy_gps_topics`

### `rc_bridge`
- 作用：接收 `MANUAL_CONTROL` 并发布 ROS 控制话题
- 主输出：`geometry_msgs/Twist@/usv/control/manual/raw`
- 兼容输出开关：`publish_legacy_manual_topic`

## 5. 构建与验证

在工作区根目录执行：

```bash
colcon build --packages-select usv_interfaces --symlink-install
colcon build --packages-select ros2_mav_demo --symlink-install
source install/setup.bash
```

## 6. 参考

- MAVLink 消息定义：[https://mavlink.io/zh/messages/common.html](https://mavlink.io/zh/messages/common.html)