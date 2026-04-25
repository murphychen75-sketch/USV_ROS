# USV MQTT Bridge

一个基于 `ROS 2 Python + paho-mqtt` 的轻量桥接节点，用于把 USV 内部 ROS 2 主题转换为 MQTT 上行遥测，并把云端 MQTT 下行消息转发回 ROS 2。

## 包定位

`usv_mqtt_bridge` 位于 `src/usv_comm/` 通信层，负责外部 MQTT 协议适配，不承担项目内部接口定义。内部统一语义接口由 `src/usv_interfaces/` 提供。

## 节点组成

当前 MQTT 节点由以下几个部分组成：

- `launch/usv_mqtt_bridge.launch.py`
  - 节点启动入口，负责加载参数文件并启动 `usv_mqtt_bridge_node`。
- `config/params.yaml`
  - 运行参数配置，包含 Broker 地址、`client_id`、重连参数、发布频率、ROS 2 topic 和 MQTT topic 映射。
- `usv_mqtt_bridge/node.py`
  - 主节点逻辑，负责创建 ROS 2 订阅器/发布器，接收上行数据并转发到 MQTT，同时接收 MQTT 下行消息并分发回 ROS 2。
- `usv_mqtt_bridge/mqtt_client.py`
  - MQTT 传输层封装，负责连接 Broker、LWT 设置、订阅、发布、断线检测和指数退避重连。
- `usv_mqtt_bridge/serializers.py`
  - 消息封装与 JSON 序列化工具，负责统一 envelope 格式、时间戳补齐和下行消息解析。
- `usv_mqtt_bridge/protocol.py`
  - 协议定义层，维护 topic 命名、QoS、消息类型和允许字段。
- `usv_mqtt_bridge/throttlers.py`
  - 节流控制模块，用于限制 `state`、`vision`、`radar` 的上云频率。
- `usv_mqtt_bridge/command_dispatcher.py`
  - 下行消息分发模块，负责校验 `control/config` 消息并转发为 ROS 2 侧输出。
- `docs/message_contract.md`
  - 说明 MQTT 外发消息格式、内部接口话题以及字段/结构映射关系。
- `scripts/publish_state_test.py`
  - 状态上报测试脚本，用于向 `/usv/state` 持续发布模拟数据，验证桥接链路。

## 功能概览

- 上行主题：
  - `usv/{device_id}/telemetry/state`
  - `usv/{device_id}/telemetry/vision`
  - `usv/{device_id}/telemetry/radar`
- 下行主题：
  - `usv/{device_id}/cmd/control`
  - `usv/{device_id}/cmd/config`
- 在线状态：
  - `usv/{device_id}/status/lwt`

默认使用统一 JSON 包装格式：

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

## ROS 2 接口

当前实现默认使用 `std_msgs/String` 作为 ROS 2 接口消息类型，消息体内容为 JSON 字符串：

- 订阅：
  - `/usv/state`
  - `/usv/vision/metadata`
  - `/usv/radar/targets`
- 发布：
  - `/usv/cmd/control/raw`
  - `/usv/cmd/config/raw`

如果内部算法已经输出了完整 envelope，节点会复用其中的 `timestamps`；如果只输出纯 payload，节点会补齐 `gateway_publish_time`。

## 现有功能

当前代码已经具备以下能力：

- 支持 ROS 2 到 MQTT 的上行桥接：
  - `/usv/state` -> `usv/{device_id}/telemetry/state`
  - `/usv/vision/metadata` -> `usv/{device_id}/telemetry/vision`
  - `/usv/radar/targets` -> `usv/{device_id}/telemetry/radar`
- 支持 MQTT 到 ROS 2 的下行桥接：
  - `usv/{device_id}/cmd/control` -> `/usv/cmd/control/raw`
  - `usv/{device_id}/cmd/config` -> `/usv/cmd/config/raw`
- 支持统一 JSON envelope：
  - 消息包含 `timestamps`、`device_id`、`msg_type`、`seq`、`payload`
  - 支持补齐 `gateway_publish_time`
- 支持 topic 规范和 QoS 约定：
  - `telemetry/*` 使用 `QoS 0`
  - `cmd/*` 使用 `QoS 1`
  - `status/lwt` 使用 `QoS 1 + retain`
- 支持 MQTT 连接管理：
  - 建立长连接
  - 自动订阅下行 topic
  - 设置 LWT 在线/离线消息
  - 断线后指数退避重连
- 支持上行节流：
  - `state`、`vision`、`radar` 可按参数配置频率限制发送
- 支持基础下行配置热更新：
  - `state_rate_hz`
  - `vision_rate_hz`
  - `radar_rate_hz`
  - `radar_safe_distance_m`（当前仅转发和记录日志）
- 支持基础测试：
  - 单元测试覆盖协议、序列化、节流、下行分发和重连退避逻辑
  - 提供 `/usv/state` 测试发布脚本

## 待开发功能

当前版本已经可以用于基础联调，但还有一些功能建议继续完善：

- 将 ROS 2 接口从 `std_msgs/String` 升级为强类型自定义 `.msg`
  - 便于字段约束、类型检查和多模块协作
- 完善 `vision` 和 `radar` 的测试脚本
  - 当前只提供了 `state` 上行测试脚本
- 增强 MQTT 连接配置
  - 支持 TLS
  - 支持证书认证
  - 支持更明确的连接错误码和日志说明
- 优化 `client_id` 管理
  - 提供自动生成唯一 `client_id` 的能力，避免公共 Broker 上冲突
- 增强下行 `config` 的运行时生效范围
  - 当前主要支持上报频率更新
  - 后续可扩展到更多运行参数
- 支持更完整的可靠性与观测能力
  - 心跳 topic
  - 发布/重连状态统计
  - 更细粒度日志级别控制
- 支持更完善的联调与集成测试
  - 基于真实 Broker 的自动化测试
  - 上下行闭环测试
  - LWT 和断线恢复场景测试
- 评估 `vision/radar` 切换到 Protobuf 的方案
  - 当目标列表增大时降低消息体积和公网带宽压力

## 运行方式

1. 安装依赖：

```bash
pip install paho-mqtt
```

2. 在 ROS 2 工作区构建：

```bash
colcon build --packages-select usv_mqtt_bridge
```

3. 启动节点：

```bash
ros2 launch usv_mqtt_bridge usv_mqtt_bridge.launch.py
```

4. 发布测试状态数据：

```bash
ros2 topic pub /usv/state std_msgs/msg/String '{data: "{\"battery_pct\": 90, \"lat\": 31.2, \"lon\": 121.5, \"heading_deg\": 10.0, \"speed_mps\": 1.2}"}'
```

5. 订阅 MQTT 状态主题：

```bash
mosquitto_sub -h 127.0.0.1 -t 'usv/001/telemetry/state'
```

## 运行时配置

可通过 `config/params.yaml` 调整：

- Broker 地址、端口、用户名密码
- Keep-alive 和重连退避
- 遥测发布频率
- ROS 2 输入/输出 topic
- MQTT topic 命名

下行 `config` 消息目前支持动态更新：

- `state_rate_hz`
- `vision_rate_hz`
- `radar_rate_hz`
- `radar_safe_distance_m`（仅转发和记录日志）
