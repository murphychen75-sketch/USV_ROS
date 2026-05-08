#!/usr/bin/env python3
"""Publish one event/property/service message from ROS and verify MQTT forwarding."""

from __future__ import annotations

import argparse
import json
import threading
import time
from pathlib import Path
from typing import Dict, Set

import paho.mqtt.client as mqtt
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import yaml

from usv_mqtt_bridge.protocol import (
    MSG_TYPE_AUTO_TASK_REPLY,
    MSG_TYPE_STATUS_JETSON,
    MSG_TYPE_TASK_PROG,
    topic_for,
)


class RosTripletPublisher(Node):
    """Publishes one sample message per selected ROS input topic."""

    def __init__(self, ros_topics: Dict[str, str]) -> None:
        super().__init__("ros_triplet_publisher")
        self._pubs: Dict[str, object] = {}
        for key, topic in ros_topics.items():
            if topic:
                self._pubs[key] = self.create_publisher(String, topic, 10)
            else:
                self.get_logger().warning(
                    f"ROS topic for '{key}' is empty in params file; skipping."
                )

    def publish_once(self, key: str, payload: Dict) -> bool:
        pub = self._pubs.get(key)
        if pub is None:
            return False
        msg = String()
        msg.data = json.dumps(payload, ensure_ascii=True)
        pub.publish(msg)
        return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish ROS event/property/service samples and verify MQTT output."
    )
    parser.add_argument(
        "--params-file",
        default="src/usv_comm/usv_mqtt_bridge/config/params.yaml",
        help="Path to usv_mqtt_bridge params.yaml",
    )
    parser.add_argument("--host", default=None, help="MQTT broker host override")
    parser.add_argument("--port", type=int, default=None, help="MQTT broker port override")
    parser.add_argument("--product-id", default=None, help="product_id override")
    parser.add_argument("--device-id", default=None, help="device_id override")
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=8.0,
        help="Wait timeout for receiving MQTT messages",
    )
    return parser.parse_args()


def load_ros_and_broker_defaults(params_file: str) -> Dict[str, str | int]:
    params_path = Path(params_file)
    if not params_path.exists():
        raise FileNotFoundError(f"Params file not found: {params_file}")

    with params_path.open("r", encoding="utf-8") as f:
        root = yaml.safe_load(f)

    ros_params = root["usv_mqtt_bridge_node"]["ros__parameters"]
    return {
        "host": str(ros_params["broker.host"]),
        "port": int(ros_params["broker.port"]),
        "product_id": str(ros_params["product_id"]),
        "device_id": str(ros_params["device_id"]),
        "status_jetson_input_topic": str(ros_params.get("ros_topics.status_jetson_input_topic", "")),
        "task_prog_input_topic": str(ros_params.get("ros_topics.task_prog_input_topic", "")),
        "auto_task_reply_input_topic": str(ros_params.get("ros_topics.auto_task_reply_input_topic", "")),
    }


def build_payloads(now_ms: int) -> Dict[str, Dict]:
    return {
        "property": {
            "timestamp": now_ms,
            "seq": 1,
            "data": {
                "cpu_usage_percent": 35.2,
                "memory_usage_percent": 48.6,
                "gpu_usage_percent": 22.1,
                "temperature_c": 61.5,
                "uptime_ms": 1234567,
                "disk_usage_percent": 41.3,
            },
        },
        "event": {
            "timestamp": now_ms,
            "seq": 1,
            "data": {
                "task_id": "TASK_DEMO_001",
                "state": 2,
                "progress_percent": 37.5,
                "current_waypoint_index": 3,
                "status_text": "running",
                "error_code": 0,
                "message": "ok",
                "start_time_ms": now_ms - 5000,
                "end_time_ms": 0,
            },
        },
        "service": {
            "timestamp": now_ms,
            "seq": 1,
            "data": {
                "code": 200,
                "message": "task complete",
                "task_id": "TASK_DEMO_001",
                "state": 4,
                "error_code": 0,
            },
        },
    }


def main() -> None:
    args = parse_args()
    defaults = load_ros_and_broker_defaults(args.params_file)
    host = args.host or str(defaults["host"])
    port = args.port if args.port is not None else int(defaults["port"])
    product_id = args.product_id or str(defaults["product_id"])
    device_id = args.device_id or str(defaults["device_id"])

    mqtt_topics = {
        "property": topic_for(product_id, device_id, MSG_TYPE_STATUS_JETSON),
        "event": topic_for(product_id, device_id, MSG_TYPE_TASK_PROG),
        "service": topic_for(product_id, device_id, MSG_TYPE_AUTO_TASK_REPLY),
    }
    ros_topics = {
        "property": str(defaults["status_jetson_input_topic"]),
        "event": str(defaults["task_prog_input_topic"]),
        "service": str(defaults["auto_task_reply_input_topic"]),
    }

    received: Set[str] = set()
    recv_lock = threading.Lock()

    def on_connect(client, userdata, flags, rc):  # noqa: ANN001, ANN201
        if rc != 0:
            raise RuntimeError(f"MQTT connect failed with rc={rc}")
        for t in mqtt_topics.values():
            client.subscribe(t, qos=1)

    def on_message(client, userdata, msg):  # noqa: ANN001, ANN201
        key = next((k for k, t in mqtt_topics.items() if t == msg.topic), None)
        if key is None:
            return
        with recv_lock:
            received.add(key)
        print(
            json.dumps(
                {
                    "received_key": key,
                    "topic": msg.topic,
                    "payload": msg.payload.decode("utf-8"),
                },
                ensure_ascii=True,
            )
        )

    client = mqtt.Client(client_id="usv-ros-triplet-verify", clean_session=True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port=port, keepalive=15)
    client.loop_start()

    rclpy.init()
    node = RosTripletPublisher(ros_topics)

    try:
        now_ms = int(time.time() * 1000)
        payloads = build_payloads(now_ms)

        sent = {}
        for key in ("property", "event", "service"):
            sent[key] = node.publish_once(key, payloads[key])
            print(
                json.dumps(
                    {
                        "key": key,
                        "ros_topic": ros_topics[key],
                        "mqtt_topic": mqtt_topics[key],
                        "sent": sent[key],
                    },
                    ensure_ascii=True,
                )
            )

        deadline = time.time() + args.timeout_sec
        while time.time() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            with recv_lock:
                expected = {k for k, v in sent.items() if v}
                if expected and expected.issubset(received):
                    break
            time.sleep(0.05)

        with recv_lock:
            expected = {k for k, v in sent.items() if v}
            missing = sorted(expected - received)

        result = {
            "broker": f"{host}:{port}",
            "expected_keys": sorted(expected),
            "received_keys": sorted(received),
            "missing_keys": missing,
            "ok": len(missing) == 0 and len(expected) > 0,
        }
        print(json.dumps(result, ensure_ascii=True))
        if not result["ok"]:
            raise SystemExit(1)
    finally:
        node.destroy_node()
        rclpy.shutdown()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

