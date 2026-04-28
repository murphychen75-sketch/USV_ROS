# MQTT 消息契约与 ROS 对齐

本文档基于最新版 [`mqtt_info.md`](./mqtt_info.md) 说明 `usv_mqtt_bridge` 的实现映射关系。  
当前已按“仅保留两个变量”调整为：

- `product_id`
- `device_id`

不再使用 `uid/unit_id`。Topic 仅通过消息主题本身区分业务类型。

## Topic 规范

统一模板：

- `/sys/{productKey}/{deviceName}/thing/{type}/{identifier}`

## Envelope（桥接内部统一外发）

```json
{
  "timestamps": {
    "sensor_capture_time": "2026-04-22T10:00:00.000Z",
    "algorithm_output_time": "2026-04-22T10:00:00.020Z",
    "gateway_publish_time": "2026-04-22T10:00:00.050Z"
  },
  "device_id": "USV_N0001",
  "msg_type": "status",
  "seq": 1,
  "payload": {}
}
```

## 当前 MQTT <-> ROS 映射

| 方向 | MQTT 主题 | ROS 话题 | 承载 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| 上行 | `/sys/{pk}/{dn}/thing/property/status` | `/usv/state` | `std_msgs/String` | 已接入 |
| 上行 | `/sys/{pk}/{dn}/thing/event/vision_targets` | `/usv/vision/metadata` | `std_msgs/String` | 已接入 |
| 上行 | `/sys/{pk}/{dn}/thing/property/radar_scan` | `/usv/radar/targets` | `std_msgs/String` | 已接入 |
| 下行 | `/sys/{pk}/{dn}/thing/service/mode` | `/usv/cmd/mode/raw` | `std_msgs/String` | 已接入 |
| 下行 | `/sys/{pk}/{dn}/thing/service/radar_scan_config` | `/usv/cmd/radar/control/raw` | `std_msgs/String` | 已接入 |

## 与 `usv_interfaces` 对应关系（当前）

| 协议语义 | 当前 ROS 话题 | 建议对齐的 `usv_interfaces` |
| :--- | :--- | :--- |
| `property/status` | `/usv/state` | `VesselState` |
| `service/mode` | `/usv/cmd/mode/raw` | `OperationMode` |
| `service/auto_task` | 空 | `WaypointRoute` |
| `event/vision_targets` | `/usv/vision/metadata` | 暂无（待补） |
| `property/radar_scan` | `/usv/radar/targets` | 暂无（待补） |
| `service/radar_scan_config` | `/usv/cmd/radar/control/raw` | 暂无（待补） |

## 当前缺少的 ROS 话题（已在参数中留空）

- 上行缺少：
  - `property/status_jetson`
  - `event/heartbeat`
  - `event/alarm`
  - `event/diag_result`
  - `event/radar_scan_config_reply`
  - `property/radar_map`
  - `property/perception_trajectory`
  - `property/depth`
  - `property/weather`
- 下行缺少：
  - `service/estop`
  - `service/arm`
  - `service/auto_task`
  - `service/video_ctrl`
  - `service/diag_request`
