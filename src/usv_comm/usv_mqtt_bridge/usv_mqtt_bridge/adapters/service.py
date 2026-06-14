"""统一 Service 适配器：JSON String（Request 字段）-> 调用 ROS service。"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional, Sequence, cast

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_services_default
from rosidl_runtime_py.set_message import set_message_fields
from rosidl_runtime_py.utilities import get_service
from std_msgs.msg import String


class ServiceJsonAdapterNode(Node):
    """Subscribe String JSON; fill service Request via rosidl_runtime_py; call_async."""

    def __init__(self) -> None:
        super().__init__("service_json_adapter_node")

        self._input_topic = str(
            self.declare_parameter("input_topic", "").value
        ).strip()
        self._service_name = str(
            self.declare_parameter("service_name", "").value
        ).strip()
        self._service_type = str(
            self.declare_parameter("service_type", "").value
        ).strip()
        self._json_root_key = str(
            self.declare_parameter("json_root_key", "").value
        ).strip()

        if not self._input_topic or not self._service_name or not self._service_type:
            raise RuntimeError(
                "Parameters input_topic, service_name, and service_type must be non-empty."
            )

        self._srv_cls = get_service(self._service_type)
        self._client = self.create_client(
            self._srv_cls,
            self._service_name,
            qos_profile=qos_profile_services_default,
        )
        self.create_subscription(String, self._input_topic, self._on_string, 10)

        self.get_logger().info(
            f"Service JSON adapter: {self._input_topic} -> {self._service_name} "
            f"({self._service_type})"
        )

    def _extract_request_mapping(self, parsed: Any) -> Mapping[str, Any]:
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

    def _on_string(self, msg: String) -> None:
        try:
            parsed = json.loads(msg.data)
            fields = dict(self._extract_request_mapping(parsed))
        except (json.JSONDecodeError, ValueError) as exc:
            self.get_logger().warning(f"Invalid service JSON input: {exc}")
            return

        if not self._client.service_is_ready():
            self.get_logger().warning(
                f"Service not ready: {self._service_name}; dropping request"
            )
            return

        request = self._srv_cls.Request()
        try:
            set_message_fields(request, fields)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"Failed to build Request: {exc}")
            return

        future = self._client.call_async(request)
        future.add_done_callback(self._on_response)

    def _on_response(self, future: Any) -> None:
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"Service call failed: {exc}")
            return
        self.get_logger().debug(f"Service response: {response}")


def main(args: Optional[Sequence[str]] = None) -> None:
    rclpy.init(args=args)
    try:
        node = ServiceJsonAdapterNode()
    except RuntimeError as exc:
        rclpy.logging.get_logger("service_json_adapter").fatal(f"{exc}")
        rclpy.shutdown()
        raise SystemExit(1) from exc
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
