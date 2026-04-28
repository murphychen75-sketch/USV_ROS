# NEUXS 无人船通信协议 V1.1
| 修改时间                 | 修改内容                                                     |
| ------------------------ | ------------------------------------------------------------ |
| 2026-04-27 15:15 (UTC+8) | 文档首次发布，补充导航雷达相关协议（`radar/map`、`radar/control` 上下行，新增 `targets_num` 字段等），移除手动控制量链路。 |
| 2026-04-28               | 基于 `无人船通信协议V1.0_0427` 的 Topic 命名进行版本升级，并按 `mqtt_info` 对齐可迁移的话题定义。                                        |

## 1. 协议规范

### 1.1 基础信息

| 项目 | 规范 |
|------|------|
| 协议版本 | 1.1 |
| 传输协议 | MQTT 3.1.1 |
| 默认端口 | 1883 (TCP) / 8883 (TLS) |
| 数据编码 | UTF-8 |
| Payload 格式 | JSON |

### 1.2 Topic 规范（沿用 V1.0）

```
/sys/${productKey}/${deviceName}/thing/${type}/${identifier}
```

---

## 2. 话题架构


### 2.1 系统主题模板

| 类型 | 主题模板 | 方向 | 默认 QoS |
|------|----------|------|----------|
| 服务下发 | `/sys/${productKey}/${deviceName}/thing/service/${identifier}` | 云 → 设备 | 1 |
| 服务回复 | `/sys/${productKey}/${deviceName}/thing/service/${identifier}_reply` | 设备 → 云 | 1 |
| 事件上报 | `/sys/${productKey}/${deviceName}/thing/event/${identifier}` | 设备 → 云 | 1 |
| 事件回复 | `/sys/${productKey}/${deviceName}/thing/event/${identifier}_reply` | 云 → 设备 | 1 |
| 属性上报 | `/sys/${productKey}/${deviceName}/thing/property/${identifier}` | 设备 → 云 | 0 |
| 属性回复 | `/sys/${productKey}/${deviceName}/thing/property/${identifier}_reply` | 云 → 设备 | 0 |

### 2.2 Jetson 单元主题

#### 下行服务（云端 → Jetson）

| 主题 | 描述 | QoS |
|------|------|-----|
| `/sys/${productKey}/${deviceName}/thing/service/estop` | 急停指令 | 1 |
| `/sys/${productKey}/${deviceName}/thing/service/arm` | 解锁/上锁 | 1 |
| `/sys/${productKey}/${deviceName}/thing/service/mode` | 模式切换 | 1 |
| `/sys/${productKey}/${deviceName}/thing/service/manual_ctrl` | 手动控制指令 | 1 |
| `/sys/${productKey}/${deviceName}/thing/service/auto_task` | 自动任务指令 | 1 |
| `/sys/${productKey}/${deviceName}/thing/service/params` | 参数下发 | 1 |
| `/sys/${productKey}/${deviceName}/thing/service/video_ctrl` | 视频流控制 | 1 |
| `/sys/${productKey}/${deviceName}/thing/service/radar_scan_config` | 雷达配置查询 | 1 |

#### 上行事件（Jetson → 云端）

| 主题 | 描述 | 频率 | QoS |
|------|------|------|-----|
| `/sys/${productKey}/${deviceName}/thing/event/alarm` | 报警信息 | 实时 | 1 |
| `/sys/${productKey}/${deviceName}/thing/event/heartbeat` | 心跳包 | 1Hz | 0 |
| `/sys/${productKey}/${deviceName}/thing/event/mission_delta` | 航点信息更新 | 实时 | 1 |
| `/sys/${productKey}/${deviceName}/thing/event/video_status` | 视频流状态 | 实时 | 1 |
| `/sys/${productKey}/${deviceName}/thing/event/radar_scan_config_reply` | 雷达配置查询回复 | 实时 | 1 |
| `/sys/${productKey}/${deviceName}/thing/event/vision_targets` | 视觉识别目标 | 1-5Hz | 1 |

#### 上行属性（Jetson → 云端）

