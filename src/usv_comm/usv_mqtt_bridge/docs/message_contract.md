# MQTT 消息契约与 ROS 对齐

本文档描述 `usv_mqtt_bridge` 当前实现：优先对齐 [`mqtt_info.md`](./mqtt_info.md)，`usv_interfaces` 对齐采取“有则映射、无则留空”。

## 设计原则

- MQTT Topic 优先遵循协议文档，不以历史实现为准
- ROS 侧暂无对应话题时，参数默认留空，节点自动跳过该链路
- ROS 与 MQTT 之间暂用 `std_msgs/String` 承载 JSON

## Topic 命名

统一格式：

- `/{product_id}/{device_id}/{unit_id}/{msg_type}`

## 外发消息结构

桥接上行统一封装为 envelope：

```json
{
  "timestamps": {
    "sensor_capture_time": "2026-04-22T10:00:00.000Z",
    "algorithm_output_time": "2026-04-22T10:00:00.020Z",
    "gateway_publish_time": "2026-04-22T10:00:00.050Z"
  },
  "device_id": "USV_N0001",
  "msg_type": "radar/scan",
  "seq": 1,
  "payload": {}
}
```

## MQTT 与 ROS 2 映射（当前实现）

| 方向 | ROS 2 侧 | 当前承载类型 | MQTT 侧 | 备注 |
| :--- | :--- | :--- | :--- | :--- |
| 上行 | `/usv/state` | `std_msgs/String` | `.../status` | 已接入 |
| 上行 | `/usv/vision/metadata` | `std_msgs/String` | `.../vision/targets` | 已接入 |
| 上行 | `/usv/radar/targets` | `std_msgs/String` | `.../radar/scan` | 已接入 |
| 上行 | 空 | - | `.../status/jetson` 等 | 暂未接 ROS，参数留空 |
| 下行 | `/usv/cmd/mode/raw` | `std_msgs/String` | `.../mode` | 已接入 |
| 下行 | `/usv/cmd/radar/control/raw` | `std_msgs/String` | `.../radar/control` | 已接入 |
| 下行 | 空 | - | `.../estop` 等 | 暂未接 ROS，参数留空 |

## 与 `usv_interfaces` 对齐策略

| 协议语义 | 当前 ROS 话题 | `usv_interfaces` 对齐建议 |
| :--- | :--- | :--- |
| `status` | `/usv/state` | `VesselState` |
| `mode` 下行 | `/usv/cmd/mode/raw` | `OperationMode` |
| `auto/task` 下行 | 空 | `WaypointRoute`（后续补） |
| `vision/targets` | `/usv/vision/metadata` | 暂无，留空 |
| `radar/scan` / `radar/map` | `/usv/radar/targets` / 空 | 暂无，留空 |
