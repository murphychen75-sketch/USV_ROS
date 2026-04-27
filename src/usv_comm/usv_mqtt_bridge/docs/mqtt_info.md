# MQTT 通信协议说明（mqtt_info）

## 文档修改登记

| 修改时间 | 修改内容 |
| --- | --- |
| 2026-04-27 15:15 (UTC+8) | 文档首次发布,补充导航雷达相关协议（`radar/map`、`radar/control` 上下行、`targets_num` 字段等），移除手动控制量链路。 |

## 协议约束与公共头

1. Topic 命名空间约束

基础格式: /{pid}/{vid}/{uid}/<msg_type>

字段说明:

{pid}: 产品 ID (如 M10)
{vid}: 设备 ID (如 USV_N0001)
{uid}: 核心节点 ID (如 MCU01, JETSON01)

2. JSON 公共信封结构
所有具体业务数据必须封装在 payload 节点内部。公共头定义如下：
```json
{
  "timestamp": 1714205910000,
  "seq": 10024,
  "device_id": "USV_N0001",
  "msg_type": "estop",
  "payload": {
     // 具体业务数据结构放置于此
  }
}
```
| 参数      | 值          | 描述         | 数据类型 | 备注               |
| --------- | ----------- | ------------ | -------- | ------------------ |
| timestamp | 1714205910000 | Unix 毫秒时间戳 | int      |                    |
| seq       | 10024       | 序列号       | int      | 用于云端计算丢包率 |
| device_id | USV_N0001   | 设备 ID       | string   | 防止数据脱离 Topic 后在云端落盘发生错乱 |
| msg_type  | estop       | 业务类型     | string   | 指引云端网关极速分发 |


## 二、 核心通信矩阵汇总
1. 下行消息（云端 -> USV）

| 消息类型 (msg_type)    | 功能模块     | 频率     | QoS | 描述                                       |
|------------------------|-------------|----------|-----|----------------------------------------------|
| estop                  | 紧急停止     | 事件     | 1   | 触发或解除紧急停机状态                     |
| arm                    | 解锁/上锁    | 事件     | 1   | 动力系统的软解锁或上锁                     |
| mode                   | 模式切换     | 事件     | 1   | 切换航行模式 (manual/auto/hold/rtl/berth)  |
| auto/task              | 自动任务     | 事件     | 1   | 下发航点任务及启停指令                     |
| radar/control          | 导航雷达控制 | 事件     | 1   | 雷达启停、扫描参数与工作模式控制           |
| video/ctrl             | 视频流控制   | 事件     | 1   | 远程控制视频流的开启/关闭与参数调整         |
| diag/request           | 自检请求     | 事件     | 1   | 触发系统硬件自检                           |

2. 上行消息（USV -> 云端）

| 消息类型 (msg_type)      | 功能模块         | 频率     | QoS | 描述                                       |
|-------------------------|------------------|----------|-----|--------------------------------------------|
| status                  | 核心状态         | 中低频   | 0   | MCU状态、信号、航行/解锁状态               |
| status/jetson           | 边缘状态         | 中低频   | 0   | Jetson CPU/内存/GPU占用率及温度            |
| heartbeat               | 心跳包           | 1Hz      | 1   | 确认桥接节点在线                           |
| alarm                   | 告警信息         | 事件     | 1   | 各级别故障上报及故障码                     |
| diag/result             | 自检结果         | 事件     | 1   | 响应自检请求，反馈模块通过状态             |
| radar/control           | 雷达控制回执     | 事件     | 1   | 雷达控制指令执行结果与当前状态             |
| radar/scan              | 雷达目标         | 高频     | 0   | 多时间戳的雷达追踪目标列表                 |
| radar/scan_config       | 雷达扫描配置     | 低频     | 1   | 雷达扫描参数配置上报                       |
| radar/map               | 导航雷达地图     | 中频     | 1   | 局部占据栅格/代价图信息上报                |
| vision/targets          | 视觉目标         | 高频     | 1   | 多时间戳的视觉识别目标及bbox               |
| perception/trajectory   | 融合轨迹         | 实时     | 0   | 算法处理后的障碍物历史运动轨迹             |
| depth                   | 测深数据         | 中低频   | 1   | 测深仪水深数据                             |
| weather                 | 气象数据         | 中低频   | 1   | 风速、风向、温湿度气压数据                 |



