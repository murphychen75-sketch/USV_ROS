# MQTT 消息契约与 ROS 对齐

本文档基于最新版 [`mqtt_info.md`](./mqtt_info.md) 说明 `usv_mqtt_bridge` 的实现映射关系。  
当前已按“仅保留两个变量”调整为：

- `product_id`
- `device_id`

不再使用 `uid/unit_id`。Topic 仅通过消息主题本身区分业务类型。


| 编号 | MQTT 物模型类型 | 行为方向 | ROS 2 映射实现建议 |
|---|---|---|---|
| 1 | Property (属性上行) | 端 -> 云 | 订阅 ROS Topic，必要时节流后上报 MQTT |
| 2 | Event (事件上行) | 端 -> 云 | 订阅 ROS Topic，按事件触发上报 MQTT |
| 3 | Service (下行请求) | 云 -> 端 | 接收 MQTT 请求，转发 ROS Service/Action/Topic |
| 4 | Service Reply (上行回复) | 端 -> 云 | 采集 ROS 执行结果，发布 MQTT `_reply` |
| 5 | Service Async (任务异步链路) | 云 <-> 端 | MQTT 请求映射 ROS Action Goal，反馈/结果回传 |

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

## 当前 MQTT <-> ROS 映射（按物模型 5 类）

状态口径：

- **接口层**：`usv_interfaces` 是否已有对应 `msg/srv/action`。
- **桥接层**：`usv_mqtt_bridge` 是否已在 `protocol.py + node.py + params.yaml` 注册映射。

### 类型1：Property 上行（设备 -> 云）

