"""统一 Action 适配器：JSON String（Goal 字段）-> send_goal；可选发布 Feedback/Result 为 String。"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional, Sequence, cast

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import qos_profile_services_default
from rosidl_runtime_py.convert import message_to_ordereddict
from rosidl_runtime_py.set_message import set_message_fields
from rosidl_runtime_py.utilities import get_action
from std_msgs.msg import String

from usv_mqtt_bridge.adapters.ros_payload import strip_headers


class ActionJsonAdapterNode(Node):
    """Subscribe String JSON goals; optional String publishers for feedback/result."""

    def __init__(self) -> None:
        super().__init__("action_json_adapter_node")

        self._goal_input_topic = str(
            self.declare_parameter("goal_input_topic", "").value
        ).strip()
        self._action_name = str(
            self.declare_parameter("action_name", "").value
        ).strip()
        self._action_type = str(
            self.declare_parameter("action_type", "").value
        ).strip()
        self._json_root_key = str(
            self.declare_parameter("json_root_key", "").value
        ).strip()
        self._feedback_output_topic = str(
            self.declare_parameter("feedback_output_topic", "").value
        ).strip()
        self._result_output_topic = str(
            self.declare_parameter("result_output_topic", "").value
        ).strip()

        if not self._goal_input_topic or not self._action_name or not self._action_type:
            raise RuntimeError(
                "Parameters goal_input_topic, action_name, and action_type must be non-empty."
            )

        self._action_if = get_action(self._action_type)
        self._client = ActionClient(
            self,
            self._action_if,
            self._action_name,
            goal_service_qos_profile=qos_profile_services_default,
            result_service_qos_profile=qos_profile_services_default,
            cancel_service_qos_profile=qos_profile_services_default,
        )

        self._feedback_pub: Optional[Any] = None
        if self._feedback_output_topic:
            self._feedback_pub = self.create_publisher(
                String, self._feedback_output_topic, 10
            )

        self._result_pub: Optional[Any] = None
        if self._result_output_topic:
            self._result_pub = self.create_publisher(
                String, self._result_output_topic, 10
            )

        self.create_subscription(String, self._goal_input_topic, self._on_goal_string, 10)

        self.get_logger().info(
            f"Action JSON adapter: {self._goal_input_topic} -> {self._action_name} "
            f"({self._action_type})"
        )

    def _extract_goal_mapping(self, parsed: Any) -> Mapping[str, Any]:
        if not isinstance(parsed, Mapping):
            raise ValueError("JSON root must be an object")
        data = parsed
        if self._json_root_key:
            inner = data.get(self._json_root_key)
            if not isinstance(inner, Mapping):
                raise ValueError(
                    f"Expected object at key '{self._json_root_key}'"
                )
            data = inner
        return cast(Mapping[str, Any], data)

    def _publish_json(self, publisher: Any, ros_msg: Any) -> None:
        data = message_to_ordereddict(ros_msg)
        data = strip_headers(data)
        publisher.publish(
            String(data=json.dumps(data, separators=(",", ":"), ensure_ascii=True))
        )

    def _feedback_callback(self, feedback_msg: Any) -> None:
        if self._feedback_pub is None:
            return
        inner = getattr(feedback_msg, "feedback", feedback_msg)
        self._publish_json(self._feedback_pub, inner)

    def _on_goal_string(self, msg: String) -> None:
        try:
            parsed = json.loads(msg.data)
            fields = dict(self._extract_goal_mapping(parsed))
        except (json.JSONDecodeError, ValueError) as exc:
            self.get_logger().warning(f"Invalid action goal JSON: {exc}")
            return

        if not self._client.server_is_ready():
            self.get_logger().warning(
                f"Action server not ready: {self._action_name}; dropping goal"
            )
            return

        goal = self._action_if.Goal()
        try:
            set_message_fields(goal, fields)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"Failed to build Goal: {exc}")
            return

        send_future = self._client.send_goal_async(
            goal,
            feedback_callback=self._feedback_callback
            if self._feedback_pub is not None
            else None,
        )
        send_future.add_done_callback(self._on_goal_accepted)

    def _on_goal_accepted(self, future: Any) -> None:
        try:
            goal_handle = future.result()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"send_goal failed: {exc}")
            return
        if not goal_handle.accepted:
            self.get_logger().warning("Goal rejected by action server")
            return

        if self._result_pub is None:
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_result)

    def _on_result(self, future: Any) -> None:
        if self._result_pub is None:
            return
        try:
            result_wrapper = future.result()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"get_result failed: {exc}")
            return
        result_msg = getattr(result_wrapper, "result", result_wrapper)
        self._publish_json(self._result_pub, result_msg)


def main(args: Optional[Sequence[str]] = None) -> None:
    rclpy.init(args=args)
    try:
        node = ActionJsonAdapterNode()
    except RuntimeError as exc:
        rclpy.logging.get_logger("action_json_adapter").fatal(f"{exc}")
        rclpy.shutdown()
        raise SystemExit(1) from exc
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
