"""ROS 2 node that bridges internal USV topics with MQTT."""

from __future__ import annotations

import logging
from itertools import count
from typing import Dict

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from std_msgs.msg import String

from usv_mqtt_bridge.mqtt_client import MqttClient, MqttTransportConfig, Subscription
from usv_mqtt_bridge.protocol import (
    MSG_TYPE_AIS,
    MSG_TYPE_AIVIDEO_CTRL,
    MSG_TYPE_AIVIDEO_CTRL_REPLY,
    MSG_TYPE_AIVIDEO_STATUS,
    MSG_TYPE_ARM_REPLY,
    MSG_TYPE_AUTO_TASK_REPLY,
    MSG_TYPE_BATTERY_STATUS,
    MSG_TYPE_DEPTH_STATUS,
    DOWNLINK_KEYS,
    MSG_TYPE_DIAG_REQUEST_REPLY,
    MSG_TYPE_ESTOP_REPLY,
    MSG_TYPE_FUEL_STATUS,
    MSG_TYPE_GPS_STATUS,
    MSG_TYPE_HEARTBEAT,
    MSG_TYPE_IMU,
    MSG_TYPE_IO_CTRL,
    MSG_TYPE_IO_CTRL_REPLY,
    MSG_TYPE_IO_STATUS,
    MSG_TYPE_MANUAL_CTRL,
    MSG_TYPE_MANUAL_CTRL_REPLY,
    MSG_TYPE_MCU_STATUS,
    MSG_TYPE_MCU_HEARTBEAT,
    MSG_TYPE_MISSION_DELTA,
    MSG_TYPE_MODE_REPLY,
    MSG_TYPE_MOTOR,
    MSG_TYPE_PARAMS,
    MSG_TYPE_PARAMS_REPLY,
    MSG_TYPE_RADAR_MM,
    MSG_TYPE_RADAR_NAV,
    MSG_TYPE_RADAR_NAV_CONFIG,
    MSG_TYPE_RADAR_NAV_CONFIG_REPLY,
    MSG_TYPE_RADAR_NAV_MAP,
    MSG_TYPE_STATUS,
    MSG_TYPE_TASK_PROG,
    MSG_TYPE_WEATHER_STATUS,
    MSG_TYPE_VISION_TARGETS,
    UPLINK_KEYS,
    TOPIC_SPECS,
    spec_for_topic,
    topic_map,
)
from usv_mqtt_bridge.serializers import (
    ProtocolError,
    build_envelope,
    serialize_envelope,
    split_payload_and_timestamps,
)
from usv_mqtt_bridge.throttlers import RateLimiter

UPLINK_PARAM_KEYS = {
    MSG_TYPE_STATUS: "status",
    "status/jetson": "status_jetson",
    MSG_TYPE_HEARTBEAT: "heartbeat",
    MSG_TYPE_MCU_HEARTBEAT: "mcu_heartbeat",
    "alarm": "alarm",
    MSG_TYPE_MISSION_DELTA: "mission_delta",
    MSG_TYPE_AIVIDEO_STATUS: "aivideo_status",
    "diag/result": "diag_result",
    MSG_TYPE_MOTOR: "motor",
    MSG_TYPE_IMU: "imu",
    MSG_TYPE_RADAR_MM: "radar_mm",
    MSG_TYPE_RADAR_NAV: "radar_nav",
    MSG_TYPE_RADAR_NAV_MAP: "radar_nav_map",
    MSG_TYPE_VISION_TARGETS: "vision_targets",
    "perception/trajectory": "perception_trajectory",
    MSG_TYPE_TASK_PROG: "task_prog",
    MSG_TYPE_GPS_STATUS: "gps_status",
    MSG_TYPE_WEATHER_STATUS: "weather_status",
    MSG_TYPE_DEPTH_STATUS: "depth_status",
    MSG_TYPE_BATTERY_STATUS: "battery_status",
    MSG_TYPE_FUEL_STATUS: "fuel_status",
    MSG_TYPE_MCU_STATUS: "mcu_status",
    MSG_TYPE_AIS: "ais",
    MSG_TYPE_IO_STATUS: "io_status",
    MSG_TYPE_AUTO_TASK_REPLY: "auto_task_reply",
    MSG_TYPE_ESTOP_REPLY: "estop_reply",
    MSG_TYPE_ARM_REPLY: "arm_reply",
    MSG_TYPE_MODE_REPLY: "mode_reply",
    MSG_TYPE_MANUAL_CTRL_REPLY: "manual_ctrl_reply",
    MSG_TYPE_PARAMS_REPLY: "params_reply",
    MSG_TYPE_AIVIDEO_CTRL_REPLY: "aivideo_ctrl_reply",
    MSG_TYPE_RADAR_NAV_CONFIG_REPLY: "radar_nav_config_reply",
    MSG_TYPE_IO_CTRL_REPLY: "io_ctrl_reply",
    MSG_TYPE_DIAG_REQUEST_REPLY: "diag_request_reply",
}

