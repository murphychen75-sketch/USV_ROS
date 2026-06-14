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
- `usv_mqtt_bridge/adapters/`：ROS ↔ JSON `std_msgs/String` 适配层（按 Topic / Service / Action 收口）
  - `ros_payload.py`：递归去掉 `header`（与 Topic 序列化一致）
  - `topic.py`：`topic_json_adapter_node`（强类型 Topic → JSON String）
  - `service.py`：`service_json_adapter_node`（JSON → 调用 `srv`）
  - `action.py`：`action_json_adapter_node`（JSON Goal → `send_goal`，可选 Feedback/Result 再发布为 String）
- `usv_mqtt_bridge/protocol.py`：消息类型、topic 模板、QoS
- `usv_mqtt_bridge/mqtt_client.py`：MQTT 连接、重连、在线状态
- `usv_mqtt_bridge/serializers.py`：envelope 序列化/校验
- `usv_mqtt_bridge/throttlers.py`：上行限频
- `launch/usv_mqtt_bridge.launch.py`：节点启动入口
- `scripts/publish_state_test.py`：本地开发用状态发布脚本（**非** `setup.py` 安装入口；与 `test/publish_protocol_topics.py` 职责不同，按需选用）
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
colcon build --packages-select usv_interfaces usv_mqtt_bridge --symlink-install
source install/setup.bash
```

3) 启动

```bash
ros2 launch usv_mqtt_bridge usv_mqtt_bridge.launch.py
```

## 适配层：Topic / Service / Action（JSON `String`）

桥接节点 `usv_mqtt_bridge_node` 的 ROS 侧仍以 `std_msgs/String`（紧凑 JSON）为主。适配层把强类型 Topic、或下行 JSON 与服务/动作对接起来。

**约定**：Topic 与 Action 的 Feedback/Result 序列化会**递归删除所有名为 `header` 的字段**。JSON 字段名需与对应 `*.msg` / `*.srv` Request / `*.action` Goal 一致；嵌套类型用嵌套 JSON。若云端字段名与接口不一致，需前置一层薄转换（本包不提供字段映射参数）。

### 1) Topic：`topic_json_adapter_node`（强类型 → JSON String）

- 必设参数：
  - `input_topic`：强类型订阅话题
  - `output_topic`：桥接层 `std_msgs/String` 输入话题（与 `config/params.yaml` 里 `ros_topics.*_input_topic` 对齐）
  - `message_type`：ROS 类型全名，例如 `usv_interfaces/msg/JetsonStatus`

示例（`property/status_jetson` 链路）：

```bash
ros2 run usv_mqtt_bridge topic_json_adapter_node \
  --ros-args \
  -p input_topic:=/usv/monitor/jetson_status \
  -p output_topic:=/usv/monitor/status_jetson/json \
  -p message_type:=usv_interfaces/msg/JetsonStatus
```

### 2) Service：`service_json_adapter_node`（JSON String → 调用 `srv`）

用于「桥已从 MQTT 吐出 JSON、需进入 ROS 服务」的下行：订阅 `String`，解析为对象后填入对应 `Request` 并 `call_async`。

- 必设参数：
  - `input_topic`：JSON `String` 订阅话题（通常与 `params.yaml` 中某 `ros_topics.*_output_topic` 一致，例如 `ros_topics.mode_output_topic`）
  - `service_name`：目标服务全名（如 `/usv/cmd/set_mode`）
  - `service_type`：服务类型全名（如 `usv_interfaces/srv/SetMode`）
- 可选：`json_root_key` — 若 JSON 顶层为 `{ "request": { ... } }` 等形式，可设为 `request` 以取内层对象作为 Request 字段表

示例（模式指令，话题名需与实际部署一致）：

```bash
ros2 run usv_mqtt_bridge service_json_adapter_node \
  --ros-args \
  -p input_topic:=/usv/cmd/mode/raw \
  -p service_name:=/usv/cmd/set_mode \
  -p service_type:=usv_interfaces/srv/SetMode
```

### 3) Action：`action_json_adapter_node`（JSON Goal → `send_goal`）

用于异步任务：订阅 Goal 的 JSON `String`，`send_goal_async`；可选将 Feedback / Result 再发布为 `String`，供桥或其它节点做上行（与 `auto_task` / `task_prog` 等协议衔接）。

- 必设参数：
  - `goal_input_topic`：Goal JSON `String`（常对应 `ros_topics.auto_task_output_topic` 等）
  - `action_name`：动作服务器名
  - `action_type`：动作类型全名（如 `usv_interfaces/action/AutoTask`）
- 可选：
  - `json_root_key`：同 Service，用于包一层对象
  - `feedback_output_topic`：有则注册 feedback 回调并发布去 `header` 后的 JSON
  - `result_output_topic`：有则在结束后发布 Result 的 JSON（可与 `ros_topics.auto_task_reply_input_topic` 等对接）

仅发 Goal、不配置 `feedback_output_topic` / `result_output_topic` 时，不做上行 Feedback/Result；与单独实现任务状态的业务节点分工由部署方约定。

```bash
ros2 run usv_mqtt_bridge action_json_adapter_node \
  --ros-args \
  -p goal_input_topic:=/usv/cmd/auto_task/raw \
  -p action_name:=/usv/task/auto_task \
  -p action_type:=usv_interfaces/action/AutoTask \
  -p feedback_output_topic:=/usv/task/progress/json \
  -p result_output_topic:=/usv/task/result/json
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