| 主题 | 描述 | 频率 | QoS |
|------|------|------|-----|
| `/sys/${productKey}/${deviceName}/thing/property/status_jetson` | Jetson 系统状态 | 中低频 | 0 |
| `/sys/${productKey}/${deviceName}/thing/property/motor` | 推进器数据 | 10Hz | 1 |
| `/sys/${productKey}/${deviceName}/thing/property/imu` | IMU 数据 | 20-50Hz | 0 |
| `/sys/${productKey}/${deviceName}/thing/property/radar` | 毫米波雷达数据 | 20Hz | 0 |
| `/sys/${productKey}/${deviceName}/thing/property/radar_scan` | 导航雷达扫描数据 | 1-2Hz | 0 |
| `/sys/${productKey}/${deviceName}/thing/property/radar_map` | 导航雷达地图 | 实时 | 1 |
| `/sys/${productKey}/${deviceName}/thing/property/perception_trajectory` | 融合感知轨迹 | 实时 | 0 |

### 2.3 MCU 单元主题

#### 下行服务（云端 → MCU）

| 主题 | 描述 | QoS |
|------|------|-----|
| `/sys/${productKey}/${deviceName}/thing/service/io_ctrl` | IO 设备控制 | 1 |
| `/sys/${productKey}/${deviceName}/thing/service/diag_request` | 自检请求 | 1 |

#### 上行属性（MCU → 云端）

| 主题 | 描述 | 频率 | QoS |
|------|------|------|-----|
| `/sys/${productKey}/${deviceName}/thing/property/status` | MCU 系统状态 | 1Hz | 0 |
| `/sys/${productKey}/${deviceName}/thing/property/gps` | GPS 定位数据 | 1-5Hz | 0 |
| `/sys/${productKey}/${deviceName}/thing/property/weather` | 气象站数据 | 1Hz | 1 |
| `/sys/${productKey}/${deviceName}/thing/property/depth` | 测深仪数据 | 1Hz | 1 |
| `/sys/${productKey}/${deviceName}/thing/property/battery` | 电池数据 | 1Hz | 1 |
| `/sys/${productKey}/${deviceName}/thing/property/fuel` | 油箱数据 | 1Hz | 1 |
| `/sys/${productKey}/${deviceName}/thing/property/io_status` | IO 设备状态 | 1Hz | 0 |
| `/sys/${productKey}/${deviceName}/thing/property/ais` | AIS 数据 | 1Hz | 0 |

#### 上行事件（MCU → 云端）

| 主题 | 描述 | 频率 | QoS |
|------|------|------|-----|
| `/sys/${productKey}/${deviceName}/thing/event/alarm` | 报警信息 | 实时 | 1 |
| `/sys/${productKey}/${deviceName}/thing/event/heartbeat` | 心跳包 | 1Hz | 0 |
| `/sys/${productKey}/${deviceName}/thing/event/diag_result` | 自检结果 | 实时 | 1 |

---

## 3. 下行数据格式（云端 → 设备）

### 3.1 通用服务回复格式

设备对服务指令的回复通过对应 `_reply` 主题发送：

```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "code": 200,
  "message": "success"
}
```

### 3.2 急停

**Topic:** `/sys/${productKey}/${deviceName}/thing/service/estop`

```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "estop": true,      // 是否紧急停止，true=停机，false=恢复
  "src": "shore"      // 来源端，例："shore"（岸端）
}
```

### 3.3 解锁/上锁

**Topic:** `/sys/${productKey}/${deviceName}/thing/service/arm`

```json
{
  "timestamp": 1703123456789,
  "seq": 2,
  "armed": "arm"      // "arm" 表示解锁，"disarm" 表示上锁
}
```

### 3.4 模式切换

**Topic:** `/sys/${productKey}/${deviceName}/thing/service/mode`

```json
{
  "timestamp": 1703123456789,
  "seq": 3,
  "mode": "auto"      // 切换目标模式
}
```

### 3.5 手动控制指令

**Topic:** `/sys/${productKey}/${deviceName}/thing/service/manual_ctrl`

```json
{
  "timestamp": 1703123456789,
  "seq": 4,
  "x": 1235,
  "y": 1235,
  "z": 1235,
  "r": 1235,
  "button": 64
}
```

