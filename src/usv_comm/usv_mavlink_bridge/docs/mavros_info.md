# MAVROS 信息整理

## 一、上行遥测数据（飞控 -> MAVROS -> Jetson）

这类数据主要用于 Jetson 端的环境感知、状态监控和导航解算。

| 飞控端（MAVLink 消息） | ROS 2 端（MAVROS 话题） | 内容概述 | 频率 |
| --- | --- | --- | --- |
| `HEARTBEAT` | `/mavros/state` | 飞控连接状态（`connected`）、解锁状态（`armed`）、当前模式（`mode`）。 | `1 Hz` |
| `GLOBAL_POSITION_INT` / `GPS_RAW_INT` | `/mavros/global_position/global` | 经纬度与高程。 | 高频（`5~10 Hz`） |
| `GLOBAL_POSITION_INT` | `/mavros/global_position/raw/gps_vel` 或 `/mavros/local_position/velocity_body` | 对地速度。 | 高频（`10~30 Hz`） |
| `ATTITUDE` / `HIGHRES_IMU` | `/mavros/imu/data` | 欧拉角、角速度、线加速度。 | 极高频（`50~100 Hz`） |

## 二、下行控制指令（Jetson -> MAVROS -> 飞控）

这类数据用于边缘端算法或云端远程接管 USV 的运动状态。  
需要注意：部分高频控制（如速度环接管）需要维持连续不断的数据流。

| 飞控端（MAVLink 消息） | ROS 2 端（MAVROS 服务/话题） | 内容概述 | 频率 |
| --- | --- | --- | --- |
| `COMMAND_LONG (MAV_CMD_DO_SET_MODE)` | （服务）`/mavros/set_mode` | 切换飞控模式：`AUTO`（自动）、`MANUAL`（手动）或 `OFFBOARD/GUIDED`（外部控制）。 | 事件触发 |
| `COMMAND_LONG (MAV_CMD_COMPONENT_ARM_DISARM)` | （服务）`/mavros/cmd/arming` | `value: true` 解锁，`value: false` 上锁。 | 事件触发 |
| `COMMAND_LONG (MAV_CMD_DO_FLIGHTTERMINATION)` | （服务）`/mavros/cmd/command` 或（话题）`/mavros/rc/override` | 通过紧急停车介入，强行拉低油门通道实现物理级停车。 | 事件触发 |
| `MISSION_ITEM_INT` | （服务）`/mavros/mission/push` | 离线静态航点下发。 | 事件触发 |
| `SET_POSITION_TARGET_GLOBAL_INT` | （话题）`/mavros/setpoint_position/global` | 实时动态目标点下发。 | 高频（`>2 Hz`，需维持心跳） |
| `SET_POSITION_TARGET_LOCAL_NED` | （话题）`/mavros/setpoint_velocity/cmd_vel` | 下发 `x/y/z` 速度向量与偏航角速度（底层姿态/速度控制介入）。 | 高频（`>10 Hz`，需持续发送） |

## 三、MAVROS 与 usv_interfaces 建议映射表

> 说明：  
> - `MAVROS` 话题用于飞控生态互联（外部接口层）。  
> - `usv_interfaces` 话题用于项目内部统一语义（内部契约层）。  
> - 建议通过专门桥接节点做“外部接口层 -> 内部契约层”的转换，避免业务节点直接耦合 `/mavros/*`。

| 数据方向 | MAVROS 侧（外部接口） | 建议统一到 usv_interfaces | 当前现状 | 建议落地 |
| --- | --- | --- | --- | --- |
| 上行遥测 | `/mavros/imu/data` | `/sensors/imu/data`（`TOPIC_SENSOR_IMU`） | 已改造：`mav_imu_bridge` 主订阅已切到 `/sensors/imu/data`，`/imu/data` 仅兼容可选。 | 继续保持业务侧只读统一话题。 |
| 上行遥测 | `/mavros/global_position/global` | `/sensors/gps/data`（`TOPIC_SENSOR_GPS`） | 已改造：`mav_gps_bridge` 主输入为 `NavSatFix` 的 `/sensors/gps/data`。 | 逐步下线 `/comm/*` 旧输入。 |
| 上行遥测 | `/mavros/global_position/raw/gps_vel` 或 `/mavros/local_position/velocity_body` | `/usv/state/velocity`（`TOPIC_STATE_VELOCITY`） | 已改造：新增统一速度话题常量，主输入为 `TwistStamped`。 | 业务节点统一消费该速度语义。 |
| 飞控状态 | `/mavros/state` | `/usv/state/autopilot`（`TOPIC_AUTOPILOT_STATE`） | 已新增常量，当前桥接包暂未实现该状态转发节点。 | 后续可新增 `mav_state_bridge` 将 `/mavros/state` 转发到统一话题。 |
| 下行控制 | `/mavros/setpoint_velocity/cmd_vel` | `/cmd_vel`（`TOPIC_CMD_VEL`） | 两套入口并存，业务语义边界不清晰。 | 统一业务入口为 `/cmd_vel`；飞控适配层负责转发到 `/mavros/setpoint_velocity/cmd_vel`。 |
| 下行控制 | `/mavros/set_mode`、`/mavros/cmd/arming` | `/usv/control/mode`（`TOPIC_CONTROL_MODE`）+ 控制服务接口 | 当前模式/解锁控制仍偏 MAVROS 直连。 | 由控制管理节点消费统一控制话题/服务，再调用 MAVROS 服务。 |

### 约定建议（避免后续接口漂移）

1. 业务节点不直接依赖 `/mavros/*`，统一订阅/发布 `usv_interfaces` 话题。  
2. MAVROS/MAVLink 相关节点只负责“协议适配”，不承载业务决策。  
3. 新增话题时，先在 `usv_interfaces/topics.hpp` 与 `usv_interfaces/topics.py` 同步登记，再接入节点代码。  
4. 对历史兼容话题（如 `/imu/data`、`/comm/gps`）标注“兼容期”，设置退役时间。  

## 四、当前桥接实现（已落地）

- 已新增集中映射文件：`usv_mavlink_bridge/topic_contract.py`，统一维护主话题与旧话题兼容映射。  
- `mav_imu_bridge`：主输入 `sensor_msgs/Imu@/sensors/imu/data`，兼容输入 `/imu/data`（参数开关）。  
- `mav_gps_bridge`：主输入 `sensor_msgs/NavSatFix@/sensors/gps/data` + `geometry_msgs/TwistStamped@/usv/state/velocity`；兼容输入 `/comm/gps`、`/comm/gpsr`（参数开关）。  
- `mav_rc_bridge`：主输出 `geometry_msgs/Twist@/usv/control/manual/raw`；兼容输出 `/control/manual_control_raw`（参数开关）。  
- 启动参数统一放在 `config/bridge_topics.yaml`，`usv_mavlink_bridge.launch.py` 已默认加载。

## 五、参数开关（兼容迁移）

默认值见 `config/bridge_topics.yaml`：

- `use_legacy_imu_topic`：是否兼容订阅 `/imu/data`
- `use_legacy_gps_topics`：是否兼容订阅 `/comm/gps`、`/comm/gpsr`
- `publish_legacy_manual_topic`：是否兼容发布 `/control/manual_control_raw`
- `publish_legacy_imu_topic`：仿真 IMU 是否兼容发布旧话题
- `publish_legacy_gps_topics`：仿真 GPS 是否兼容发布旧话题

建议：新链路联调完成后，将兼容开关保持为 `false`，逐步退役旧话题。