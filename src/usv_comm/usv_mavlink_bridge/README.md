# USV MAVLink Bridge

这是一个预留的 ROS 2 功能包，用于后续承载 USV 与 MAVLink 生态之间的协议桥接能力。

当前阶段仅创建包骨架，不引入具体的 MAVLink 依赖或运行节点。后续实现建议包括：

- ROS 2 状态到 MAVLink 遥测消息的映射
- MAVLink 控制/模式/任务点到内部 ROS 接口的映射
- UDP、串口或 TCP 连接参数管理
- 与 `usv_interfaces` 的强类型消息对齐

## 目录定位

本包位于 `src/usv_comm/`，与 `usv_mqtt_bridge` 平级，统一属于外部通信层。