| 参数 | 类型 | 范围 | 说明 |
|------|------|------|------|
| x | int | -1000~1000 | 前后方向 |
| y | int | -1000~1000 | 左右方向 |
| z | int | -1000~1000 | 垂直方向 |
| r | int | -1000~1000 | 旋转方向 |
| button | int | - | 按键位掩码 |

### 3.6 自动任务

**Topic:** `/sys/${productKey}/${deviceName}/thing/service/auto_task`

```json
{
  "timestamp": 1703123456789,
  "seq": 5,
  "cmd": "start",             // 任务操作："start"/"stop"
  "task_id": "TASK_001",      // 任务流水号
  "pointNumers": 2,           // 航点数量
  "waypoints": [
    { "lat": 31.123456, "lon": 121.123456, "order": 1 },
    { "lat": 31.123457, "lon": 121.123457, "order": 2 }
  ],
  "mode": "auto"              // 路径执行模式
}
```

### 3.7 参数下发

**Topic:** `/sys/${productKey}/${deviceName}/thing/service/params`

```json
{
  "timestamp": 1703123456789,
  "seq": 6,
  "params": [
    {"name": "MAX_SPEED", "value": 5.2, "type": "float"},
    {"name": "SAFE_DISTANCE", "value": 10, "type": "int"}
  ]
}
```

### 3.8 视频控制

**Topic:** `/sys/${productKey}/${deviceName}/thing/service/video_ctrl`

```json
{
  "timestamp": 1703123456789,
  "seq": 7,
  "cmd": "start",             // "start"/"stop"
  "camera_id": "front",       // 摄像头标识
  "resolution": "1920x1080",  // 分辨率
  "fps": 30,                  // 帧率
  "bitrate_kbps": 4096        // 码率（kbps）
}
```

### 3.9 IO 设备控制（MCU）

**Topic:** `/sys/${productKey}/${deviceName}/thing/service/io_ctrl`

```json
{
  "timestamp": 1703123456789,
  "seq": 8,
  "devices": [
    {"id": "light_left", "action": "on"},
    {"id": "light_right", "action": "on"},
    {"id": "light_mast", "action": "off"},
    {"id": "pwr_radar", "action": "on"}
  ]
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| id | string | 设备标识符（见设备清单） |
| action | string | on/off |

### 3.10 自检请求

**Topic:** `/sys/${productKey}/${deviceName}/thing/service/diag_request`

```json
{
  "timestamp": 1703123456789,
  "seq": 9,
  "modules": ["all"]         // 指定自检模块名数组，如 ["all"]
}
```

| modules 值 | 说明 |
|------------|------|
| all | 全部模块 |
| imu | IMU 模块 |
| gps | GPS 模块 |
| motor | 推进器模块 |
| battery | 电池模块 |
| comms | 通信模块 |

### 3.11 雷达配置查询（Jetson）

**Topic:** `/sys/${productKey}/${deviceName}/thing/service/radar_scan_config`

```json
{
  "timestamp": 1703123456789,
  "seq": 10,
  "cmd": "get_config"
}
```

---

## 4. 上行数据格式（设备 → 云端）

### 4.1 属性数据

#### 4.1.1 Jetson 状态

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/status_jetson`

```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "cpu_usage_percent": 42.5,     // CPU 占用率 %
  "memory_usage_percent": 68.3,  // 内存占用率 %
  "gpu_usage_percent": 27.8,     // GPU 占用率 %
  "temperature_c": 72.4,         // 温度(摄氏度)
  "uptime_ms": 86400000,         // 上电时长（毫秒）
  "disk_usage_percent": 55.2     // 磁盘占用率 %
}
```

#### 4.1.2 推进器数据

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/motor`

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

| 参数 | 类型 | 说明 |
|------|------|------|
| motor_id | int | 推进器标识 |
| ts | int | 推进器原始时间戳 |
| rpm | int | 实际转速（转/分钟） |
| angle | int | 推进器角度 |
| power_w | float | 实时功率 |

#### 4.1.3 IMU 数据

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/imu`

```json
{
  "timestamp": 1703123456789,
  "seq": 3,
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
```

