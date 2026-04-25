# MQTT 消息契约与内部接口映射

本文档说明 `usv_mqtt_bridge` 对外发布的 MQTT 消息格式，以及它与当前内部 ROS 2 话题/接口之间的对应关系。

## 设计原则

- 外部 MQTT topic 与 envelope 格式只保留在 `usv_mqtt_bridge` 内部
- 内部业务语义优先收敛到 `usv_interfaces`
- 当前桥接节点仍以 `std_msgs/String` 承载 JSON 文本，后续可以逐步升级到 `usv_interfaces` 中的强类型消息

## MQTT topic 约定

### 上行

- `usv/{device_id}/telemetry/state`
- `usv/{device_id}/telemetry/vision`
- `usv/{device_id}/telemetry/radar`

### 下行

- `usv/{device_id}/cmd/control`
- `usv/{device_id}/cmd/config`

### 链路状态

- `usv/{device_id}/status/lwt`

## 外发消息统一结构

所有上行消息默认都使用统一 envelope：

```json
{
  "timestamps": {
    "sensor_capture_time": "2026-04-22T10:00:00.000Z",
    "algorithm_output_time": "2026-04-22T10:00:00.020Z",
    "gateway_publish_time": "2026-04-22T10:00:00.050Z"
  },
  "device_id": "001",
  "msg_type": "state",
  "seq": 1,
  "payload": {
    "battery_pct": 86.5,
    "lat": 31.123,
    "lon": 121.456,
    "heading_deg": 75.0,
    "speed_mps": 2.3
  }
}
```

字段说明：

- `timestamps`：时间戳集合；如果内部输入已经带有 `timestamps`，桥接节点会继承并补齐 `gateway_publish_time`
- `device_id`：船体设备编号
- `msg_type`：消息类别，对应 `state` / `vision` / `radar` / `control` / `config` / `status`
- `seq`：单类别消息递增序号
- `payload`：业务载荷

## MQTT 与 ROS 2 话题映射

| 方向 | ROS 2 侧 | 当前承载类型 | MQTT 侧 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| 上行 | `/usv/state` | `std_msgs/String`(JSON) | `usv/{device_id}/telemetry/state` | 船体状态、位置、电量等 |
| 上行 | `/usv/vision/metadata` | `std_msgs/String`(JSON) | `usv/{device_id}/telemetry/vision` | 视觉检测摘要 |
| 上行 | `/usv/radar/targets` | `std_msgs/String`(JSON) | `usv/{device_id}/telemetry/radar` | 雷达目标列表 |
| 下行 | `/usv/cmd/control/raw` | `std_msgs/String`(JSON) | `usv/{device_id}/cmd/control` | 控制命令下发 |
| 下行 | `/usv/cmd/config/raw` | `std_msgs/String`(JSON) | `usv/{device_id}/cmd/config` | 参数更新下发 |
| 状态 | 无 ROS 输出 | - | `usv/{device_id}/status/lwt` | MQTT 在线/离线状态 |

## 与 `usv_interfaces` 的结构对应关系

当前实现里，MQTT bridge 还没有直接使用 `usv_interfaces` 强类型消息，而是先通过 JSON 串承载。为了后续升级，建议按下面的语义对应关系理解：

| 内部语义 | 当前 ROS 2 输入/输出 | 建议对齐的 `usv_interfaces` 结构 | MQTT payload 典型字段 |
| :--- | :--- | :--- | :--- |
| 船体综合状态 | `/usv/state` | `VesselState` | `battery_pct`、`lat`、`lon`、`heading_deg`、`speed_mps` |
| 作业模式/控制指令 | `/usv/cmd/control/raw` | `OperationMode` 或控制类扩展接口 | `command`、`mode`、`waypoints`、`estop` |
| 动态航路点 | `/usv/cmd/control/raw` | `WaypointRoute` | `waypoints` |
| 桥接配置更新 | `/usv/cmd/config/raw` | 暂无统一强类型，保留桥接内部配置 | `state_rate_hz`、`vision_rate_hz`、`radar_rate_hz`、`radar_safe_distance_m` |

## 结构映射建议

### `state`

建议把 MQTT `payload` 理解为 `VesselState` 的外发裁剪视图，而不是新的内部真值结构。也就是说：

- 内部算法/融合节点优先发布 `usv_interfaces/VesselState`
- `usv_mqtt_bridge` 再将其转换成公网传输更友好的 JSON payload

### `control`

`control` 当前允许的字段为：

- `command`
- `mode`
- `waypoints`
- `estop`

其中：

- `mode` 可逐步映射到 `OperationMode`
- `waypoints` 可逐步映射到 `WaypointRoute`
- `command` / `estop` 如果后续被多个内部节点共同消费，再考虑抽象进 `usv_interfaces`

### `config`

`config` 目前属于桥接运行时配置，只在 `usv_mqtt_bridge` 内部生效，不建议直接抽象到 `usv_interfaces`。

当前支持：

- `state_rate_hz`
- `vision_rate_hz`
- `radar_rate_hz`
- `radar_safe_distance_m`

## 升级路径

后续如果要从 JSON 串升级到强类型 ROS 接口，推荐顺序如下：

1. 先由内部节点输出 `usv_interfaces/VesselState`、`WaypointRoute`、`OperationMode`
2. 在 `usv_mqtt_bridge` 内新增对应的 typed subscriber / converter
3. 保持 MQTT 外发 envelope 不变，只替换 `payload` 生成来源
4. 最后再移除遗留的 `std_msgs/String` 输入路径
