"""统一 Topic 适配器：任意 ROS msg -> 紧凑 JSON String（供桥接上行订阅）。"""

from __future__ import annotations

import json
from typing import Any, Optional, Sequence

import rclpy
from rclpy.node import Node
from rosidl_runtime_py.convert import message_to_ordereddict
from rosidl_runtime_py.utilities import get_message
from std_msgs.msg import String

from usv_mqtt_bridge.adapters.ros_payload import strip_headers


class TopicJsonAdapterNode(Node):
    """Subscribe a typed topic; publish compact JSON on a String topic."""

    def __init__(self) -> None:
        super().__init__("topic_json_adapter_node")

        self._input_topic = str(
            self.declare_parameter("input_topic", "").value
        ).strip()
        self._output_topic = str(
            self.declare_parameter("output_topic", "").value
        ).strip()
        self._message_type = str(
            self.declare_parameter("message_type", "").value
        ).strip()

        if not self._input_topic or not self._output_topic or not self._message_type:
            raise RuntimeError(
                "Parameters input_topic, output_topic, and message_type must be non-empty."
            )

        self._msg_cls = get_message(self._message_type)
        self._publisher = self.create_publisher(String, self._output_topic, 10)
        self.create_subscription(
            self._msg_cls,
            self._input_topic,
            self._on_message,
            10,
        )

        self.get_logger().info(
            f"Topic JSON adapter: {self._message_type} "
            f"{self._input_topic} -> {self._output_topic} (headers stripped)"
        )

    def _on_message(self, msg: Any) -> None:
        data = message_to_ordereddict(msg)
        data = strip_headers(data)
        self._publisher.publish(
            String(data=json.dumps(data, separators=(",", ":"), ensure_ascii=True))
        )


def main(args: Optional[Sequence[str]] = None) -> None:
    rclpy.init(args=args)
    try:
        node = TopicJsonAdapterNode()
    except RuntimeError as exc:
        rclpy.logging.get_logger("topic_json_adapter").fatal(f"{exc}")
        rclpy.shutdown()
        raise SystemExit(1) from exc
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
