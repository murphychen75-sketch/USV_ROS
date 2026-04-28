import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from usv_interfaces.msg import HeartbeatStatus
from usv_interfaces import topics as usv_topics

try:
    from mavros_msgs.msg import State as MavrosState
except Exception:  # noqa: BLE001
    MavrosState = None


class HeartbeatNode(Node):
    def __init__(self) -> None:
        super().__init__("heartbeat_node")
        self.declare_parameter("heartbeat_hz", 1.0)
        self.declare_parameter("autopilot_state_topic", usv_topics.TOPIC_AUTOPILOT_STATE)
        self.declare_parameter("heartbeat_topic", usv_topics.TOPIC_HEARTBEAT)
        self.declare_parameter("heartbeat_json_topic", "/usv/monitor/heartbeat/json")
        self.declare_parameter("fallback_mavros_state_topic", usv_topics.TOPIC_MAVROS_STATE_RAW)
        self.declare_parameter("use_fallback_mavros", False)

        self._mcu_online = False
        self._armed_status = False
        self._control_mode = "UNKNOWN"

        hb_topic = self.get_parameter("heartbeat_topic").value
        self._heartbeat_pub = self.create_publisher(HeartbeatStatus, hb_topic, 10)
        self._heartbeat_json_pub = self.create_publisher(
            String, self.get_parameter("heartbeat_json_topic").value, 10
        )
        self.create_subscription(
            HeartbeatStatus,
            self.get_parameter("autopilot_state_topic").value,
            self._autopilot_state_cb,
            10,
        )

        if self.get_parameter("use_fallback_mavros").value and MavrosState is not None:
            self.create_subscription(
                MavrosState,
                self.get_parameter("fallback_mavros_state_topic").value,
                self._mavros_state_cb,
                10,
            )

        hz = max(0.2, float(self.get_parameter("heartbeat_hz").value))
        self.create_timer(1.0 / hz, self._timer_cb)
        self.get_logger().info(f"heartbeat_node started: {hz:.2f}Hz")

    def _autopilot_state_cb(self, msg: HeartbeatStatus) -> None:
        self._mcu_online = bool(msg.online)
        self._armed_status = bool(msg.armed_status)
        self._control_mode = msg.control_mode or "UNKNOWN"

    def _mavros_state_cb(self, msg) -> None:
        self._mcu_online = bool(msg.connected)
        self._armed_status = bool(msg.armed)
        self._control_mode = msg.mode if msg.mode else "UNKNOWN"

    def _publish_status(self, online: bool, unit: str, armed: bool, mode: str) -> None:
        msg = HeartbeatStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.online = online
        msg.unit = unit
        msg.armed_status = armed
        msg.control_mode = mode
        self._heartbeat_pub.publish(msg)

        payload = {"online": online, "unit": unit}
        if unit == "mcu":
            payload["armed_status"] = armed
            payload["control_mode"] = mode
        s = String()
        s.data = json.dumps(payload, ensure_ascii=True)
        self._heartbeat_json_pub.publish(s)

    def _timer_cb(self) -> None:
        self._publish_status(True, "jetson", False, "")
        self._publish_status(
            self._mcu_online,
            "mcu",
            self._armed_status,
            self._control_mode,
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = HeartbeatNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

