#!/usr/bin/env python3
"""Publish multiple protocol topics concurrently for integration testing."""

from __future__ import annotations

import argparse
import json
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import paho.mqtt.client as mqtt
import yaml

from usv_mqtt_bridge.protocol import (
    MSG_TYPE_ALARM,
    MSG_TYPE_ARM,
    MSG_TYPE_AUTO_TASK,
    MSG_TYPE_DEPTH,
    MSG_TYPE_DIAG_REQUEST,
    MSG_TYPE_DIAG_RESULT,
    MSG_TYPE_ESTOP,
    MSG_TYPE_HEARTBEAT,
    MSG_TYPE_MODE,
    MSG_TYPE_PERCEPTION_TRAJECTORY,
    MSG_TYPE_RADAR_CONTROL,
    MSG_TYPE_RADAR_MAP,
    MSG_TYPE_RADAR_SCAN,
    MSG_TYPE_RADAR_SCAN_CONFIG,
    MSG_TYPE_STATUS,
    MSG_TYPE_STATUS_JETSON,
    MSG_TYPE_VIDEO_CTRL,
    MSG_TYPE_VISION_TARGETS,
    MSG_TYPE_WEATHER,
    TOPIC_SPECS,
    topic_for,
)
from usv_mqtt_bridge.serializers import build_envelope, serialize_envelope


def build_sample_payload(msg_type: str) -> Dict:
    if msg_type == MSG_TYPE_STATUS_JETSON:
        return {
            "cpu_usage_percent": 42.5,
            "memory_usage_percent": 68.3,
            "gpu_usage_percent": 27.8,
            "temperature_c": 72.4,
            "uptime_ms": 86400000,
            "disk_usage_percent": 55.2,
        }
    if msg_type == MSG_TYPE_HEARTBEAT:
        return {"mcu_online": True}
    if msg_type == MSG_TYPE_ALARM:
        return {
            "event_id": "evt-001",
            "error_name": "SENSOR_AIS_FAIL",
            "error_level": "warning",
        }
    if msg_type == MSG_TYPE_DIAG_RESULT:
        return {"modules": [{"name": "all", "ok": True}], "result": "ok"}
    """Return a protocol-aligned payload per message type."""
    if msg_type == MSG_TYPE_STATUS:
        return {
            "version": "1.1.0",
            "uptime": 86400,
            "rssi": -68,
            "current_link": "5G",
            "control_mode": "auto",
            "armed_status": "armed",
            "estop": False,
            "mqtt_online": True,
        }
    if msg_type == MSG_TYPE_VISION_TARGETS:
        return {
            "targets_num": 1,
            "targets": [
                {
                    "class": "buoy",
                    "confidence": 0.96,
                    "bbox": {"x": 120, "y": 80, "width": 200, "height": 150},
                    "rel_ang": 31.1257,
                }
            ],
        }
    if msg_type == MSG_TYPE_RADAR_SCAN:
        return {
            "targets_num": 2,
            "targets": [
                {
                    "range_m": 45.2,
                    "bearing_deg": 32.5,
                    "intensity": 0.92,
                    "velocity_mps": 6.8,
                },
                {
                    "range_m": 78.0,
                    "bearing_deg": 120.3,
                    "intensity": 0.45,
                    "velocity_mps": -2.3,
                },
            ],
        }
    if msg_type == MSG_TYPE_RADAR_SCAN_CONFIG:
        return {"angular_resolution_deg": 0.9, "max_range_m": 200.0}
    if msg_type == MSG_TYPE_RADAR_MAP:
        return {
            "map_id": "radar_local_001",
            "frame_id": "base_link",
            "width": 100,
            "height": 100,
            "resolution_m": 0.5,
            "origin": {"x": -25.0, "y": -25.0},
            "encoding": "rle",
            "cells": "AAECAwQFBgc=",
        }
    if msg_type == MSG_TYPE_MODE:
        return {"mode": "auto"}
    if msg_type == MSG_TYPE_ESTOP:
        return {"estop": False, "src": "shore"}
    if msg_type == MSG_TYPE_ARM:
        return {"armed": "arm"}
    if msg_type == MSG_TYPE_AUTO_TASK:
        return {
            "cmd": "start",
            "task_id": "TASK_001",
            "pointNumers": 2,
            "waypoints": [
                {"lat": 31.123456, "lon": 121.123456, "order": 1},
                {"lat": 31.123457, "lon": 121.123457, "order": 2},
            ],
            "mode": "auto",
        }
    if msg_type == MSG_TYPE_RADAR_CONTROL:
        return {
            "cmd": "set_config",
            "mode": "navigation",
            "scan_config": {
                "angular_resolution_deg": 0.9,
                "max_range_m": 200.0,
                "scan_rate_hz": 10.0,
            },
            "source": "shore",
        }
    if msg_type == MSG_TYPE_VIDEO_CTRL:
        return {
            "cmd": "start",
            "camera_id": "front",
            "resolution": "1920x1080",
            "fps": 30,
            "bitrate_kbps": 4096,
        }
    if msg_type == MSG_TYPE_DIAG_REQUEST:
        return {"modules": ["all"]}
    if msg_type == MSG_TYPE_PERCEPTION_TRAJECTORY:
        return {
            "trajectories": [
                {
                    "track_id": 101,
                    "object_type": "vehicle",
                    "points": [
                        {
                            "lat": 31.12567890,
                            "lon": 121.12567890,
                            "timestamp": 1703123456000,
                            "speed_mps": 5.2,
                            "heading_deg": 90.0,
                        }
                    ],
                }
            ]
        }
    if msg_type == MSG_TYPE_DEPTH:
        return {
            "position": {"lat": 30.1234567, "lon": 114.1234567, "alt": None},
            "water_depth": {"depth_m": 12.37, "offset_m": 0.45, "confidence": 0.98},
        }
    if msg_type == MSG_TYPE_WEATHER:
        return {
            "temp": 25.9,
            "humidity": 67.1,
            "pressure": 1000.2,
            "wind_speed": 3.5,
            "wind_direction": 120.0,
        }
    return {}