| 序号 | MQTT 主题 | 推荐 ROS 语义 | 承载类型 | 接口层 | 桥接层 |
| :---: | :--- | :--- | :--- | :---: | :---: |
| [1-01](#ref-1-01) | `property/status_jetson` | `/usv/monitor/jetson_status` | `usv_interfaces/JetsonStatus` | 已对齐 | 已接入 |
| [1-02](#ref-1-02) | `property/motor` | `/usv/motor/status` | `usv_interfaces/MotorStatus` | 已对齐 | 已接入 |
| [1-03](#ref-1-03) | `property/imu` | `/usv/imu/status` | `usv_interfaces/ImuStatus` | 已对齐 | 已接入 |
| [1-04](#ref-1-04) | `property/radar_mm` | `/usv/radar/mm/obstacles` | `usv_interfaces/RadarMmObstacles` | 已对齐 | 已接入 |
| [1-05](#ref-1-05) | `property/radar_nav` | `/usv/radar/nav/scan` | `usv_interfaces/RadarNavScan` | 已对齐 | 已接入 |
| [1-06](#ref-1-06) | `property/radar_nav_map` | `/usv/radar/nav/map` | `usv_interfaces/RadarNavMap` | 已对齐 | 已接入 |
| [1-07](#ref-1-07) | `property/perception_trajectory` | `/usv/perception/trajectory` | `usv_interfaces/PerceptionTrajectories` | 已对齐 | 已接入 |
| [1-08](#ref-1-08) | `property/gps_status` | `/usv/gps/status` | `usv_interfaces/GpsStatus` | 已对齐 | 已接入 |
| [1-09](#ref-1-09) | `property/weather_status` | `/usv/weather/status` | `usv_interfaces/WeatherStatus` | 已对齐 | 已接入 |
| [1-10](#ref-1-10) | `property/depth_status` | `/usv/depth/status` | `usv_interfaces/DepthStatus` | 已对齐 | 已接入 |
| [1-11](#ref-1-11) | `property/battery_status` | `/usv/battery/status` | `usv_interfaces/BatteryStatus` | 已对齐 | 已接入 |
| [1-12](#ref-1-12) | `property/fuel_status` | `/usv/fuel/status` | `usv_interfaces/FuelStatus` | 已对齐 | 已接入 |
| [1-13](#ref-1-13) | `property/mcu_status` | `/usv/mcu/status` | `usv_interfaces/McuStatus` | 已对齐 | 已接入 |
| [1-14](#ref-1-14) | `property/ais` | `/usv/ais/raw` | `usv_interfaces/AisRaw` | 已对齐 | 已接入 |
| [1-15](#ref-1-15) | `property/io_status` | `/usv/io/status` | `usv_interfaces/IoStatus` | 已对齐 | 已接入 |

### 类型2：Event 上行（设备 -> 云）

| 序号 | MQTT 主题 | 推荐 ROS 语义 | 承载类型 | 接口层 | 桥接层 |
| :---: | :--- | :--- | :--- | :---: | :---: |
| [2-01](#ref-2-01) | `event/jetson_heartbeat` | `/usv/monitor/heartbeat` | `usv_interfaces/HeartbeatStatus` | 已对齐 | 已接入 |
| [2-02](#ref-2-02) | `event/mcu_heartbeat` | `/usv/monitor/heartbeat` | `usv_interfaces/HeartbeatStatus` | 已对齐 | 已接入 |
| [2-03](#ref-2-03) | `event/alarm` | `/usv/monitor/alarm` | `usv_interfaces/AlarmEvent` | 已对齐 | 已接入 |
| [2-04](#ref-2-04) | `event/mission_delta` | `/usv/mission/delta` | `usv_interfaces/MissionDelta` | 已对齐 | 已接入 |
| [2-05](#ref-2-05) | `event/aivideo_status` | `/usv/video/status` | `usv_interfaces/VideoStreamStatus` | 已对齐 | 已接入 |
| [2-06](#ref-2-06) | `event/aivision_targets` | `/usv/vision/targets` | `usv_interfaces/AIVisionTargets` | 已对齐 | 已接入 |
| [2-07](#ref-2-07) | `event/diag_result` | `/usv/diag/result` | `usv_interfaces/DiagResult` | 已对齐 | 已接入 |
| [2-08](#ref-2-08) | `event/task_prog` | `/usv/task/progress` | `usv_interfaces/TaskProgress` | 已对齐 | 已接入 |

### 类型3：Service 下行请求（云 -> 设备）

| 序号 | MQTT 主题 | 推荐 ROS 语义 | 承载类型 | 接口层 | 桥接层 |
| :---: | :--- | :--- | :--- | :---: | :---: |
| [3-01](#ref-3-01) | `service/estop` | `/usv/service/estop` | `usv_interfaces/srv/EStop` | 已对齐 | 已接入 |
| [3-02](#ref-3-02) | `service/arm` | `/usv/service/arm` | `usv_interfaces/srv/Arm` | 已对齐 | 已接入 |
| [3-03](#ref-3-03) | `service/mode` | `/usv/service/set_mode` | `usv_interfaces/srv/SetMode` | 已对齐 | 已接入 |
| [3-04](#ref-3-04) | `service/manual_ctrl` | `/usv/service/manual_control` | `usv_interfaces/srv/ManualControl` | 已对齐 | 已接入 |
| [3-05](#ref-3-05) | `service/auto_task` | `/usv/task/execute_auto_task`(Goal) | `usv_interfaces/action/ExecuteAutoTask` | 已对齐 | 已接入 |
| [3-06](#ref-3-06) | `service/params` | `/usv/service/set_params` | `usv_interfaces/srv/SetParams` | 已对齐 | 已接入 |
| [3-07](#ref-3-07) | `service/aivideo_ctrl` | `/usv/service/video_control` | `usv_interfaces/srv/VideoControl` | 已对齐 | 已接入 |
| [3-08](#ref-3-08) | `service/radar_nav_config` | `/usv/service/radar_nav_config` | `usv_interfaces/srv/RadarNavConfig` | 已对齐 | 已接入 |
| [3-09](#ref-3-09) | `service/io_ctrl` | `/usv/service/io_control` | `usv_interfaces/srv/IoControl` | 已对齐 | 已接入 |
| [3-10](#ref-3-10) | `service/diag_request` | `/usv/service/diag_request` | `usv_interfaces/srv/DiagRequest` | 已对齐 | 已接入 |

### 类型4：Service 回复上行（设备 -> 云）

| 序号 | MQTT 主题 | 推荐 ROS 语义 | 承载类型 | 接口层 | 桥接层 |
| :---: | :--- | :--- | :--- | :---: | :---: |
| [4-01](#ref-4-01) | `service/estop_reply` | `/usv/service/estop`(Response) | `usv_interfaces/srv/EStop` | 已对齐 | 已接入 |
| [4-02](#ref-4-02) | `service/arm_reply` | `/usv/service/arm`(Response) | `usv_interfaces/srv/Arm` | 已对齐 | 已接入 |
| [4-03](#ref-4-03) | `service/mode_reply` | `/usv/service/set_mode`(Response) | `usv_interfaces/srv/SetMode` | 已对齐 | 已接入 |
| [4-04](#ref-4-04) | `service/manual_ctrl_reply` | `/usv/service/manual_control`(Response) | `usv_interfaces/srv/ManualControl` | 已对齐 | 已接入 |
| [4-05](#ref-4-05) | `service/params_reply` | `/usv/service/set_params`(Response) | `usv_interfaces/srv/SetParams` | 已对齐 | 已接入 |
| [4-06](#ref-4-06) | `service/aivideo_ctrl_reply` | `/usv/service/video_control`(Response) | `usv_interfaces/srv/VideoControl` | 已对齐 | 已接入 |
| [4-07](#ref-4-07) | `service/radar_nav_config_reply` | `/usv/service/radar_nav_config`(Response) | `usv_interfaces/srv/RadarNavConfig` | 已对齐 | 已接入 |
| [4-08](#ref-4-08) | `service/io_ctrl_reply` | `/usv/service/io_control`(Response) | `usv_interfaces/srv/IoControl` | 已对齐 | 已接入 |
| [4-09](#ref-4-09) | `service/diag_request_reply` | `/usv/service/diag_request`(Response) | `usv_interfaces/srv/DiagRequest` | 已对齐 | 已接入 |
| [4-10](#ref-4-10) | `service/auto_task_reply` | `/usv/task/execute_auto_task`(Result) | `usv_interfaces/action/ExecuteAutoTask` | 已对齐 | 已接入 |

### 类型5：任务异步链路（Action 专项）

| 序号 | MQTT 链路 | ROS 语义 | 承载类型 | 状态 |
| :---: | :--- | :--- | :--- | :--- |
| [5-01](#ref-5-01) | `service/auto_task` | Action Goal | `usv_interfaces/action/ExecuteAutoTask` | 已接入 |
| [5-02](#ref-5-02) | `event/task_prog` | Action Feedback | `usv_interfaces/TaskProgress` | 已接入 |
| [5-03](#ref-5-03) | `service/auto_task_reply` | Action Result | `usv_interfaces/action/ExecuteAutoTask` | 已接入 |

## 强映射参照（按序号逐行）

<a id="ref-1-01"></a>
#### 1-01 `property/status_jetson`
- 主题名称和 ROS 话题：`property/status_jetson` -> `/usv/monitor/jetson_status`
- 常量名称和实际话题名称：`MSG_TYPE_STATUS_JETSON` -> `/sys/{product_id}/{device_id}/thing/property/status_jetson`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "cpu_usage_percent": 42.5,
    "memory_usage_percent": 68.3,
    "gpu_usage_percent": 27.8,
    "temperature_c": 72.4,
    "uptime_ms": 86400000,
    "disk_usage_percent": 55.2
  }
}
```
```json
std_msgs/Header header  #标准消息头（时间戳与坐标系）
float32 cpu_usage_percent  #CPU使用率百分比
float32 memory_usage_percent  #内存使用率百分比
float32 gpu_usage_percent  #GPU使用率百分比
float32 temperature_c  #设备温度（摄氏度）
uint64 uptime_ms  #系统运行时长（毫秒）
float32 disk_usage_percent  #磁盘使用率百分比
```

<a id="ref-1-02"></a>
#### 1-02 `property/motor`
- 主题名称和 ROS 话题：`property/motor` -> `/usv/motor/status`
- 常量名称和实际话题名称：`MSG_TYPE_MOTOR` -> `/sys/{product_id}/{device_id}/thing/property/motor`
```json
{
  "timestamp": 1703123456789,
  "seq": 2,
  "data": {
    "motor_id": 1,
    "ts": 1703123456000,
    "rpm": 1500,
    "angle": 20,
    "power_w": 602.5
  }
}
```
```json
std_msgs/Header header  # 标准消息头
int32 motor_id  # 电机、唯一标识
uint64 ts_ms  # ts_ms 字段含义
int32 rpm  # 转速（转每分钟）
int32 angle  # 角度
float32 power_w  # 功率（瓦）
```

<a id="ref-1-03"></a>
#### 1-03 `property/imu`
- 主题名称和 ROS 话题：`property/imu` -> `/usv/imu/status`
- 常量名称和实际话题名称：`MSG_TYPE_IMU` -> `/sys/{product_id}/{device_id}/thing/property/imu`
```json
{
  "timestamp": 1703123456789,
  "seq": 3,
  "data": {
    "orientation": {
      "yaw_deg": 120.1,
      "roll_deg": 1.2,
      "pitch_deg": 0.5
    },
    "angular_velocity": {
      "yaw_rate_dps": 0.5,
      "roll_rate_dps": 0.1,
      "pitch_rate_dps": 0.05
    },
    "linear_acceleration": {
      "x_mps2": 0.01,
      "y_mps2": 0.02,
      "z_mps2": 9.81
    }
  }
}
```
```json
std_msgs/Header header  #标准消息头（时间戳与坐标系）
float32 yaw_deg  #航向角（度）
float32 roll_deg  #横滚角（度）
float32 pitch_deg  #俯仰角（度）
float32 yaw_rate_dps  #航向角速度（度每秒）
float32 roll_rate_dps  #横滚角速度（度每秒）
float32 pitch_rate_dps  #俯仰角速度（度每秒）
float32 accel_x_mps2  #X轴线加速度（米每二次方秒）
float32 accel_y_mps2  #Y轴线加速度（米每二次方秒）
float32 accel_z_mps2  #Z轴线加速度（米每二次方秒）
```

<a id="ref-1-04"></a>
#### 1-04 `property/radar_mm`
- 主题名称和 ROS 话题：`property/radar_mm` -> `/usv/radar/mm/obstacles`
- 常量名称和实际话题名称：`MSG_TYPE_RADAR_MM` -> `/sys/{product_id}/{device_id}/thing/property/radar_mm`
```json
{
  "timestamp": 1703123456789,
  "seq": 4,
  "data": {
    "obstacles_num": 2,
    "obstacles": [
      {
        "id": "obj_001",
        "distance_m": 5.2,
        "angle_deg": 30.0,
        "relative_speed_mps": 0.5
      },
      {
        "id": "obj_002",
        "distance_m": 7.2,
        "angle_deg": 70.0,
        "relative_speed_mps": 0.2
      }
    ]
  }
}
```
```json
std_msgs/Header header  # 标准消息头
uint32 obstacles_num  # obstacles_num 字段含义
usv_interfaces/RadarMmObstacle[] obstacles  # obstacles 字段含义
```

<a id="ref-1-05"></a>
#### 1-05 `property/radar_nav`
- 主题名称和 ROS 话题：`property/radar_nav` -> `/usv/radar/nav/scan`
- 常量名称和实际话题名称：`MSG_TYPE_RADAR_NAV` -> `/sys/{product_id}/{device_id}/thing/property/radar_nav`
```json
{
  "timestamp": 1703123456789,
  "seq": 5,
  "data": {
    "timestamps": [
      {
        "name": "scan_start",
        "time": 1703123456000
      },
      {
        "name": "scan_end",
        "time": 1703123456700
      },
      {
        "name": "signal_processing_end",
        "time": 1703123456789
      }
    ],
    "targets_num": 2,
    "targets": [
      {
        "range_m": 45.2,
        "bearing_deg": 32.5,
        "intensity": 0.92,
        "velocity_mps": 6.8
      },
      {
        "range_m": 78.0,
        "bearing_deg": 120.3,
        "intensity": 0.45,
        "velocity_mps": -2.3
      }
    ]
  }
}
```
```json
std_msgs/Header header  # 标准消息头
usv_interfaces/PipelineTimestamp[] timestamps  # 时间戳
uint32 targets_num  # 目标列表
usv_interfaces/RadarNavTarget[] targets  # 目标列表
```

<a id="ref-1-06"></a>
#### 1-06 `property/radar_nav_map`
- 主题名称和 ROS 话题：`property/radar_nav_map` -> `/usv/radar/nav/map`
- 常量名称和实际话题名称：`MSG_TYPE_RADAR_NAV_MAP` -> `/sys/{product_id}/{device_id}/thing/property/radar_nav_map`
```json
{
  "timestamp": 1703123456789,
  "seq": 6,
  "data": {
    "map_id": "radar_local_001",
    "frame_id": "base_link",
    "width": 200,
    "height": 200,
    "resolution_m": 0.5,
    "origin": {
      "x": -50.0,
      "y": -50.0
    },
    "encoding": "rle",
    "cells_len": 100,
    "cells": "AAECAwQFBgc..."
  }
}
```
```json
std_msgs/Header header  # 标准消息头
string map_id  # 唯一标识
string frame_id  # 坐标系 ID
uint32 width  # 宽度
uint32 height  # 高度
float32 resolution_m  # resolution_m 字段含义
usv_interfaces/RadarNavMapOrigin origin  # origin 字段含义
string encoding  # encoding 字段含义
uint32 cells_len  # cells_len 字段含义
string cells  # cells 字段含义
```

<a id="ref-1-07"></a>
#### 1-07 `property/perception_trajectory`
- 主题名称和 ROS 话题：`property/perception_trajectory` -> `/usv/perception/trajectory`
- 常量名称和实际话题名称：`MSG_TYPE_PERCEPTION_TRAJECTORY` -> `/sys/{product_id}/{device_id}/thing/property/perception_trajectory`
```json
{
  "timestamp": 1703123456789,
  "seq": 7,
  "data": {
    "tra_num": 1,
    "trajectories": [
      {
        "track_id": 101,
        "object_type": "vehicle",
        "points": [
          {
            "lat": 31.1256789,
            "lon": 121.1256789,
            "timestamp": 1703123456000,
            "speed_mps": 5.2,
            "heading_deg": 90.0
          }
        ]
      }
    ]
  }
}
```
```json
std_msgs/Header header  # 标准消息头
uint32 tra_num  # tra_num 字段含义
usv_interfaces/PerceptionTrajectory[] trajectories  # 轨迹
```

<a id="ref-1-08"></a>
#### 1-08 `property/gps_status`
- 主题名称和 ROS 话题：`property/gps_status` -> `/usv/gps/status`
- 常量名称和实际话题名称：`MSG_TYPE_GPS_STATUS` -> `/sys/{product_id}/{device_id}/thing/property/gps_status`
```json
{
  "timestamp": 1703123456789,
  "seq": 8,
  "data": {
    "fix_type": 4,
    "satellites": 24,
    "hdop": 0.8,
    "vdop": 1.2,
    "pdop": 1.5,
    "diff_age": 0.5,
    "lat": 32.12345678,
    "lon": 118.1234567,
    "alt_m": 5.123,
    "heading_deg": 78.9,
    "ground_speed_mps": 2.4
  }
}
```
```json
std_msgs/Header header  # 标准消息头
uint8 fix_type  # 类型
uint8 satellites  # satellites 字段含义
float32 hdop  # hdop 字段含义
float32 vdop  # vdop 字段含义
float32 pdop  # pdop 字段含义
float32 diff_age  # diff_age 字段含义
float64 lat  # 纬度（度）
float64 lon  # 经度（度）
float32 alt_m  # 高度（米）
float32 heading_deg  # 航向角（度）
float32 ground_speed_mps  # 速度（米每秒）
```

<a id="ref-1-09"></a>
#### 1-09 `property/weather_status`
- 主题名称和 ROS 话题：`property/weather_status` -> `/usv/weather/status`
- 常量名称和实际话题名称：`MSG_TYPE_WEATHER_STATUS` -> `/sys/{product_id}/{device_id}/thing/property/weather_status`
```json
{
  "timestamp": 1703123456789,
  "seq": 9,
  "data": {
    "temp_c": 25.9,
    "humidity_percent": 67.1,
    "pressure_hpa": 1000.2,
    "wind_speed_mps": 3.5,
    "wind_direction_deg": 120.0
  }
}
```
```json
std_msgs/Header header  # 标准消息头
float32 temp_c  # 温度
float32 humidity_percent  # 标识
float32 pressure_hpa  # 压力
float32 wind_speed_mps  # 速度（米每秒）
float32 wind_direction_deg  # wind_direction_deg 字段含义
```

<a id="ref-1-10"></a>
#### 1-10 `property/depth_status`
- 主题名称和 ROS 话题：`property/depth_status` -> `/usv/depth/status`
- 常量名称和实际话题名称：`MSG_TYPE_DEPTH_STATUS` -> `/sys/{product_id}/{device_id}/thing/property/depth_status`
```json
{
  "timestamp": 1703123456789,
  "seq": 10,
  "data": {
    "position": {
      "lat": 30.1234567,
      "lon": 114.1234567,
      "alt_m": 0
    },
    "water_depth": {
      "depth_m": 12.37,
      "offset_m": 0.45,
      "confidence": 0.98
    }
  }
}
```
```json
std_msgs/Header header  # 标准消息头
usv_interfaces/DepthPosition position  # position 字段含义
usv_interfaces/WaterDepth water_depth  # 深度（米）
```

<a id="ref-1-11"></a>
#### 1-11 `property/battery_status`
- 主题名称和 ROS 话题：`property/battery_status` -> `/usv/battery/status`
- 常量名称和实际话题名称：`MSG_TYPE_BATTERY_STATUS` -> `/sys/{product_id}/{device_id}/thing/property/battery_status`
```json
{
  "timestamp": 1703123456789,
  "seq": 11,
  "data": {
    "battery_quantity": 3,
    "battery_info": [
      {
        "battery_id": 1,
        "battery_name": "main_battery",
        "current_a": 18.62,
        "voltage_v": 48.34,
        "power_w": 900.68
      },
      {
        "battery_id": 2,
        "battery_name": "core_battery",
        "current_a": 6.62,
        "voltage_v": 48.34,
        "power_w": 300.68
      },
      {
        "battery_id": 3,
        "battery_name": "power_battery",
        "current_a": 6.62,
        "voltage_v": 48.34,
        "power_w": 300.68
      }
    ]
  }
}
```
```json
std_msgs/Header header  # 标准消息头
uint32 battery_quantity  # 电池
usv_interfaces/BatteryInfo[] battery_info  # 电池
```

<a id="ref-1-12"></a>
#### 1-12 `property/fuel_status`
- 主题名称和 ROS 话题：`property/fuel_status` -> `/usv/fuel/status`
- 常量名称和实际话题名称：`MSG_TYPE_FUEL_STATUS` -> `/sys/{product_id}/{device_id}/thing/property/fuel_status`
```json
{
  "timestamp": 1703123456789,
  "seq": 12,
  "data": {
    "level_percent": 56,
    "volume_liter": 45,
    "capacity_liter": 60,
    "temperature_c": 23.9,
    "pressure_bar": 1.01
  }
}
```
```json
std_msgs/Header header  # 标准消息头
uint32 level_percent  # 速度
float32 volume_liter  # volume_liter 字段含义
float32 capacity_liter  # capacity_liter 字段含义
float32 temperature_c  # 温度（摄氏度）
float32 pressure_bar  # 压力
```

<a id="ref-1-13"></a>
#### 1-13 `property/mcu_status`
- 主题名称和 ROS 话题：`property/mcu_status` -> `/usv/mcu/status`
- 常量名称和实际话题名称：`MSG_TYPE_MCU_STATUS` -> `/sys/{product_id}/{device_id}/thing/property/mcu_status`
```json
{
  "timestamp": 1703123456789,
  "seq": 13,
  "data": {
    "version": "1.1.0",
    "uptime_s": 86400,
    "rssi_dbm": -68,
    "current_link": "5G",
    "gnss_status": "valid",
    "control_mode": "auto",
    "armed_status": "armed",
    "estop": false,
    "mqtt_online": true,
    "temp":26.5,
    "humi":85.0
  }
}
```
```json
std_msgs/Header header  # 标准消息头
string version  # version 字段含义
uint32 uptime_s  # 时间
int32 rssi_dbm  # rssi_dbm 字段含义
string current_link  # 电流（安）
string gnss_status  # 状态
string control_mode  # 控制量、模式值
string armed_status  # 状态
bool estop  # estop 字段含义
bool mqtt_online  # 在线状态
float32 temp_c  # 温度
float32 humi_percent  # humi_percent 字段含义
```

<a id="ref-1-14"></a>
#### 1-14 `property/ais`
- 主题名称和 ROS 话题：`property/ais` -> `/usv/ais/raw`
- 常量名称和实际话题名称：`MSG_TYPE_AIS` -> `/sys/{product_id}/{device_id}/thing/property/ais`
```json
{
  "timestamp": 1703123456789,
  "seq": 14,
  "data": {
    "ais_stream_num": 99,
    "ais_stream": "!AIVDM,1,1,,A,15Muq@?P00PD;88MD5MTDwwT0<0u,0*5C"
  }
}
```
```json
std_msgs/Header header  # 标准消息头
uint32 ais_stream_num  # AIS、视频流
string ais_stream  # AIS、视频流
```

<a id="ref-1-15"></a>
#### 1-15 `property/io_status`
- 主题名称和 ROS 话题：`property/io_status` -> `/usv/io/status`
- 常量名称和实际话题名称：`MSG_TYPE_IO_STATUS` -> `/sys/{product_id}/{device_id}/thing/property/io_status`
```json
{
  "timestamp": 1703123456789,
  "seq": 15,
  "data": {
    "devices_num": 8,
    "devices": [
      {
        "id": "light_left",
        "status": "on"
      },
      {
        "id": "light_right",
        "status": "on"
      },
      {
        "id": "light_mast",
        "status": "on"
      },
      {
        "id": "light_stern",
        "status": "on"
      },
      {
        "id": "light_signal",
        "status": "off"
      },
      {
        "id": "tilt_control",
        "status": "off"
      },
      {
        "id": "main_power",
        "status": "on"
      },
      {
        "id": "air_conditioner",
        "status": "on"
      }
    ]
  }
}
```
```json
std_msgs/Header header  # 标准消息头
uint32 devices_num  # 设备
usv_interfaces/IoDeviceStatus[] devices  # 设备
```

<a id="ref-2-01"></a>
#### 2-01 `event/jetson_heartbeat`
- 主题名称和 ROS 话题：`event/jetson_heartbeat` -> `/usv/monitor/heartbeat`
- 常量名称和实际话题名称：`MSG_TYPE_HEARTBEAT` -> `/sys/{product_id}/{device_id}/thing/event/jetson_heartbeat`
```json
{
  "timestamp": 1703123456789,
  "seq": 16,
  "data": {
    "online": true,
    "unit": "jetson"
  }
}
```
```json
std_msgs/Header header  #标准消息头（时间戳与坐标系）
bool online  #心跳在线状态
string unit  #心跳来源单元名称（如jetson/mcu）
bool armed_status  #解锁状态（true为已解锁）
string control_mode  #当前控制模式
```

<a id="ref-2-02"></a>
#### 2-02 `event/mcu_heartbeat`
- 主题名称和 ROS 话题：`event/mcu_heartbeat` -> `/usv/monitor/heartbeat`
- 常量名称和实际话题名称：`MSG_TYPE_MCU_HEARTBEAT` -> `/sys/{product_id}/{device_id}/thing/event/mcu_heartbeat`
```json
{
  "timestamp": 1703123456789,
  "seq": 16,
  "data": {
    "online": true,
    "unit": "mcu"
  }
}
```
```json
std_msgs/Header header  #标准消息头（时间戳与坐标系）
bool online  #心跳在线状态
string unit  #心跳来源单元名称（如jetson/mcu）
bool armed_status  #解锁状态（true为已解锁）
string control_mode  #当前控制模式
```

<a id="ref-2-03"></a>
#### 2-03 `event/alarm`
- 主题名称和 ROS 话题：`event/alarm` -> `/usv/monitor/alarm`
- 常量名称和实际话题名称：`MSG_TYPE_ALARM` -> `/sys/{product_id}/{device_id}/thing/event/alarm`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "event_id": "evt-001",
    "error_name": "SENSOR_AIS_FAIL",
    "error_level": "critical"
  }
}
```
```json
std_msgs/Header header  # 标准消息头
string event_id  # 唯一标识
string error_name  # 错误、名称
string error_level  # 错误、速度
```

<a id="ref-2-04"></a>
#### 2-04 `event/mission_delta`
- 主题名称和 ROS 话题：`event/mission_delta` -> `/usv/mission/delta`
- 常量名称和实际话题名称：`MSG_TYPE_MISSION_DELTA` -> `/sys/{product_id}/{device_id}/thing/event/mission_delta`
```json
{
  "timestamp": 1703123456789,
  "seq": 2,
  "data": {
    "mission_id": "M20250122_001",
    "operation": "update",
    "waypoint": {
      "index": 2,
      "lat": 31.1256789,
      "lon": 121.1256789,
      "radius_m": 5.0,
      "speed_mps": 4.0
    }
  }
}
```
```json
std_msgs/Header header  # 标准消息头
string mission_id  # 唯一标识
string operation  # operation 字段含义
uint32 waypoint_index  # 航点信息、索引号
float64 waypoint_lat  # 航点信息、纬度（度）
float64 waypoint_lon  # 航点信息、经度（度）
float32 waypoint_radius_m  # 航点信息、半径
float32 waypoint_speed_mps  # 航点信息、速度（米每秒）
```

<a id="ref-2-05"></a>
#### 2-05 `event/aivideo_status`
- 主题名称和 ROS 话题：`event/aivideo_status` -> `/usv/video/status`
- 常量名称和实际话题名称：`MSG_TYPE_AIVIDEO_STATUS` -> `/sys/{product_id}/{device_id}/thing/event/aivideo_status`
```json
{
  "timestamp": 1703123456789,
  "seq": 3,
  "data": {
    "streaming": true,
    "camera_id": "front",
    "url": "rtmp://push.example.com/live/boat001"
  }
}
```
```json
std_msgs/Header header  # 标准消息头
bool streaming  # 视频流
string camera_id  # 唯一标识
string url  # 流地址
```

<a id="ref-2-06"></a>
#### 2-06 `event/aivision_targets`
- 主题名称和 ROS 话题：`event/aivision_targets` -> `/usv/vision/targets`
- 常量名称和实际话题名称：`MSG_TYPE_VISION_TARGETS` -> `/sys/{product_id}/{device_id}/thing/event/aivision_targets`
```json
{
  "timestamp": 1703123456789,
  "seq": 4,
  "data": {
    "timestamps": [
      {
        "name": "image_capture",
        "time": 1703123456000
      },
      {
        "name": "preprocessing_start",
        "time": 1703123456100
      },
      {
        "name": "inference_end",
        "time": 1703123456780
      }
    ],
    "targets_num": 1,
    "targets": [
      {
        "class": "buoy",
        "confidence": 0.96,
        "bbox": {
          "x": 120,
          "y": 80,
          "width": 200,
          "height": 150
        },
        "rel_ang": 31.1257
      }
    ]
  }
}
```
```json
std_msgs/Header header  #标准消息头（时间戳与坐标系）
usv_interfaces/PipelineTimestamp[] timestamps  #算法流水线时间戳列表
uint32 targets_num  #目标数量
usv_interfaces/AIVisionTarget[] targets  #视觉目标数组
```

<a id="ref-2-07"></a>
#### 2-07 `event/diag_result`
- 主题名称和 ROS 话题：`event/diag_result` -> `/usv/diag/result`
- 常量名称和实际话题名称：`MSG_TYPE_DIAG_RESULT` -> `/sys/{product_id}/{device_id}/thing/event/diag_result`
```json
{
  "timestamp": 1703123456789,
  "seq": 6,
  "data": {
    "result": "pass",
    "modules": [
      {
        "name": "imu",
        "status": "pass",
        "message": ""
      },
      {
        "name": "gps",
        "status": "fail",
        "message": "RTK固定解未收敛"
      },
      {
        "name": "motor",
        "status": "pass",
        "message": ""
      }
    ],
    "summary": {
      "total": 3,
      "pass": 2,
      "fail": 1
    }
  }
}
```
```json
std_msgs/Header header  # 标准消息头
string result  # 执行结果
usv_interfaces/DiagModuleStatus[] modules  # 模块
usv_interfaces/DiagSummary summary  # summary 字段含义
```

<a id="ref-2-08"></a>
#### 2-08 `event/task_prog`
- 主题名称和 ROS 话题：`event/task_prog` -> `/usv/task/progress`
- 常量名称和实际话题名称：`MSG_TYPE_TASK_PROG` -> `/sys/{product_id}/{device_id}/thing/event/task_prog`
```json
{"mqtt_data_definition":{"task_id":"string","state":"uint8","progress_percent":"float","current_waypoint_index":"uint32","status_text":"string","error_code":"int32","message":"string","start_time_ms":"uint64","end_time_ms":"uint64"}}
```
```json
std_msgs/Header header  # 标准消息头

# 任务ID（来自 MQTT auto_task.task_id）
string task_id  # 唯一标识

# 任务状态机枚举
uint8 STATE_UNKNOWN=0  # 常量：状态值
uint8 STATE_ACCEPTED=1  # 常量：状态值、加速度
uint8 STATE_RUNNING=2  # 常量：状态值
uint8 STATE_PAUSED=3  # 常量：状态值
uint8 STATE_COMPLETED=4  # 常量：状态值
uint8 STATE_FAILED=5  # 常量：状态值
uint8 STATE_CANCELLED=6  # 常量：状态值
uint8 state  # 状态值

# 进度（0~100）
float32 progress_percent  # 进度（%）

# 当前航点索引（从0或1开始由实现约定；建议在文档中注明）
uint32 current_waypoint_index  # 电流（安）、航点信息、索引号

# 状态文本（用于上位机展示/日志）
string status_text  # 状态

# 错误信息（失败时填写）
int32 error_code  # 错误码
string message  # 消息说明

# 时间戳（毫秒，便于与 MQTT timestamp 对齐；为0表示未知/未设置）
uint64 start_time_ms  # 时间
uint64 end_time_ms  # 时间
```

<a id="ref-3-01"></a>
#### 3-01 `service/estop`
- 主题名称和 ROS 语义：`service/estop` -> `/usv/service/estop` (Request)
- 常量名称和实际话题名称：`MSG_TYPE_ESTOP` -> `/sys/{product_id}/{device_id}/thing/service/estop`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "estop": true,
    "src": "shore"
  }
}
```
```json
bool estop  # estop 字段含义
string source  # 数据来源
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-3-02"></a>
#### 3-02 `service/arm`
- 主题名称和 ROS 语义：`service/arm` -> `/usv/service/arm` (Request)
- 常量名称和实际话题名称：`MSG_TYPE_ARM` -> `/sys/{product_id}/{device_id}/thing/service/arm`
```json
{
  "timestamp": 1703123456789,
  "seq": 2,
  "data": {
    "armed": "arm"
  }
}
```
```json
string armed  # armed 字段含义
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-3-03"></a>
#### 3-03 `service/mode`
- 主题名称和 ROS 语义：`service/mode` -> `/usv/service/set_mode` (Request)
- 常量名称和实际话题名称：`MSG_TYPE_MODE` -> `/sys/{product_id}/{device_id}/thing/service/mode`
```json
{
  "timestamp": 1703123456789,
  "seq": 3,
  "data": {
    "mode": "auto"
  }
}
```
```json
string mode  # 模式值
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-3-04"></a>
#### 3-04 `service/manual_ctrl`
- 主题名称和 ROS 语义：`service/manual_ctrl` -> `/usv/service/manual_control` (Request)
- 常量名称和实际话题名称：`MSG_TYPE_MANUAL_CTRL` -> `/sys/{product_id}/{device_id}/thing/service/manual_ctrl`
```json
{
  "timestamp": 1703123456789,
  "seq": 4,
  "data": {
    "x": 500,
    "y": 0,
    "z": 0,
    "r": 0,
    "button": 64
  }
}
```
```json
int32 x  # X 坐标
int32 y  # Y 坐标
int32 z  # Z 坐标
int32 r  # r 字段含义
int32 button  # button 字段含义
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-3-05"></a>
#### 3-05 `service/auto_task`
- 主题名称和 ROS 语义：`service/auto_task` -> `/usv/task/execute_auto_task` (Goal)
- 常量名称和实际话题名称：`MSG_TYPE_AUTO_TASK` -> `/sys/{product_id}/{device_id}/thing/service/auto_task`
```json
{
  "timestamp": 1703123456789,
  "seq": 5,
  "data": {
    "cmd": "start",
    "task_id": "TASK_001",
    "waypoints_num": 2,
    "waypoints": [
      {
        "lat": 31.123456,
        "lon": 121.123456,
        "order": 1
      },
      {
        "lat": 31.123457,
        "lon": 121.123457,
        "order": 2
      }
    ],
    "mode": "auto"
  }
}
```
```json
# Goal
string task_id  #任务ID
string command  #任务命令（start/stop/pause/resume）
usv_interfaces/Waypoint[] waypoints  #任务航点列表
string mode  #执行模式
bool loop_execution  #是否循环执行
```

<a id="ref-3-06"></a>
#### 3-06 `service/params`
- 主题名称和 ROS 语义：`service/params` -> `/usv/service/set_params` (Request)
- 常量名称和实际话题名称：`MSG_TYPE_PARAMS` -> `/sys/{product_id}/{device_id}/thing/service/params`
```json
{
  "timestamp": 1703123456789,
  "seq": 6,
  "data": {
    "params": [
      {
        "name": "MAX_SPEED",
        "value": 5.2,
        "type": "float"
      },
      {
        "name": "SAFE_DISTANCE",
        "value": 10,
        "type": "int"
      }
    ]
  }
}
```
```json
string params_json  # params_json 字段含义
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-3-07"></a>
#### 3-07 `service/aivideo_ctrl`
- 主题名称和 ROS 语义：`service/aivideo_ctrl` -> `/usv/service/video_control` (Request)
- 常量名称和实际话题名称：`MSG_TYPE_AIVIDEO_CTRL` -> `/sys/{product_id}/{device_id}/thing/service/aivideo_ctrl`
```json
{
  "timestamp": 1703123456789,
  "seq": 7,
  "data": {
    "cmd": "start",
    "camera_id": "front",
    "resolution": "1920x1080",
    "fps": 30,
    "bitrate_kbps": 4096
  }
}
```
```json
bool streaming  # 视频流
string camera_id  # 唯一标识
string url  # 流地址
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-3-08"></a>
#### 3-08 `service/radar_nav_config`
- 主题名称和 ROS 语义：`service/radar_nav_config` -> `/usv/service/radar_nav_config` (Request)
- 常量名称和实际话题名称：`MSG_TYPE_RADAR_NAV_CONFIG` -> `/sys/{product_id}/{device_id}/thing/service/radar_nav_config`
```json
{
  "timestamp": 1703123456789,
  "seq": 10,
  "data": {
    "cmd": "get_config"
  }
}
```
```json
string cmd  # 控制指令
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
float32 angular_resolution_deg  # angular_resolution_deg 字段含义
float32 max_range_m  # 量程（米）
```

<a id="ref-3-09"></a>
#### 3-09 `service/io_ctrl`
- 主题名称和 ROS 语义：`service/io_ctrl` -> `/usv/service/io_control` (Request)
- 常量名称和实际话题名称：`MSG_TYPE_IO_CTRL` -> `/sys/{product_id}/{device_id}/thing/service/io_ctrl`
```json
{
  "timestamp": 1703123456789,
  "seq": 8,
  "data": {
    "devices": [
      {
        "id": "light_left",
        "action": "on"
      },
      {
        "id": "light_right",
        "action": "on"
      },
      {
        "id": "light_mast",
        "action": "off"
      },
      {
        "id": "light_stern",
        "action": "on"
      },
      {
        "id": "light_signal",
        "action": "off"
      },
      {
        "id": "tilt_control",
        "action": "off"
      },
      {
        "id": "main_power",
        "action": "on"
      },
      {
        "id": "air_conditioner",
        "action": "on"
      }
    ]
  }
}
```
```json
string id  # 唯一标识
string action  # action 字段含义
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-3-10"></a>
#### 3-10 `service/diag_request`
- 主题名称和 ROS 语义：`service/diag_request` -> `/usv/service/diag_request` (Request)
- 常量名称和实际话题名称：`MSG_TYPE_DIAG_REQUEST` -> `/sys/{product_id}/{device_id}/thing/service/diag_request`
```json
{
  "timestamp": 1703123456789,
  "seq": 9,
  "data": {
    "modules": [
      "all"
    ]
  }
}
```
```json
string[] modules  # 模块
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-4-01"></a>
#### 4-01 `service/estop_reply`
- 主题名称和 ROS 语义：`service/estop_reply` -> `/usv/service/estop` (Response)
- 常量名称和实际话题名称：`MSG_TYPE_ESTOP_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/estop_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "code": 200,
    "message": "success"
  }
}
```
```json
bool estop  # estop 字段含义
string source  # 数据来源
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-4-02"></a>
#### 4-02 `service/arm_reply`
- 主题名称和 ROS 语义：`service/arm_reply` -> `/usv/service/arm` (Response)
- 常量名称和实际话题名称：`MSG_TYPE_ARM_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/arm_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "code": 200,
    "message": "success"
  }
}
```
```json
string armed  # armed 字段含义
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-4-03"></a>
#### 4-03 `service/mode_reply`
- 主题名称和 ROS 语义：`service/mode_reply` -> `/usv/service/set_mode` (Response)
- 常量名称和实际话题名称：`MSG_TYPE_MODE_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/mode_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "code": 200,
    "message": "success"
  }
}
```
```json
string mode  # 模式值
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-4-04"></a>
#### 4-04 `service/manual_ctrl_reply`
- 主题名称和 ROS 语义：`service/manual_ctrl_reply` -> `/usv/service/manual_control` (Response)
- 常量名称和实际话题名称：`MSG_TYPE_MANUAL_CTRL_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/manual_ctrl_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "code": 200,
    "message": "success"
  }
}
```
```json
int32 x  # X 坐标
int32 y  # Y 坐标
int32 z  # Z 坐标
int32 r  # r 字段含义
int32 button  # button 字段含义
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-4-05"></a>
#### 4-05 `service/params_reply`
- 主题名称和 ROS 语义：`service/params_reply` -> `/usv/service/set_params` (Response)
- 常量名称和实际话题名称：`MSG_TYPE_PARAMS_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/params_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "code": 200,
    "message": "success"
  }
}
```
```json
string params_json  # params_json 字段含义
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-4-06"></a>
#### 4-06 `service/aivideo_ctrl_reply`
- 主题名称和 ROS 语义：`service/aivideo_ctrl_reply` -> `/usv/service/video_control` (Response)
- 常量名称和实际话题名称：`MSG_TYPE_AIVIDEO_CTRL_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/aivideo_ctrl_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "code": 200,
    "message": "success"
  }
}
```
```json
bool streaming  # 视频流
string camera_id  # 唯一标识
string url  # 流地址
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-4-07"></a>
#### 4-07 `service/radar_nav_config_reply`
- 主题名称和 ROS 语义：`service/radar_nav_config_reply` -> `/usv/service/radar_nav_config` (Response)
- 常量名称和实际话题名称：`MSG_TYPE_RADAR_NAV_CONFIG_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/radar_nav_config_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 5,
  "data": {
    "code": 200,
    "message": "success",
    "angular_resolution_deg": 0.9,
    "max_range_m": 200.0
  }
}
```
```json
string cmd  # 控制指令
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
float32 angular_resolution_deg  # angular_resolution_deg 字段含义
float32 max_range_m  # 量程（米）
```

<a id="ref-4-08"></a>
#### 4-08 `service/io_ctrl_reply`
- 主题名称和 ROS 语义：`service/io_ctrl_reply` -> `/usv/service/io_control` (Response)
- 常量名称和实际话题名称：`MSG_TYPE_IO_CTRL_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/io_ctrl_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "code": 200,
    "message": "success"
  }
}
```
```json
string id  # 唯一标识
string action  # action 字段含义
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-4-09"></a>
#### 4-09 `service/diag_request_reply`
- 主题名称和 ROS 语义：`service/diag_request_reply` -> `/usv/service/diag_request` (Response)
- 常量名称和实际话题名称：`MSG_TYPE_DIAG_REQUEST_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/diag_request_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "code": 200,
    "message": "success"
  }
}
```
```json
string[] modules  # 模块
---
bool success  # 是否成功
int32 code  # 状态码
string message  # 消息说明
```

<a id="ref-4-10"></a>
#### 4-10 `service/auto_task_reply`
- 主题名称和 ROS 语义：`service/auto_task_reply` -> `/usv/task/execute_auto_task` (Result)
- 常量名称和实际话题名称：`MSG_TYPE_AUTO_TASK_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/auto_task_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "code": 200,
    "message": "success"
  }
}
```
```json
# Result
bool success  #任务是否执行成功
int32 code  #结果码
uint8 final_state  #最终状态枚举值
string task_id  #任务ID
int32 error_code  #错误码
string message  #结果说明
```

<a id="ref-5-01"></a>
#### 5-01 `service/auto_task`
- 主题名称和 ROS 话题：`service/auto_task` -> `/usv/task/execute_auto_task` (Goal)
- 常量名称和实际话题名称：`MSG_TYPE_AUTO_TASK` -> `/sys/{product_id}/{device_id}/thing/service/auto_task`
```json
{
  "timestamp": 1703123456789,
  "seq": 5,
  "data": {
    "cmd": "start",
    "task_id": "TASK_001",
    "waypoints_num": 2,
    "waypoints": [
      {
        "lat": 31.123456,
        "lon": 121.123456,
        "order": 1
      },
      {
        "lat": 31.123457,
        "lon": 121.123457,
        "order": 2
      }
    ],
    "mode": "auto"
  }
}
```
```json
# Goal
string task_id  #任务ID
string command  #任务命令（start/stop/pause/resume）
usv_interfaces/Waypoint[] waypoints  #任务航点列表
string mode  #执行模式
bool loop_execution  #是否循环执行
```

<a id="ref-5-02"></a>
#### 5-02 `event/task_prog`
- 主题名称和 ROS 话题：`event/task_prog` -> `/usv/task/progress` (Feedback)
- 常量名称和实际话题名称：`MSG_TYPE_TASK_PROG` -> `/sys/{product_id}/{device_id}/thing/event/task_prog`
```json
{
  "timestamp": 1703123456789,
  "seq": 8,
  "data": {
    "task_id": "TASK_001",
    "state": 2,
    "progress_percent": 45.5,
    "current_waypoint_index": 1,
    "status_text": "running",
    "error_code": 0,
    "message": "任务执行中",
    "start_time_ms": 1703123400000,
    "end_time_ms": 0
  }
}
```
```json
std_msgs/Header header  # 标准消息头

# 任务ID（来自 MQTT auto_task.task_id）
string task_id  # 唯一标识

# 任务状态机枚举
uint8 STATE_UNKNOWN=0  # 常量：状态值
uint8 STATE_ACCEPTED=1  # 常量：状态值、加速度
uint8 STATE_RUNNING=2  # 常量：状态值
uint8 STATE_PAUSED=3  # 常量：状态值
uint8 STATE_COMPLETED=4  # 常量：状态值
uint8 STATE_FAILED=5  # 常量：状态值
uint8 STATE_CANCELLED=6  # 常量：状态值
uint8 state  # 状态值

# 进度（0~100）
float32 progress_percent  # 进度（%）

# 当前航点索引（从0或1开始由实现约定；建议在文档中注明）
uint32 current_waypoint_index  # 电流（安）、航点信息、索引号

# 状态文本（用于上位机展示/日志）
string status_text  # 状态

# 错误信息（失败时填写）
int32 error_code  # 错误码
string message  # 消息说明

# 时间戳（毫秒，便于与 MQTT timestamp 对齐；为0表示未知/未设置）
uint64 start_time_ms  # 时间
uint64 end_time_ms  # 时间
```

<a id="ref-5-03"></a>
#### 5-03 `service/auto_task_reply`
- 主题名称和 ROS 话题：`service/auto_task_reply` -> `/usv/task/execute_auto_task` (Result)
- 常量名称和实际话题名称：`MSG_TYPE_AUTO_TASK_REPLY` -> `/sys/{product_id}/{device_id}/thing/service/auto_task_reply`
```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "data": {
    "code": 200,
    "message": "success"
  }
}
```
```json
# Result
bool success  #任务是否执行成功
int32 code  #结果码
uint8 final_state  #最终状态枚举值
string task_id  #任务ID
int32 error_code  #错误码
string message  #结果说明
```


## 已对齐与未对齐汇总

### 已对齐（接口层）

- `usv_interfaces` 的 `msg/srv/action` 已可覆盖当前协议文档中列出的核心 MQTT 语义（含 `event/task_prog` 与 `service/auto_task` 全链路）。

### 未完全对齐（桥接层）

- 当前 bridge 已补齐所有“接口层已对齐但未接入”的 key；剩余工作主要是将具体业务节点发布/订阅映射从 `std_msgs/String` 逐步替换为强类型 `msg/srv/action`。

## 桥接侧下一步工作建议

1. 将下行输出从 `std_msgs/String` 逐步替换为 `usv_interfaces/srv` 或 `action` 调用。  
2. 把 `params.yaml` 中非空映射补齐到统一 ROS 话题命名（优先使用 `usv_interfaces/topics` 常量体系）。  
3. 为 `_reply`、`task_prog`、`mission_delta` 等关键链路补集成测试。  

## task 专项链路（约定）

- `service/auto_task` -> ROS Action Goal: `ExecuteAutoTask`
- `event/task_prog` <- ROS Action Feedback: `ExecuteAutoTask`
- `service/auto_task_reply` <- ROS Action Result: `ExecuteAutoTask`