DOWNLINK_PARAM_KEYS = {
    "estop": "estop",
    "arm": "arm",
    "mode": "mode",
    MSG_TYPE_MANUAL_CTRL: "manual_ctrl",
    "auto/task": "auto_task",
    MSG_TYPE_PARAMS: "params",
    MSG_TYPE_AIVIDEO_CTRL: "aivideo_ctrl",
    MSG_TYPE_RADAR_NAV_CONFIG: "radar_nav_config",
    MSG_TYPE_IO_CTRL: "io_ctrl",
    "diag/request": "diag_request",
}


class UsvMqttBridgeNode(Node):
    """Bridge ROS 2 topics to MQTT topics and back."""

    def __init__(self) -> None:
        super().__init__("usv_mqtt_bridge_node")

        self._logger = self.get_logger()
        self._product_id = str(self.declare_parameter("product_id", "M10").value)
        self._device_id = str(self.declare_parameter("device_id", "USV_N0001").value)
        default_topics = topic_map(self._product_id, self._device_id)

        self._mqtt_topics: Dict[str, str] = {}
        for msg_type in TOPIC_SPECS:
            param_suffix = msg_type.replace("/", "_")
            self._mqtt_topics[msg_type] = str(
                self.declare_parameter(f"topics.{param_suffix}", default_topics[msg_type]).value
            )

        default_rates = {
            MSG_TYPE_STATUS: 2.0,
            MSG_TYPE_VISION_TARGETS: 10.0,
            MSG_TYPE_RADAR_NAV: 10.0,
            MSG_TYPE_TASK_PROG: 20.0,
        }
        self._rate_limiters: Dict[str, RateLimiter] = {}
        for msg_type, hz in default_rates.items():
            self._rate_limiters[msg_type] = RateLimiter(
                float(
                    self.declare_parameter(
                        f"publish_rates.{msg_type.replace('/', '_')}_hz", hz
                    ).value
                )
            )
        self._sequences = {msg_type: count(1) for msg_type in UPLINK_KEYS}

        self._downlink_publishers: Dict[str, String] = {}
        for msg_type in DOWNLINK_KEYS:
            param_name = DOWNLINK_PARAM_KEYS[msg_type]
            ros_topic = str(
                self.declare_parameter(f"ros_topics.{param_name}_output_topic", "").value
            ).strip()
            if not ros_topic:
                self._logger.info(f"ROS output topic for {msg_type} is empty; skipping.")
                continue
            self._downlink_publishers[msg_type] = self.create_publisher(
                String,
                ros_topic,
                QoSProfile(depth=10),
            )

        self._telemetry_subscriptions = []
        for msg_type in UPLINK_KEYS:
            param_name = UPLINK_PARAM_KEYS[msg_type]
            ros_topic = str(
                self.declare_parameter(f"ros_topics.{param_name}_input_topic", "").value
            ).strip()
            if not ros_topic:
                self._logger.info(f"ROS input topic for {msg_type} is empty; skipping.")
                continue
            qos = (
                qos_profile_sensor_data
                if msg_type in {MSG_TYPE_VISION_TARGETS, MSG_TYPE_RADAR_NAV}
                else QoSProfile(depth=10)
            )
            self._telemetry_subscriptions.append(
                self.create_subscription(
                    String,
                    ros_topic,
                    lambda msg, key=msg_type: self._handle_telemetry_message(key, msg),
                    qos,
                )
            )

        client_id = str(
            self.declare_parameter("broker.client_id", f"usv-mqtt-{self._device_id}").value
        )
        mqtt_config = MqttTransportConfig(
            host=str(self.declare_parameter("broker.host", "127.0.0.1").value),
            port=int(self.declare_parameter("broker.port", 1883).value),
            client_id=client_id,
            product_id=self._product_id,
            device_id=self._device_id,
            keepalive_sec=int(self.declare_parameter("broker.keepalive_sec", 15).value),
            username=self._optional_string("broker.username"),
            password=self._optional_string("broker.password"),
            reconnect_initial_backoff_sec=float(
                self.declare_parameter("reconnect.initial_backoff_sec", 1.0).value
            ),
            reconnect_max_backoff_sec=float(
                self.declare_parameter("reconnect.max_backoff_sec", 30.0).value
            ),
        )

        self._mqtt_client = MqttClient(
            mqtt_config,
            subscriptions=[
                Subscription(self._mqtt_topics[msg_type], TOPIC_SPECS[msg_type].qos)
                for msg_type in DOWNLINK_KEYS
            ],
            on_message=self._handle_mqtt_message,
            on_connection_state_change=self._handle_connection_state,
            logger=logging.getLogger("usv_mqtt_bridge.mqtt"),
        )
        self._mqtt_client.connect()

    def destroy_node(self) -> bool:
        self._mqtt_client.disconnect()
        return super().destroy_node()

    def _optional_string(self, name: str) -> str | None:
        value = str(self.declare_parameter(name, "").value)
        return value or None

    def _handle_connection_state(self, connected: bool) -> None:
        if connected:
            self._logger.info("MQTT transport connected.")
        else:
            self._logger.warning("MQTT transport disconnected.")

    def _handle_telemetry_message(self, msg_type: str, ros_message: String) -> None:
        limiter = self._rate_limiters.get(msg_type)
        if limiter is not None and not limiter.allow():
            return

        try:
            payload, timestamps = split_payload_and_timestamps(ros_message.data)
            envelope = build_envelope(
                device_id=self._device_id,
                msg_type=msg_type,
                seq=next(self._sequences[msg_type]),
                payload=payload,
                timestamps=timestamps,
            )
            serialized = serialize_envelope(envelope)
        except ProtocolError as exc:
            self._logger.warning(f"Dropping invalid {msg_type} telemetry: {exc}")
            return

        if not self._mqtt_client.is_connected:
            self._logger.debug(
                f"MQTT disconnected, dropping {msg_type} telemetry sample."
            )
            return

        topic = self._mqtt_topics[msg_type]
        spec = TOPIC_SPECS[msg_type]
        try:
            self._mqtt_client.publish(
                topic,
                serialized,
                qos=spec.qos,
                retain=spec.retain,
            )
        except RuntimeError as exc:
            self._logger.warning(f"Failed to publish {msg_type} telemetry: {exc}")

    def _handle_mqtt_message(self, topic: str, raw_payload: bytes) -> None:
        spec = spec_for_topic(topic, self._product_id, self._device_id)
        if spec is None:
            self._logger.warning(f"Ignoring message on unknown topic: {topic}")
            return

        try:
            publisher = self._downlink_publishers.get(spec.key)
            if publisher is None:
                self._logger.info(f"No ROS output for {spec.key}; inbound message ignored.")
                return
            publisher.publish(String(data=raw_payload.decode("utf-8")))
            self._logger.info(f"Processed inbound {spec.key} message.")
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error(f"Unexpected error on inbound message: {exc}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = UsvMqttBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