def build_message(device_id: str, msg_type: str, seq: int) -> str:
    """Build envelope JSON text for a msg_type."""
    envelope = build_envelope(
        device_id=device_id,
        msg_type=msg_type,
        seq=seq,
        payload=build_sample_payload(msg_type),
    )
    return serialize_envelope(envelope)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish several MQTT protocol topics in each cycle."
    )
    parser.add_argument(
        "--params-file",
        default="src/usv_comm/usv_mqtt_bridge/config/params.yaml",
        help="Path to usv_mqtt_bridge params.yaml",
    )
    parser.add_argument("--host", default=None, help="MQTT broker host (override)")
    parser.add_argument("--port", type=int, default=None, help="MQTT broker port (override)")
    parser.add_argument("--product-id", default=None, help="Product id (override)")
    parser.add_argument("--device-id", default=None, help="Device id (override)")
    parser.add_argument("--unit-id", default=None, help="Unit id (override)")
    parser.add_argument("--interval-sec", type=float, default=1.0)
    parser.add_argument(
        "--client-id", default="usv-mqtt-test-publisher", help="MQTT client id"
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=0,
        help="Publish cycles count, 0 means run forever until stopped manually",
    )
    parser.add_argument(
        "--topic-group",
        choices=("uplink", "downlink", "all"),
        default="all",
        help="Select which topic set to publish",
    )
    return parser.parse_args()


def load_defaults_from_params(params_file: str) -> Dict[str, str | int]:
    """Load defaults from usv_mqtt_bridge ROS params file."""
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
        "unit_id": str(ros_params["unit_id"]),
    }


def topic_rate_hz(msg_type: str) -> float:
    """Return a default publish rate according to mqtt_info frequency labels."""
    rate_map = {
        MSG_TYPE_STATUS: 2.0,  # 中低频
        MSG_TYPE_STATUS_JETSON: 2.0,  # 中低频
        MSG_TYPE_HEARTBEAT: 1.0,  # 1Hz
        MSG_TYPE_ALARM: 0.2,  # 事件
        MSG_TYPE_DIAG_RESULT: 0.2,  # 事件
        MSG_TYPE_RADAR_CONTROL: 0.2,  # 事件（上行回执/下行指令）
        MSG_TYPE_RADAR_SCAN: 10.0,  # 高频
        MSG_TYPE_RADAR_SCAN_CONFIG: 1.0,  # 低频
        MSG_TYPE_RADAR_MAP: 2.0,  # 中频
        MSG_TYPE_VISION_TARGETS: 10.0,  # 高频
        MSG_TYPE_PERCEPTION_TRAJECTORY: 10.0,  # 实时
        MSG_TYPE_DEPTH: 2.0,  # 中低频
        MSG_TYPE_WEATHER: 2.0,  # 中低频
        MSG_TYPE_ESTOP: 0.2,  # 事件
        MSG_TYPE_ARM: 0.2,  # 事件
        MSG_TYPE_MODE: 0.2,  # 事件
        MSG_TYPE_AUTO_TASK: 0.2,  # 事件
        MSG_TYPE_VIDEO_CTRL: 0.2,  # 事件
        MSG_TYPE_DIAG_REQUEST: 0.2,  # 事件
    }
    return rate_map[msg_type]


