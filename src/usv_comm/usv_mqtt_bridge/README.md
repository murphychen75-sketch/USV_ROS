# USV MQTT Bridge

`usv_mqtt_bridge` 是 `ROS 2 Python + paho-mqtt` 的协议桥接包，用于在 ROS 与 MQTT 之间双向转发无人船数据与指令。

## 包定位

- 目录：`src/usv_comm/usv_mqtt_bridge`
- 职责：外部 MQTT 协议适配（topic、qos、payload/envelope）
- 边界：不定义内部业务语义，内部语义由 `src/usv_interfaces` 承载

## 核心文档

- [`config/params.yaml`](./config/params.yaml)：运行时参数与 ROS/MQTT 映射
- [`docs/mqtt_info.md`](./docs/mqtt_info.md)：协议定义文档
- [`docs/message_contract.md`](./docs/message_contract.md)：实现映射与“强映射”字段对照

## 代码结构

- `usv_mqtt_bridge/node.py`：桥接主节点（ROS 订阅/发布装配 + MQTT 收发）
- `usv_mqtt_bridge/protocol.py`：消息类型、topic 模板、QoS
- `usv_mqtt_bridge/mqtt_client.py`：MQTT 连接、重连、在线状态
- `usv_mqtt_bridge/serializers.py`：envelope 序列化/反序列化
- `usv_mqtt_bridge/throttlers.py`：上行限频
- `launch/usv_mqtt_bridge.launch.py`：节点启动入口
- `test/`：联调与单测脚本

## 当前实现状态

### 1) 物模型映射

已按协议完成 5 类映射能力：

- `Property` 上行
- `Event` 上行
- `Service` 下行请求
- `Service` 上行回复（`*_reply`）
- 任务异步链路（`auto_task` goal / `task_prog` feedback / `auto_task_reply` result）

> 详细映射与字段级对照请看 [`docs/message_contract.md`](./docs/message_contract.md)。

### 2) ROS 接口形态

- 当前桥接 I/O 仍以 `std_msgs/String`（JSON 文本）为主
- 语义层已与 `usv_interfaces` 对齐（`msg/srv/action` 已建立）
- 后续可逐步把字符串 topic 迁移到强类型服务/动作调用

### 3) 空映射策略

- `ros_topics.*` 为空时，该链路自动跳过，不影响节点启动
- 这允许按子系统分批接入，不要求一次配全

## Envelope 格式

上行默认封装为统一 envelope：

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

如果 ROS 输入本身已是 envelope，桥接会复用其中字段；如果仅是 payload，会自动补齐 `gateway_publish_time`。

## 运行方式

1) 安装依赖

```bash
pip install paho-mqtt
```

2) 构建

```bash
cd ~/USV_ROS
colcon build --packages-select usv_mqtt_bridge --symlink-install
source install/setup.bash
```

3) 启动

```bash
ros2 launch usv_mqtt_bridge usv_mqtt_bridge.launch.py
```

## 测试脚本

### 1) 三类话题联调脚本（ROS -> MQTT）

脚本：`test/publish_ros_triplet_and_verify_mqtt.py`

用途：分别从 ROS 侧发布一条 `event/property/service` 测试消息，并在 MQTT 侧订阅验证转发成功。

```bash
cd ~/USV_ROS
python3 src/usv_comm/usv_mqtt_bridge/test/publish_ros_triplet_and_verify_mqtt.py
```

可选参数：

```bash
python3 src/usv_comm/usv_mqtt_bridge/test/publish_ros_triplet_and_verify_mqtt.py \
  --params-file src/usv_comm/usv_mqtt_bridge/config/params.yaml \
  --host 127.0.0.1 --port 1883 --timeout-sec 10
```

### 2) 协议多话题发布脚本（MQTT 侧）

脚本：`test/publish_protocol_topics.py`

```bash
python3 src/usv_comm/usv_mqtt_bridge/test/publish_protocol_topics.py --topic-group all
```

## 常见调试点

- 检查 `config/params.yaml` 中 `ros_topics.*` 是否配置了实际业务 topic
- 检查 `product_id/device_id` 是否与订阅端一致
- 检查 broker 可达性（host/port/鉴权）
- 检查 MQTT 订阅主题是否与 `topic_for(...)` 生成结果一致

## 后续建议

- 将下行控制链路由 `std_msgs/String` 逐步升级为 `usv_interfaces/srv`/`action`
- 为关键链路补集成测试（`*_reply`、`task_prog`、`mission_delta`）
- 收敛 `params.yaml` 默认映射到统一 `usv_interfaces/topics` 常量命名体系