#### 4.1.4 毫米波雷达数据

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/radar`

```json
{
  "timestamp": 1703123456789,
  "seq": 4,
  "data": {
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

#### 4.1.5 雷达扫描

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/radar_scan`

```json
{
  "timestamp": 1703123456789,
  "seq": 5,
  "timestamps": [
    { "name": "scan_start", "time": 1703123456000 },
    { "name": "scan_end", "time": 1703123456700 },
    { "name": "signal_processing_end", "time": 1703123456789 }
  ],                              // 流程各时间戳
  "targets_num": 2,               // 目标数量
  "targets": [
    { "range_m": 45.2, "bearing_deg": 32.5, "intensity": 0.92, "velocity_mps": 6.8 },
    { "range_m": 78.0, "bearing_deg": 120.3, "intensity": 0.45, "velocity_mps": -2.3 }
  ]                               // 追踪目标列表
}
```

#### 4.1.6 雷达地图

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/radar_map`

```json
{
  "timestamp": 1703123456789,
  "seq": 6,
  "map_id": "radar_local_001",     // 地图编号
  "frame_id": "base_link",         // 坐标系
  "width": 200,                    // 栅格宽度
  "height": 200,                   // 栅格高度
  "resolution_m": 0.5,             // 栅格分辨率（米/格）
  "origin": { "x": -50.0, "y": -50.0 }, // 原点位置
  "encoding": "rle",               // 数据编码方式: "raw"/"rle"
  "cells": "AAECAwQFBgc..."         // 栅格数据（可压缩后字符串）
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| map_id | string | 地图编号 |
| frame_id | string | 坐标系 |
| width | int | 栅格宽度 |
| height | int | 栅格高度 |
| resolution_m | float | 栅格分辨率（米/格） |
| origin | object | 原点位置 |
| encoding | string | 数据编码方式：raw/rle |
| cells | string | 栅格数据（可压缩后字符串） |

#### 4.1.7 融合轨迹

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/perception_trajectory`

```json
{
  "timestamp": 1703123456789,
  "seq": 7,
  "tra_num":1,
  "trajectories": [
    {
      "track_id": 101,                     // 目标跟踪ID
      "object_type": "vehicle",            // 目标类型
      "points": [
        {
          "lat": 31.12567890,
          "lon": 121.12567890,
          "timestamp": 1703123456000,
          "speed_mps": 5.2,
          "heading_deg": 90.0
        }
      ]       // 轨迹点集
    }
  ]
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| track_id | int | 目标跟踪ID |
| object_type | string | 目标类型（vehicle/pedestrian/buoy/obstacle/unknown） |
| points | array | 轨迹点集 |

#### 4.1.8 GPS 数据（MCU）

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/gps`

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

| fix_type | 说明 |
|----------|------|
| 0 | 无效解 |
| 1 | 单点定位 |
| 2 | 伪距差分 |
| 4 | RTK 固定解 |
| 5 | RTK 浮点解 |

#### 4.1.9 气象数据（MCU）

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/weather`

```json
{
  "timestamp": 1703123456789,
  "seq": 9,
  "temp": 25.9,               // 温度(°C)
  "humidity": 67.1,           // 湿度(%)
  "pressure": 1000.2,         // 气压(hPa)
  "wind_speed": 3.5,          // 风速(m/s)
  "wind_direction": 120.0     // 风向(度)
}
```

#### 4.1.10 测深数据（MCU）

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/depth`

```json
{
  "timestamp": 1703123456789,
  "seq": 10,
  "position": {
    "lat": 30.1234567,      // 纬度
    "lon": 114.1234567,     // 经度
    "alt": null             // 高程，可为null
  },
  "water_depth": {
    "depth_m": 12.37,       // 水深(米)
    "offset_m": 0.45,       // 偏移(米)
    "confidence": 0.98      // 置信度
  }
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| depth_m | float | 相对于换能器的水深 |
| offset_m | float | 吃水深度 |
| confidence | float | 置信度 |

#### 4.1.11 电池数据（MCU）

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/battery`

```json
{
  "timestamp": 1703123456789,
  "seq": 11,
  "data": {
    "battery_quantity": 3,
    "battery_info": [
      {"battery_id": 1, "battery_name": "main_battery", "current_a": 18.62, "voltage_v": 48.34, "power_w": 900.68},
      {"battery_id": 2, "battery_name": "core_battery", "current_a": 6.62, "voltage_v": 48.34, "power_w": 300.68},
      {"battery_id": 3, "battery_name": "power_battery", "current_a": 6.62, "voltage_v": 48.34, "power_w": 300.68}
    ]
  }
}
```

#### 4.1.12 油箱数据（MCU）

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/fuel`

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

#### 4.1.13 核心状态（MCU）

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/status`

```json
{
  "timestamp": 1703123456789,
  "seq": 13,
  "version": "1.1.0",            // 协议版本
  "uptime": 86400,               // 上电时长（秒）
  "rssi": -68,                   // 信号强度
  "current_link": "5G",          // 当前链路
  "gnss_status": "valid",        // GNSS 状态
  "control_mode": "auto",        // 当前模式
  "armed_status": "armed",       // 解锁状态
  "estop": false,                // 是否急停
  "mqtt_online": true            // MQTT 是否在线
}
```

#### 4.1.14 AIS 数据（MCU）

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/ais`

```json
{
  "timestamp": 1703123456789,
  "seq": 14,
  "data": "$GNRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
}
```

#### 4.1.15 IO 设备状态（MCU）

**Topic:** `/sys/${productKey}/${deviceName}/thing/property/io_status`

```json
{
  "timestamp": 1703123456789,
  "seq": 15,
  "devices": [
    {"id": "light_left", "status": "on"},
    {"id": "light_right", "status": "on"},
    {"id": "light_mast", "status": "on"},
    {"id": "light_stern", "status": "on"},
    {"id": "light_signal", "status": "off"},
    {"id": "tilt_control", "status": "off"},
    {"id": "main_power", "status": "on"},
    {"id": "air_conditioner", "status": "on"}
  ]
}
```

#### 4.1.16 心跳状态

**Topic:** `/sys/${productKey}/${deviceName}/thing/event/heartbeat`

**Jetson 心跳：**
```json
{
  "timestamp": 1703123456789,
  "seq": 16,
  "online": true,
  "unit": "jetson"
}
```

**MCU 心跳：**
```json
{
  "timestamp": 1703123456789,
  "seq": 16,
  "online": true,
  "unit": "mcu"
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| online | bool | 在线状态 |
| unit | string | 单元标识：jetson/mcu |

### 4.2 事件数据

#### 4.2.1 报警

**Topic:** `/sys/${productKey}/${deviceName}/thing/event/alarm`

```json
{
  "timestamp": 1703123456789,
  "seq": 1,
  "event_id": "evt-001",             // 事件ID
  "error_name": "SENSOR_AIS_FAIL",   // 故障名
  "error_level": "critical"          // 故障等级
}
```

#### 4.2.2 航点信息更新

**Topic:** `/sys/${productKey}/${deviceName}/thing/event/mission_delta`

```json
{
  "timestamp": 1703123456789,
  "seq": 2,
  "mission_id": "M20250122_001",
  "operation": "update",
  "waypoint": {
    "index": 2,
    "lat": 31.12567890,
    "lon": 121.12567890,
    "radius_m": 5.0,
    "speed_mps": 4.0
  }
}
```

#### 4.2.3 视频流状态

**Topic:** `/sys/${productKey}/${deviceName}/thing/event/video_status`

```json
{
  "timestamp": 1703123456789,
  "seq": 3,
  "streaming": true,
  "camera_id": "front",
  "url": "rtmp://push.example.com/live/boat001"
}
```

#### 4.2.4 视觉目标

**Topic:** `/sys/${productKey}/${deviceName}/thing/event/vision_targets`

```json
{
  "timestamp": 1703123456789,
  "seq": 4,
  "timestamps": [
    { "name": "image_capture", "time": 1703123456000 },
    { "name": "preprocessing_start", "time": 1703123456100 },
    { "name": "inference_end", "time": 1703123456780 }
  ],                              // 处理流程主要时间戳
  "targets_num": 1,               // 目标数量
  "targets": [
    {
      "class": "buoy",
      "confidence": 0.96,
      "bbox": { "x": 120, "y": 80, "width": 200, "height": 150 },
      "rel_ang": 31.1257
    }
  ]                               // 检测目标列表
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| timestamps | array | 处理流程各阶段时间戳 |
| targets_num | int | 目标数量 |
| targets | array | 检测目标列表 |
| class | string | 目标类别（buoy/ship/boat/obstacle/person） |
| confidence | float | 置信度（0-1） |
| bbox | object | 边界框（x,y,width,height） |
| rel_ang | float | 相对角度（度） |

#### 4.2.5 雷达配置查询回复

**Topic:** `/sys/${productKey}/${deviceName}/thing/event/radar_scan_config_reply`

```json
{
  "timestamp": 1703123456789,
  "seq": 5,
  "angular_resolution_deg": 0.9,
  "max_range_m": 200.0
}
```

#### 4.2.6 自检结果（MCU）

**Topic:** `/sys/${productKey}/${deviceName}/thing/event/diag_result`

```json
{
  "timestamp": 1703123456789,
  "seq": 6,
  "result": "pass",
  "modules": [
    {"name": "imu", "status": "pass", "message": ""},
    {"name": "gps", "status": "fail", "message": "RTK固定解未收敛"},
    {"name": "motor", "status": "pass", "message": ""}
  ],
  "summary": {
    "total": 3,
    "pass": 2,
    "fail": 1
  }
}
```

---

## 5. 设备清单

### 5.1 IO 设备清单（MCU）

| 分类 | 设备名称 | 设备 ID | 类型 |
|------|----------|---------|------|
| 航行灯 | 左舷灯 | light_left | relay |
| 航行灯 | 右舷灯 | light_right | relay |
| 航行灯 | 前舷灯 | light_front | relay |
| 航行灯 | 后舷灯 | light_back | relay |
| 航行灯 | 桅灯 | light_mast | relay |
| 航行灯 | 尾灯 | light_stern | relay |
| 航行灯 | 告警灯 | light_signal | relay |
| 设备电源 | 毫米波雷达 | pwr_radar | relay |
| 设备电源 | 气象站 | pwr_weather | relay |
| 设备电源 | 测深仪 | pwr_depth | relay |
| 设备电源 | 水泵 | pump | relay |
| 执行机构 | 发动机起翘 | tilt_control | relay |
| 执行机构 | 主电源开关 | main_power | relay |
| 执行机构 | 空调开关 | air_conditioner | relay |
| 执行机构 | 执行电机 | execution_motor | pwm |

### 5.2 对象类型定义

| object_type | 说明 |
|-------------|------|
| vehicle | 船舶/车辆 |
| pedestrian | 行人 |
| buoy | 浮标 |
| obstacle | 障碍物 |
| unknown | 未知类型 |

### 5.3 视觉目标类别定义

| class | 说明 |
|-------|------|
| boat | 船只 |
| ship | 船舶 |
| buoy | 浮标 |
| obstacle | 障碍物 |
| person | 人员 |

---

## 6. 附录

### 6.1 错误码定义

| Code | 说明 |
|------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 401 | 认证失败 |
| 404 | 资源不存在 |
| 408 | 请求超时 |
| 429 | 请求过于频繁 |
| 500 | 服务内部错误 |
| 503 | 服务不可用 |

### 6.2 通信频率建议

| 数据类型 | 建议频率 | QoS |
|----------|----------|-----|
| IMU 数据 | 20-50 Hz | 0 |
| GPS 数据 | 1-5 Hz | 0 |
| 推进器数据 | 10 Hz | 1 |
| 电池/燃料数据 | 1 Hz | 1 |
| 气象站数据 | 1 Hz | 1 |
| 视觉识别目标 | 1-5 Hz | 1 |
| 雷达扫描数据 | 1-2 Hz | 0 |
| 雷达地图数据 | 实时 | 1 |
| 感知轨迹数据 | 实时 | 0 |
| 报警事件 | 触发时立即上报 | 1 |
| 心跳状态 | 1 Hz | 0 |

### 6.3 MQTT 配置建议

| 配置项 | 建议值 |
|--------|--------|
| Keep Alive | 60 秒 |
| Clean Session | false |
| QoS 0 | 高频、允许少量丢失的数据 |
| QoS 1 | 控制指令和告警 |

---