def select_msg_types(group: str) -> List[str]:
    uplink_types = [
        MSG_TYPE_STATUS,
        MSG_TYPE_STATUS_JETSON,
        MSG_TYPE_HEARTBEAT,
        MSG_TYPE_ALARM,
        MSG_TYPE_DIAG_RESULT,
        MSG_TYPE_RADAR_SCAN,
        MSG_TYPE_RADAR_SCAN_CONFIG,
        MSG_TYPE_RADAR_MAP,
        MSG_TYPE_VISION_TARGETS,
        MSG_TYPE_PERCEPTION_TRAJECTORY,
        MSG_TYPE_DEPTH,
        MSG_TYPE_WEATHER,
    ]
    downlink_types = [
        MSG_TYPE_ESTOP,
        MSG_TYPE_ARM,
        MSG_TYPE_MODE,
        MSG_TYPE_AUTO_TASK,
        MSG_TYPE_RADAR_CONTROL,
        MSG_TYPE_VIDEO_CTRL,
        MSG_TYPE_DIAG_REQUEST,
    ]
    if group == "uplink":
        return uplink_types
    if group == "downlink":
        return downlink_types
    return uplink_types + downlink_types


def start_manual_stop_listener(stop_event: threading.Event) -> None:
    """Allow manual stop by typing 'stop' in terminal."""
    print('输入 "stop" 并回车可手动停止发送。')
    while not stop_event.is_set():
        try:
            command = input().strip().lower()
        except EOFError:
            return
        if command == "stop":
            stop_event.set()
            return


def main() -> None:
    args = parse_args()
    defaults = load_defaults_from_params(args.params_file)
    host = args.host or defaults["host"]
    port = args.port if args.port is not None else int(defaults["port"])
    product_id = args.product_id or defaults["product_id"]
    device_id = args.device_id or defaults["device_id"]
    unit_id = args.unit_id or defaults["unit_id"]

    client = mqtt.Client(client_id=args.client_id, clean_session=True)
    client.connect(host, port=port, keepalive=15)
    client.loop_start()

    msg_types = select_msg_types(args.topic_group)
    seq_map = defaultdict(int)
    interval_map = {msg_type: 1.0 / topic_rate_hz(msg_type) for msg_type in msg_types}
    next_due = {msg_type: time.monotonic() for msg_type in msg_types}
    stop_event = threading.Event()
    threading.Thread(
        target=start_manual_stop_listener, args=(stop_event,), daemon=True
    ).start()
    cycle = 0

    try:
        while not stop_event.is_set():
            now = time.monotonic()
            published_types = []
            for msg_type in msg_types:
                if now < next_due[msg_type]:
                    continue
                seq_map[msg_type] += 1
                topic = topic_for(product_id, device_id, unit_id, msg_type)
                payload = build_message(device_id, msg_type, seq_map[msg_type])
                spec = TOPIC_SPECS[msg_type]
                result = client.publish(topic, payload=payload, qos=spec.qos)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    raise RuntimeError(
                        f"Publish failed on topic {topic}, rc={result.rc}"
                    )
                next_due[msg_type] = now + interval_map[msg_type]
                published_types.append(f"{msg_type}(qos={spec.qos},hz={topic_rate_hz(msg_type)})")

            if published_types:
                cycle += 1
                print(
                    json.dumps(
                        {
                            "cycle": cycle,
                            "published_types": published_types,
                            "target": f"{product_id}/{device_id}/{unit_id}",
                            "broker": f"{host}:{port}",
                        },
                        ensure_ascii=True,
                    )
                )
                if args.cycles > 0 and cycle >= args.cycles:
                    break
            time.sleep(min(args.interval_sec, 0.02))
    finally:
        stop_event.set()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

