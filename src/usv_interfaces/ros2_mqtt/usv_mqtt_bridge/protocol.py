"""Protocol definitions for MQTT topics and payload contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


TOPIC_ROOT = "usv"

MSG_TYPE_STATE = "state"
MSG_TYPE_VISION = "vision"
MSG_TYPE_RADAR = "radar"
MSG_TYPE_CONTROL = "control"
MSG_TYPE_CONFIG = "config"
MSG_TYPE_STATUS = "status"

TIMESTAMP_SENSOR = "sensor_capture_time"
TIMESTAMP_ALGORITHM = "algorithm_output_time"
TIMESTAMP_GATEWAY = "gateway_publish_time"

REQUIRED_ENVELOPE_FIELDS = ("timestamps", "device_id", "msg_type", "seq", "payload")

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
    category: str
    subtype: str
    qos: int
    retain: bool = False

    def render(self, device_id: str) -> str:
        return f"{TOPIC_ROOT}/{device_id}/{self.category}/{self.subtype}"


TOPIC_SPECS: Dict[str, TopicSpec] = {
    MSG_TYPE_STATE: TopicSpec(MSG_TYPE_STATE, "telemetry", "state", qos=0),
    MSG_TYPE_VISION: TopicSpec(MSG_TYPE_VISION, "telemetry", "vision", qos=0),
    MSG_TYPE_RADAR: TopicSpec(MSG_TYPE_RADAR, "telemetry", "radar", qos=0),
    MSG_TYPE_CONTROL: TopicSpec(MSG_TYPE_CONTROL, "cmd", "control", qos=1),
    MSG_TYPE_CONFIG: TopicSpec(MSG_TYPE_CONFIG, "cmd", "config", qos=1),
    MSG_TYPE_STATUS: TopicSpec(MSG_TYPE_STATUS, "status", "lwt", qos=1, retain=True),
}


def topic_for(device_id: str, topic_key: str) -> str:
    """Return a concrete MQTT topic for a device and topic key."""

    try:
        return TOPIC_SPECS[topic_key].render(device_id)
    except KeyError as exc:
        raise ValueError(f"Unsupported topic key: {topic_key}") from exc


def topic_map(device_id: str) -> Dict[str, str]:
    """Return all MQTT topics keyed by logical message type."""

    return {key: spec.render(device_id) for key, spec in TOPIC_SPECS.items()}


def spec_for_topic(topic: str, device_id: str) -> Optional[TopicSpec]:
    """Match an MQTT topic against the known namespace."""

    for spec in TOPIC_SPECS.values():
        if spec.render(device_id) == topic:
            return spec
    return None
