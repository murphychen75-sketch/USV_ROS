"""Protocol definitions for MQTT topics and payload contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


MSG_TYPE_STATUS = "status"
MSG_TYPE_STATUS_JETSON = "status/jetson"
MSG_TYPE_HEARTBEAT = "heartbeat"
MSG_TYPE_MCU_HEARTBEAT = "mcu/heartbeat"
MSG_TYPE_ALARM = "alarm"
MSG_TYPE_MISSION_DELTA = "mission/delta"
MSG_TYPE_AIVIDEO_STATUS = "aivideo/status"
MSG_TYPE_DIAG_RESULT = "diag/result"
MSG_TYPE_MOTOR = "motor"
MSG_TYPE_IMU = "imu"
MSG_TYPE_RADAR_MM = "radar/mm"
MSG_TYPE_RADAR_NAV = "radar/nav"
MSG_TYPE_RADAR_NAV_MAP = "radar/nav_map"
MSG_TYPE_VISION_TARGETS = "vision/targets"
MSG_TYPE_PERCEPTION_TRAJECTORY = "perception/trajectory"
MSG_TYPE_TASK_PROG = "task/prog"
MSG_TYPE_GPS_STATUS = "gps/status"
MSG_TYPE_WEATHER_STATUS = "weather/status"
MSG_TYPE_DEPTH_STATUS = "depth/status"
MSG_TYPE_BATTERY_STATUS = "battery/status"
MSG_TYPE_FUEL_STATUS = "fuel/status"
MSG_TYPE_MCU_STATUS = "mcu/status"
MSG_TYPE_AIS = "ais"
MSG_TYPE_IO_STATUS = "io/status"

MSG_TYPE_ESTOP = "estop"
MSG_TYPE_ARM = "arm"
MSG_TYPE_MODE = "mode"
MSG_TYPE_MANUAL_CTRL = "manual_ctrl"
MSG_TYPE_AUTO_TASK = "auto/task"
MSG_TYPE_AUTO_TASK_REPLY = "auto/task_reply"
MSG_TYPE_PARAMS = "params"
MSG_TYPE_AIVIDEO_CTRL = "aivideo_ctrl"
MSG_TYPE_RADAR_NAV_CONFIG = "radar_nav_config"
MSG_TYPE_IO_CTRL = "io_ctrl"
MSG_TYPE_DIAG_REQUEST = "diag/request"
MSG_TYPE_ESTOP_REPLY = "estop_reply"
MSG_TYPE_ARM_REPLY = "arm_reply"
MSG_TYPE_MODE_REPLY = "mode_reply"
MSG_TYPE_MANUAL_CTRL_REPLY = "manual_ctrl_reply"
MSG_TYPE_PARAMS_REPLY = "params_reply"
MSG_TYPE_AIVIDEO_CTRL_REPLY = "aivideo_ctrl_reply"
MSG_TYPE_RADAR_NAV_CONFIG_REPLY = "radar_nav_config_reply"
MSG_TYPE_IO_CTRL_REPLY = "io_ctrl_reply"
MSG_TYPE_DIAG_REQUEST_REPLY = "diag_request_reply"

TIMESTAMP_SENSOR = "sensor_capture_time"
TIMESTAMP_ALGORITHM = "algorithm_output_time"
TIMESTAMP_GATEWAY = "gateway_publish_time"

REQUIRED_ENVELOPE_FIELDS = ("timestamps", "device_id", "msg_type", "seq", "payload")

UPLINK_KEYS = (
    MSG_TYPE_STATUS,
    MSG_TYPE_STATUS_JETSON,
    MSG_TYPE_HEARTBEAT,
    MSG_TYPE_MCU_HEARTBEAT,
    MSG_TYPE_ALARM,
    MSG_TYPE_MISSION_DELTA,
    MSG_TYPE_AIVIDEO_STATUS,
    MSG_TYPE_DIAG_RESULT,
    MSG_TYPE_MOTOR,
    MSG_TYPE_IMU,
    MSG_TYPE_RADAR_MM,
    MSG_TYPE_RADAR_NAV,
    MSG_TYPE_RADAR_NAV_MAP,
    MSG_TYPE_VISION_TARGETS,
    MSG_TYPE_PERCEPTION_TRAJECTORY,
    MSG_TYPE_TASK_PROG,
    MSG_TYPE_GPS_STATUS,
    MSG_TYPE_WEATHER_STATUS,
    MSG_TYPE_DEPTH_STATUS,
    MSG_TYPE_BATTERY_STATUS,
    MSG_TYPE_FUEL_STATUS,
    MSG_TYPE_MCU_STATUS,
    MSG_TYPE_AIS,
    MSG_TYPE_IO_STATUS,
    MSG_TYPE_AUTO_TASK_REPLY,
    MSG_TYPE_ESTOP_REPLY,
    MSG_TYPE_ARM_REPLY,
    MSG_TYPE_MODE_REPLY,
    MSG_TYPE_MANUAL_CTRL_REPLY,
    MSG_TYPE_PARAMS_REPLY,
    MSG_TYPE_AIVIDEO_CTRL_REPLY,
    MSG_TYPE_RADAR_NAV_CONFIG_REPLY,
    MSG_TYPE_IO_CTRL_REPLY,
    MSG_TYPE_DIAG_REQUEST_REPLY,
)

DOWNLINK_KEYS = (
    MSG_TYPE_ESTOP,
    MSG_TYPE_ARM,
    MSG_TYPE_MODE,
    MSG_TYPE_MANUAL_CTRL,
    MSG_TYPE_AUTO_TASK,
    MSG_TYPE_PARAMS,
    MSG_TYPE_AIVIDEO_CTRL,
    MSG_TYPE_RADAR_NAV_CONFIG,
    MSG_TYPE_IO_CTRL,
    MSG_TYPE_DIAG_REQUEST,
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
    MSG_TYPE_HEARTBEAT: TopicSpec(MSG_TYPE_HEARTBEAT, "event/jetson_heartbeat", "up", qos=0),
    MSG_TYPE_MCU_HEARTBEAT: TopicSpec(MSG_TYPE_MCU_HEARTBEAT, "event/mcu_heartbeat", "up", qos=0),
    MSG_TYPE_ALARM: TopicSpec(MSG_TYPE_ALARM, "event/alarm", "up", qos=1),
    MSG_TYPE_MISSION_DELTA: TopicSpec(MSG_TYPE_MISSION_DELTA, "event/mission_delta", "up", qos=1),
    MSG_TYPE_AIVIDEO_STATUS: TopicSpec(MSG_TYPE_AIVIDEO_STATUS, "event/aivideo_status", "up", qos=1),
    MSG_TYPE_DIAG_RESULT: TopicSpec(MSG_TYPE_DIAG_RESULT, "event/diag_result", "up", qos=1),
    MSG_TYPE_MOTOR: TopicSpec(MSG_TYPE_MOTOR, "property/motor", "up", qos=1),
    MSG_TYPE_IMU: TopicSpec(MSG_TYPE_IMU, "property/imu", "up", qos=0),
    MSG_TYPE_RADAR_MM: TopicSpec(MSG_TYPE_RADAR_MM, "property/radar_mm", "up", qos=0),
    MSG_TYPE_RADAR_NAV: TopicSpec(MSG_TYPE_RADAR_NAV, "property/radar_nav", "up", qos=0),
    MSG_TYPE_RADAR_NAV_MAP: TopicSpec(MSG_TYPE_RADAR_NAV_MAP, "property/radar_nav_map", "up", qos=1),
    MSG_TYPE_VISION_TARGETS: TopicSpec(
        MSG_TYPE_VISION_TARGETS, "event/aivision_targets", "up", qos=1
    ),
    MSG_TYPE_PERCEPTION_TRAJECTORY: TopicSpec(
        MSG_TYPE_PERCEPTION_TRAJECTORY, "property/perception_trajectory", "up", qos=0
    ),
    MSG_TYPE_TASK_PROG: TopicSpec(MSG_TYPE_TASK_PROG, "event/task_prog", "up", qos=1),
    MSG_TYPE_GPS_STATUS: TopicSpec(MSG_TYPE_GPS_STATUS, "property/gps_status", "up", qos=0),
    MSG_TYPE_WEATHER_STATUS: TopicSpec(MSG_TYPE_WEATHER_STATUS, "property/weather_status", "up", qos=1),
    MSG_TYPE_DEPTH_STATUS: TopicSpec(MSG_TYPE_DEPTH_STATUS, "property/depth_status", "up", qos=1),
    MSG_TYPE_BATTERY_STATUS: TopicSpec(MSG_TYPE_BATTERY_STATUS, "property/battery_status", "up", qos=1),
    MSG_TYPE_FUEL_STATUS: TopicSpec(MSG_TYPE_FUEL_STATUS, "property/fuel_status", "up", qos=1),
    MSG_TYPE_MCU_STATUS: TopicSpec(MSG_TYPE_MCU_STATUS, "property/mcu_status", "up", qos=0),
    MSG_TYPE_AIS: TopicSpec(MSG_TYPE_AIS, "property/ais", "up", qos=0),
    MSG_TYPE_IO_STATUS: TopicSpec(MSG_TYPE_IO_STATUS, "property/io_status", "up", qos=0),
    MSG_TYPE_AUTO_TASK_REPLY: TopicSpec(
        MSG_TYPE_AUTO_TASK_REPLY, "service/auto_task_reply", "up", qos=1
    ),
    MSG_TYPE_ESTOP_REPLY: TopicSpec(MSG_TYPE_ESTOP_REPLY, "service/estop_reply", "up", qos=1),
    MSG_TYPE_ARM_REPLY: TopicSpec(MSG_TYPE_ARM_REPLY, "service/arm_reply", "up", qos=1),
    MSG_TYPE_MODE_REPLY: TopicSpec(MSG_TYPE_MODE_REPLY, "service/mode_reply", "up", qos=1),
    MSG_TYPE_MANUAL_CTRL_REPLY: TopicSpec(MSG_TYPE_MANUAL_CTRL_REPLY, "service/manual_ctrl_reply", "up", qos=1),
    MSG_TYPE_PARAMS_REPLY: TopicSpec(MSG_TYPE_PARAMS_REPLY, "service/params_reply", "up", qos=1),
    MSG_TYPE_AIVIDEO_CTRL_REPLY: TopicSpec(MSG_TYPE_AIVIDEO_CTRL_REPLY, "service/aivideo_ctrl_reply", "up", qos=1),
    MSG_TYPE_RADAR_NAV_CONFIG_REPLY: TopicSpec(
        MSG_TYPE_RADAR_NAV_CONFIG_REPLY, "service/radar_nav_config_reply", "up", qos=1
    ),
    MSG_TYPE_IO_CTRL_REPLY: TopicSpec(MSG_TYPE_IO_CTRL_REPLY, "service/io_ctrl_reply", "up", qos=1),
    MSG_TYPE_DIAG_REQUEST_REPLY: TopicSpec(
        MSG_TYPE_DIAG_REQUEST_REPLY, "service/diag_request_reply", "up", qos=1
    ),
    MSG_TYPE_ESTOP: TopicSpec(MSG_TYPE_ESTOP, "service/estop", "down", qos=1),
    MSG_TYPE_ARM: TopicSpec(MSG_TYPE_ARM, "service/arm", "down", qos=1),
    MSG_TYPE_MODE: TopicSpec(MSG_TYPE_MODE, "service/mode", "down", qos=1),
    MSG_TYPE_MANUAL_CTRL: TopicSpec(MSG_TYPE_MANUAL_CTRL, "service/manual_ctrl", "down", qos=1),
    MSG_TYPE_AUTO_TASK: TopicSpec(MSG_TYPE_AUTO_TASK, "service/auto_task", "down", qos=1),
    MSG_TYPE_PARAMS: TopicSpec(MSG_TYPE_PARAMS, "service/params", "down", qos=1),
    MSG_TYPE_AIVIDEO_CTRL: TopicSpec(MSG_TYPE_AIVIDEO_CTRL, "service/aivideo_ctrl", "down", qos=1),
    MSG_TYPE_RADAR_NAV_CONFIG: TopicSpec(MSG_TYPE_RADAR_NAV_CONFIG, "service/radar_nav_config", "down", qos=1),
    MSG_TYPE_IO_CTRL: TopicSpec(MSG_TYPE_IO_CTRL, "service/io_ctrl", "down", qos=1),
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
