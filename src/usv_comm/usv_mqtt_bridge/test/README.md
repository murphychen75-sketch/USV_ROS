# usv_mqtt_bridge 测试说明

本目录用于协议与桥接逻辑的测试，分为两类：

- 单元测试：`test_*.py`
- 联调发布脚本：`publish_protocol_topics.py`

## 1) 按现协议发送测试话题（频率 + QoS）

脚本会按 `docs/mqtt_info.md` 的频率语义发送：

- 高频：10 Hz（如 `radar/scan`、`vision/targets`）
- 中频：2 Hz（如 `radar/map`）
- 中低频：2 Hz（如 `status`、`status/jetson`、`depth`、`weather`）
- 心跳：1 Hz（`heartbeat`）
- 低频：1 Hz（`radar/scan_config`）
- 事件：0.2 Hz（每 5s 一次，如 `mode`、`radar/control`、`estop` 等）

QoS 直接取自 `protocol.py` 的 `TOPIC_SPECS`：

- `status`/`radar/scan`/`perception/trajectory` 使用 QoS 0
- 其他协议消息默认 QoS 1

发布 Topic 统一遵循：

- `/sys/{product_id}/{device_id}/thing/{type}/{identifier}`

### 运行命令

在工作区根目录执行：

```bash
python3 src/usv_comm/usv_mqtt_bridge/test/publish_protocol_topics.py
```

默认会读取：

- `src/usv_comm/usv_mqtt_bridge/config/params.yaml`
- 读取字段：`broker.host`、`broker.port`、`product_id`、`device_id`

默认行为是**持续发送**（不自动停止）。

手动停止方式：

- 在同一终端输入 `stop` 并回车
- 或直接 `Ctrl+C`

### 参数覆盖（可选）

可按需覆盖部分参数，例如：

```bash
python3 src/usv_comm/usv_mqtt_bridge/test/publish_protocol_topics.py \
  --host 127.0.0.1 \
  --port 1883 \
  --device-id USV_N0002 \
  --topic-group uplink
```

如果你仍希望定长发送，可指定 `--cycles`，例如 20 次调度循环后退出：

```bash
python3 src/usv_comm/usv_mqtt_bridge/test/publish_protocol_topics.py --cycles 20
```

### 说明

- 消息内容按 `docs/mqtt_info.md` 当前协议示例构造。
- 所有消息按 envelope 格式封装：`timestamps/device_id/msg_type/seq/payload`。
- `--topic-group` 可选：`uplink` / `downlink` / `all`（默认 `all`）。

## 2) 建议配合的订阅验证

```bash
mosquitto_sub -h 127.0.0.1 -t '/M10/USV_N0001/JETSON01/#'
```

## 3) 协议参考

- 协议主文档：[`../docs/mqtt_info.md`](../docs/mqtt_info.md)
- 实现映射：[`../docs/message_contract.md`](../docs/message_contract.md)
