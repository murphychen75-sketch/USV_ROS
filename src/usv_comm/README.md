# usv_comm

`usv_comm` 用于承载 USV_ROS 中所有面向外部系统的通信桥接包。

这一层只做协议适配，不定义项目内部的核心业务语义。内部统一语义接口继续由 `src/usv_interfaces/` 提供，通信层作为其下游消费者，将 ROS 2 侧消息、话题和命令映射为外部协议。

## 当前规划

- `usv_mqtt_bridge`：ROS 2 <-> MQTT 桥接
- `usv_mavlink_bridge`：ROS 2 <-> MAVLink 桥接

## 依赖约束

- `usv_comm/*` 可以依赖 `usv_interfaces`
- `usv_interfaces` 不依赖 `usv_comm/*`
- 协议专属字段、topic 命名、线协议封装格式保留在各自桥接包内部

## 设计原则

当多个内部节点都需要共同理解某个“业务语义”时，应将其抽象到 `usv_interfaces` 中；当某个结构只服务于 MQTT、MAVLink 等单一外部协议时，应保留在对应桥接包内部。
