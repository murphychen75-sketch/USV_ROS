# USV MQTT Bridge

一个基于 `ROS 2 Python + paho-mqtt` 的轻量桥接节点，用于把 USV 内部 ROS 2 话题转换为 MQTT 上行消息，并把云端 MQTT 下行消息转发回 ROS 2。

## 包定位

`usv_mqtt_bridge` 位于 `src/usv_comm/` 通信层，负责外部 MQTT 协议适配，不承担项目内部接口定义。内部统一语义接口由 `src/usv_interfaces/` 提供。

## 文档入口

### 主要可修改文档

- [`config/params.yaml`](./config/params.yaml)：运行参数、ROS/MQTT 话题映射（首选修改入口）
- [`docs/mqtt_info.md`](./docs/mqtt_info.md)：协议主文档（Topic 与 Payload 定义）
- [`docs/message_contract.md`](./docs/message_contract.md)：代码实现与 ROS 对齐说明

### 参考说明文档

- [`usv_mqtt_bridge/protocol.py`](./usv_mqtt_bridge/protocol.py)：协议常量、Topic 规格、QoS 定义
- [`usv_mqtt_bridge/node.py`](./usv_mqtt_bridge/node.py)：桥接主节点与订阅/发布装配逻辑
- [`usv_mqtt_bridge/mqtt_client.py`](./usv_mqtt_bridge/mqtt_client.py)：MQTT 连接、重连与在线状态处理

## 节点组成

当前 MQTT 节点由以下几个部分组成：

- `launch/usv_mqtt_bridge.launch.py`
  - 节点启动入口，负责加载参数文件并启动 `usv_mqtt_bridge_node`。
- `config/params.yaml`
  - 运行参数配置，包含 Broker 地址、`client_id`、重连参数、发布频率、ROS 2 话题和 MQTT 话题映射。
- `usv_mqtt_bridge/node.py`
  - 主节点逻辑，负责创建 ROS 2 订阅器/发布器，接收上行数据并转发到 MQTT，同时接收 MQTT 下行消息并分发回 ROS 2。
- `usv_mqtt_bridge/mqtt_client.py`
  - MQTT 传输层封装，负责连接 Broker、订阅、发布、断线检测和指数退避重连。
- `usv_mqtt_bridge/serializers.py`
  - 消息封装与 JSON 序列化工具，负责统一 envelope 格式、时间戳补齐和消息解析。
- `usv_mqtt_bridge/protocol.py`
  - 协议定义层，维护 topic 命名、QoS 和消息类型。
- `usv_mqtt_bridge/throttlers.py`
  - 节流控制模块，用于限制部分高频上行话题的发送频率。
- `docs/message_contract.md`
  - 说明 MQTT 与 ROS 2 的当前映射和 `usv_interfaces` 对齐策略。
- `docs/mqtt_info.md`
  - 协议主文档，定义消息矩阵与 payload 结构。
- `scripts/publish_state_test.py`
  - 状态上报测试脚本，用于向 `/usv/state` 持续发布模拟数据，验证桥接链路。

## 功能概览

- Topic 命名统一为：`/sys/{product_id}/{device_id}/thing/{type}/{identifier}`
- 协议优先：优先遵循 [`docs/mqtt_info.md`](./docs/mqtt_info.md) 定义
- ROS 侧缺失链路允许留空：`ros_topics.*` 为空时自动跳过，不影响节点启动
- 上行链路统一封装 envelope：`timestamps`、`device_id`、`msg_type`、`seq`、`payload`

默认使用统一 JSON 包装格式：

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
  "payload": {
    "battery_pct": 86.5,
    "lat": 31.123,
    "lon": 121.456,
    "heading_deg": 75.0,
    "speed_mps": 2.3
  }
}
```

## ROS 2 接口（当前默认接入）

当前实现默认使用 `std_msgs/String` 作为 ROS 2 接口消息类型，消息体内容为 JSON 字符串：

- 上行（ROS -> MQTT）：
  - `/usv/state` -> `.../status`
  - `/usv/vision/metadata` -> `.../vision/targets`
  - `/usv/radar/targets` -> `.../radar/scan`
- 下行（MQTT -> ROS）：
  - `.../mode` -> `/usv/cmd/mode/raw`
  - `.../radar/control` -> `/usv/cmd/radar/control/raw`

如果内部算法已经输出了完整 envelope，节点会复用其中的 `timestamps`；如果只输出纯 payload，节点会补齐 `gateway_publish_time`。

## 现有功能

- 支持按协议定义的上行/下行 topic 自动装配
- 支持“参数留空即不接入”策略，便于渐进式对齐 ROS 话题
- 支持统一 envelope 封装与时间戳补齐
- 支持 MQTT 自动重连与在线状态上报
- 支持高频上行话题节流（由 `publish_rates.*` 控制）

## 待开发功能

- 为下行消息补齐字段级校验（模式枚举、雷达控制参数约束等）
- 增加协议级联调测试（真实 broker 上下行回环）
- 逐步将 `std_msgs/String` 升级到 `usv_interfaces` 强类型接口

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

5. 订阅 MQTT 状态主题（示例）：

```bash
mosquitto_sub -h 127.0.0.1 -t '/sys/M10/USV_N0001/thing/property/status'
```

## 运行时配置

可通过 `config/params.yaml` 调整：

- Broker 地址、端口、用户名密码
- Keep-alive 和重连退避
- 遥测发布频率
- ROS 2 输入/输出 topic
- MQTT topic 命名

完整协议字段请参考 [`docs/mqtt_info.md`](./docs/mqtt_info.md)，实现映射说明请参考 [`docs/message_contract.md`](./docs/message_contract.md)。
