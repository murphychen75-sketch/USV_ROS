# usv_monitor 功能说明

`usv_monitor` 负责边缘端（Jetson）运行状态监测、飞控连通状态汇聚与心跳上报，并向 `usv_mqtt_bridge` 提供协议对齐的 JSON 输入。

## 1. 功能总览

- `system_status_node`
  - 高频采集主机资源状态（默认 5Hz）。
  - 发布 `usv_interfaces/msg/JetsonStatus`。
  - 同步发布 MQTT 上报 JSON（严格 6 字段）到 `/usv/monitor/status_jetson/json`。
- `heartbeat_node`
  - 使用 ROS Timer 1Hz 发布心跳。
  - 优先订阅 `/usv/state/autopilot`（由 `usv_mavlink_bridge` 产出）获得 `mcu` 在线态、解锁态、模式。
  - 发布 `usv_interfaces/msg/HeartbeatStatus` 到 `/usv/monitor/heartbeat`。
  - 同步发布 MQTT 心跳 JSON 到 `/usv/monitor/heartbeat/json`。
- `autopilot_control_service_node`
  - 提供统一前端服务 `/usv/control/autopilot`。
  - 将请求代理到后端服务 `/usv/mavlink/autopilot_control`（由 `usv_mavlink_bridge` 提供）。
- `alarm_watchdog_node`
  - 预留 watchdog 框架节点，当前仅发布占位状态，后续可扩展节点活性检查与告警策略。

## 2. 关键实现逻辑

### 2.1 Jetson 状态采集

- CPU、内存、磁盘、启动时长由 `psutil` 采集。
- GPU 利用率与温度优先使用 `jtop`；若不可用则自动降级：
  - GPU 使用率置为 `0.0`
  - 温度退化为 `psutil.sensors_temperatures` 结果（若可用）
- 采集值同时写入：
  - 强类型消息 `JetsonStatus`
  - JSON 包体：
    - `cpu_usage_percent`
    - `memory_usage_percent`
    - `gpu_usage_percent`
    - `temperature_c`
    - `uptime_ms`
    - `disk_usage_percent`

### 2.2 心跳与飞控状态汇聚

- `heartbeat_node` 每秒发布两类单元状态：
  - `{"online": true, "unit": "jetson"}`
  - `{"online": <connected>, "unit": "mcu", "armed_status": <bool>, "control_mode": "<mode>"}`
- `mcu` 状态来源：
  - 默认来自 `/usv/state/autopilot`（统一语义，推荐）
  - 可选兼容模式直连 `/mavros/state`

### 2.3 控制服务链路

- 前端业务调用：
  - `/usv/control/autopilot` (`usv_interfaces/srv/AutopilotControl`)
- monitor 服务节点仅做代理，不直接依赖 MAVROS：
  - 转发到 `/usv/mavlink/autopilot_control`
- 后端由 `usv_mavlink_bridge` 完成 `/mavros/cmd/arming`、`/mavros/set_mode` 调用。

## 3. 参数与启动

- 参数文件：`config/monitor_params.yaml`
- 启动文件：`launch/usv_monitor.launch.py`

启动命令：

```bash
ros2 launch usv_monitor usv_monitor.launch.py
```

## 4. 联调建议

建议启动顺序：

1. `usv_mavlink_bridge`（提供飞控状态与后端控制服务）
2. `usv_monitor`
3. `usv_mqtt_bridge`

关键观测话题：

- `/usv/state/autopilot`
- `/usv/monitor/jetson_status`
- `/usv/monitor/heartbeat`
- `/usv/monitor/status_jetson/json`
- `/usv/monitor/heartbeat/json`