## 三、下行指令 Payload 定义

1. 紧急停止 (estop)
```json
{
    "estop": true,      // 是否紧急停止，true=停机，false=恢复
    "src": "shore"      // 来源端，例："shore"（岸端）
}
```

2. 解锁/上锁 (arm)
```json
{
    "armed": "arm"      // "arm" 表示解锁，"disarm" 表示上锁
}
```

3. 模式切换 (mode)
> 支持的值: manual（手动）, auto（自动）, hold（悬停）, rtl（返航）, berth（靠泊）
```json
{
    "mode": "auto"      // 切换目标模式
}
```

4. 自动任务下发 (auto/task)
```json
{
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

5. 导航雷达控制 (radar/control)
```json
{
    "cmd": "start_scan",            // 指令类型: "start_scan"/"stop_scan"/"set_mode"/"set_config"
    "mode": "navigation",           // 雷达模式: "navigation"/"tracking"/"standby"
    "scan_config": {
        "angular_resolution_deg": 0.9,
        "max_range_m": 200.0,
        "scan_rate_hz": 10.0
    },
    "source": "shore"               // 指令来源
}
```

6. 视频推流控制 (video/ctrl)
```json
{
    "cmd": "start",             // "start"/"stop"
    "camera_id": "front",       // 摄像头标识
    "resolution": "1920x1080",  // 分辨率
    "fps": 30,                  // 帧率
    "bitrate_kbps": 4096        // 码率（kbps）
}
```

7. 自检请求 (diag/request) 这部分有待补充,本次测试不体现
```json
{
    "modules": ["all"]         // 指定自检模块名数组，如 ["all"]
}
```

## 四、上行遥测 Payload 定义

1. 系统核心状态 (status)
```json
{
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

2. 边缘计算状态 (status/jetson)
```json
{
    "cpu_usage_percent": 42.5,     // CPU 占用率 %
    "memory_usage_percent": 68.3,  // 内存占用率 %
    "gpu_usage_percent": 27.8,     // GPU 占用率 %
    "temperature_c": 72.4,         // 温度(摄氏度)
    "uptime_ms": 86400000,         // 上电时长（毫秒）
    "disk_usage_percent": 55.2     // 磁盘占用率 %
}
```

3. 心跳维持 (heartbeat)
```json
{
    "mcu_online": true             // MCU 是否在线
}
```

4. 故障告警 (alarm)
> 故障等级 (error_level): fatal, critical, warning, info
```json
{
    "event_id": "evt-001",         // 事件ID
    "error_name": "SENSOR_AIS_FAIL",   // 故障名
    "error_level": "critical"      // 故障等级
}
```

5. 导航雷达控制回执 (radar/control)
```json
{
    "cmd": "set_config",            // 回执对应的控制指令
    "result": "ok",                 // 执行结果: "ok"/"failed"
    "reason": "",                   // 失败原因，成功可为空
    "mode": "navigation",           // 当前生效模式
    "scan_config": {
        "angular_resolution_deg": 0.9,
        "max_range_m": 200.0,
        "scan_rate_hz": 10.0
    }
}
```

6. 毫米波雷达追踪目标 (radar/scan)
```json
{
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

7. 毫米波雷达扫描配置 (radar/scan_config)
```json
{
    "angular_resolution_deg": 0.9,  // 角分辨率
    "max_range_m": 200.0            // 最大探测距离（米）
}
```

8. 导航雷达地图 (radar/map)
```json
{
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

9. 视觉识别目标 (vision/targets)
```json
{
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

10. 融合感知轨迹 (perception/trajectory)
```json
{
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

11. 辅助传感：水深与气象 (depth & weather)

depth Payload:
```json
{
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

weather Payload:
```json
{
    "temp": 25.9,               // 温度(°C)
    "humidity": 67.1,           // 湿度(%)
    "pressure": 1000.2,         // 气压(hPa)
    "wind_speed": 3.5,          // 风速(m/s)
    "wind_direction": 120.0     // 风向(度)
}
```
