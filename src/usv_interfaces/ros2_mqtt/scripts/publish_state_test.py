#!/usr/bin/env python3
"""Publish test JSON messages to /usv/state for MQTT bridge validation."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def utc_now_iso() -> str:
    """Return an ISO8601 UTC timestamp string."""

    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


class StateTestPublisher(Node):
    """Publish synthetic USV state messages for bridge testing."""

    def __init__(self) -> None:
        super().__init__("state_test_publisher")

        self.declare_parameter("topic", "/usv/state")
        self.declare_parameter("rate_hz", 2.0)
        self.declare_parameter("device_id", "001")
        self.declare_parameter("base_lat", 31.2304)
        self.declare_parameter("base_lon", 121.4737)

        topic = str(self.get_parameter("topic").value)
        self._rate_hz = float(self.get_parameter("rate_hz").value)
        self._device_id = str(self.get_parameter("device_id").value)
        self._base_lat = float(self.get_parameter("base_lat").value)
        self._base_lon = float(self.get_parameter("base_lon").value)
        self._seq = 0

        self._publisher = self.create_publisher(String, topic, 10)
        self._timer = self.create_timer(1.0 / self._rate_hz, self._publish_once)

        self.get_logger().info(
            f"Publishing test state messages to {topic} at {self._rate_hz:.2f} Hz"
        )

    def _publish_once(self) -> None:
        self._seq += 1
        phase = self._seq / 10.0

        payload = {
            "timestamps": {
                "sensor_capture_time": utc_now_iso(),
                "algorithm_output_time": utc_now_iso(),
            },
            "device_id": self._device_id,
            "msg_type": "state",
            "seq": self._seq,
            "payload": {
                "cpu_usage": round(25.0 + 5.0 * math.sin(phase), 2),
                "mem_usage": round(43.0 + 3.0 * math.cos(phase), 2),
                "battery_pct": round(max(0.0, 92.0 - self._seq * 0.05), 2),
                "lat": round(self._base_lat + 0.0001 * math.sin(phase / 2.0), 7),
                "lon": round(self._base_lon + 0.0001 * math.cos(phase / 2.0), 7),
                "heading_deg": round((phase * 15.0) % 360.0, 2),
                "speed_mps": round(1.5 + 0.3 * math.sin(phase), 2),
            },
        }

        message = String()
        message.data = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        self._publisher.publish(message)
        self.get_logger().info(
            f"Published /usv/state test message seq={self._seq}"
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = StateTestPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
