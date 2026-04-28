import json

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class AlarmWatchdogNode(Node):
    def __init__(self) -> None:
        super().__init__("alarm_watchdog_node")
        self.declare_parameter("watchdog_hz", 1.0)
        self.declare_parameter("alarm_topic", "/usv/monitor/alarm")
        self.declare_parameter("monitored_nodes", [])

        self._monitored_nodes = list(self.get_parameter("monitored_nodes").value)
        self._alarm_pub = self.create_publisher(
            String, self.get_parameter("alarm_topic").value, 10
        )

        hz = max(0.2, float(self.get_parameter("watchdog_hz").value))
        self.create_timer(1.0 / hz, self._tick)
        self.get_logger().info("alarm_watchdog_node placeholder started.")

    def _tick(self) -> None:
        msg = {
            "watchdog_ready": True,
            "alarm_enabled": False,
            "monitored_nodes": self._monitored_nodes,
            "todo": "implement node liveness checks and alarm policy",
        }
        ros_msg = String()
        ros_msg.data = json.dumps(msg, ensure_ascii=True)
        self._alarm_pub.publish(ros_msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = AlarmWatchdogNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

