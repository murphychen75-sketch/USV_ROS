"""Protocol definitions for MQTT topics and payload contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


MSG_TYPE_STATUS = "status"
MSG_TYPE_STATUS_JETSON = "status/jetson"
MSG_TYPE_HEARTBEAT = "heartbeat"
MSG_TYPE_ALARM = "alarm"
MSG_TYPE_DIAG_RESULT = "diag/result"
MSG_TYPE_RADAR_CONTROL = "radar/control"
MSG_TYPE_RADAR_SCAN = "radar/scan"
MSG_TYPE_RADAR_SCAN_CONFIG = "radar/scan_config"
MSG_TYPE_RADAR_MAP = "radar/map"
MSG_TYPE_VISION_TARGETS = "vision/targets"
MSG_TYPE_PERCEPTION_TRAJECTORY = "perception/trajectory"
MSG_TYPE_DEPTH = "depth"
MSG_TYPE_WEATHER = "weather"

MSG_TYPE_ESTOP = "estop"
MSG_TYPE_ARM = "arm"
MSG_TYPE_MODE = "mode"
MSG_TYPE_AUTO_TASK = "auto/task"
MSG_TYPE_VIDEO_CTRL = "video/ctrl"
MSG_TYPE_DIAG_REQUEST = "diag/request"

# Legacy aliases retained for backward compatibility in tests/tools.
MSG_TYPE_CONTROL = "control"
MSG_TYPE_CONFIG = "config"

TIMESTAMP_SENSOR = "sensor_capture_time"
TIMESTAMP_ALGORITHM = "algorithm_output_time"
TIMESTAMP_GATEWAY = "gateway_publish_time"

REQUIRED_ENVELOPE_FIELDS = ("timestamps", "device_id", "msg_type", "seq", "payload")

UPLINK_KEYS = (
    MSG_TYPE_STATUS,
    MSG_TYPE_STATUS_JETSON,
    MSG_TYPE_HEARTBEAT,
    MSG_TYPE_ALARM,
    MSG_TYPE_DIAG_RESULT,
    MSG_TYPE_RADAR_CONTROL,
    MSG_TYPE_RADAR_SCAN,
    MSG_TYPE_RADAR_SCAN_CONFIG,
    MSG_TYPE_RADAR_MAP,
    MSG_TYPE_VISION_TARGETS,
    MSG_TYPE_PERCEPTION_TRAJECTORY,
    MSG_TYPE_DEPTH,
    MSG_TYPE_WEATHER,
)

DOWNLINK_KEYS = (
    MSG_TYPE_ESTOP,
    MSG_TYPE_ARM,
    MSG_TYPE_MODE,
    MSG_TYPE_AUTO_TASK,
    MSG_TYPE_RADAR_CONTROL,
    MSG_TYPE_VIDEO_CTRL,
    MSG_TYPE_DIAG_REQUEST,
)

ALLOWED_CONTROL_FIELDS = frozenset({"command", "mode", "waypoints", "estop"})
ALLOWED_CONFIG_FIELDS = frozenset(
    {
        "radar_safe_distance_m",
        "state_rate_hz",
        "vision_rate_hz",
        "radar_rate_hz",
    }
)


@dataclass(frozen=True)
class TopicSpec:
    """MQTT topic contract for a message family."""

    key: str
    msg_type: str
    direction: str
    qos: int
    retain: bool = False

    def render(self, product_id: str, device_id: str) -> str:
        return f"/sys/{product_id}/{device_id}/thing/{self.msg_type}"


TOPIC_SPECS: Dict[str, TopicSpec] = {
    MSG_TYPE_STATUS: TopicSpec(MSG_TYPE_STATUS, "property/status", "up", qos=0),
    MSG_TYPE_STATUS_JETSON: TopicSpec(
        MSG_TYPE_STATUS_JETSON, "property/status_jetson", "up", qos=0
    ),
    MSG_TYPE_HEARTBEAT: TopicSpec(MSG_TYPE_HEARTBEAT, "event/heartbeat", "up", qos=0),
    MSG_TYPE_ALARM: TopicSpec(MSG_TYPE_ALARM, "event/alarm", "up", qos=1),
    MSG_TYPE_DIAG_RESULT: TopicSpec(MSG_TYPE_DIAG_RESULT, "event/diag_result", "up", qos=1),
    MSG_TYPE_RADAR_CONTROL: TopicSpec(MSG_TYPE_RADAR_CONTROL, "service/radar_scan_config", "both", qos=1),
    MSG_TYPE_RADAR_SCAN: TopicSpec(MSG_TYPE_RADAR_SCAN, "property/radar_scan", "up", qos=0),
    MSG_TYPE_RADAR_SCAN_CONFIG: TopicSpec(
        MSG_TYPE_RADAR_SCAN_CONFIG, "event/radar_scan_config_reply", "up", qos=1
    ),
    MSG_TYPE_RADAR_MAP: TopicSpec(MSG_TYPE_RADAR_MAP, "property/radar_map", "up", qos=1),
    MSG_TYPE_VISION_TARGETS: TopicSpec(
        MSG_TYPE_VISION_TARGETS, "event/vision_targets", "up", qos=1
    ),
    MSG_TYPE_PERCEPTION_TRAJECTORY: TopicSpec(
        MSG_TYPE_PERCEPTION_TRAJECTORY, "property/perception_trajectory", "up", qos=0
    ),
    MSG_TYPE_DEPTH: TopicSpec(MSG_TYPE_DEPTH, "property/depth", "up", qos=1),
    MSG_TYPE_WEATHER: TopicSpec(MSG_TYPE_WEATHER, "property/weather", "up", qos=1),
    MSG_TYPE_ESTOP: TopicSpec(MSG_TYPE_ESTOP, "service/estop", "down", qos=1),
    MSG_TYPE_ARM: TopicSpec(MSG_TYPE_ARM, "service/arm", "down", qos=1),
    MSG_TYPE_MODE: TopicSpec(MSG_TYPE_MODE, "service/mode", "down", qos=1),
    MSG_TYPE_AUTO_TASK: TopicSpec(MSG_TYPE_AUTO_TASK, "service/auto_task", "down", qos=1),
    MSG_TYPE_VIDEO_CTRL: TopicSpec(MSG_TYPE_VIDEO_CTRL, "service/video_ctrl", "down", qos=1),
    MSG_TYPE_DIAG_REQUEST: TopicSpec(MSG_TYPE_DIAG_REQUEST, "service/diag_request", "down", qos=1),
}


def topic_for(product_id: str, device_id: str, topic_key: str) -> str:
    """Return a concrete MQTT topic for a device and topic key."""

    try:
        return TOPIC_SPECS[topic_key].render(product_id, device_id)
    except KeyError as exc:
        raise ValueError(f"Unsupported topic key: {topic_key}") from exc


def topic_map(product_id: str, device_id: str) -> Dict[str, str]:
    """Return all MQTT topics keyed by logical message type."""

    return {key: spec.render(product_id, device_id) for key, spec in TOPIC_SPECS.items()}


def spec_for_topic(topic: str, product_id: str, device_id: str) -> Optional[TopicSpec]:
    """Match an MQTT topic against the known namespace."""

    for spec in TOPIC_SPECS.values():
        if spec.render(product_id, device_id) == topic:
            return spec
    return None
