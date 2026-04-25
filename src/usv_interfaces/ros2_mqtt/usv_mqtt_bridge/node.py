"""ROS 2 node that bridges internal USV topics with MQTT."""

from __future__ import annotations

import logging
from itertools import count
from typing import Any, Dict

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from std_msgs.msg import String

from usv_mqtt_bridge.command_dispatcher import CommandDispatcher
from usv_mqtt_bridge.mqtt_client import MqttClient, MqttTransportConfig, Subscription
from usv_mqtt_bridge.protocol import (
    MSG_TYPE_CONFIG,
    MSG_TYPE_CONTROL,
    MSG_TYPE_RADAR,
    MSG_TYPE_STATE,
    MSG_TYPE_VISION,
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


class UsvMqttBridgeNode(Node):
    """Bridge ROS 2 topics to MQTT topics and back."""

    def __init__(self) -> None:
        super().__init__("usv_mqtt_bridge_node")

        self._logger = self.get_logger()
        self._device_id = str(self.declare_parameter("device_id", "001").value)
        default_topics = topic_map(self._device_id)

        self._mqtt_topics = {
            MSG_TYPE_STATE: str(
                self.declare_parameter("topics.state", default_topics[MSG_TYPE_STATE]).value
            ),
            MSG_TYPE_VISION: str(
                self.declare_parameter("topics.vision", default_topics[MSG_TYPE_VISION]).value
            ),
            MSG_TYPE_RADAR: str(
                self.declare_parameter("topics.radar", default_topics[MSG_TYPE_RADAR]).value
            ),
            MSG_TYPE_CONTROL: str(
                self.declare_parameter(
                    "topics.control", default_topics[MSG_TYPE_CONTROL]
                ).value
            ),
            MSG_TYPE_CONFIG: str(
                self.declare_parameter("topics.config", default_topics[MSG_TYPE_CONFIG]).value
            ),
            "status": str(
                self.declare_parameter("topics.status_lwt", default_topics["status"]).value
            ),
        }

        state_hz = float(self.declare_parameter("publish_rates.state_hz", 2.0).value)
        vision_hz = float(self.declare_parameter("publish_rates.vision_hz", 10.0).value)
        radar_hz = float(self.declare_parameter("publish_rates.radar_hz", 10.0).value)

        self._rate_limiters = {
            MSG_TYPE_STATE: RateLimiter(state_hz),
            MSG_TYPE_VISION: RateLimiter(vision_hz),
            MSG_TYPE_RADAR: RateLimiter(radar_hz),
        }
        self._sequences = {
            MSG_TYPE_STATE: count(1),
            MSG_TYPE_VISION: count(1),
            MSG_TYPE_RADAR: count(1),
        }

        self._control_publisher = self.create_publisher(
            String,
            str(
                self.declare_parameter(
                    "ros_topics.control_output_topic", "/usv/cmd/control/raw"
                ).value
            ),
            QoSProfile(depth=10),
        )
        self._config_publisher = self.create_publisher(
            String,
            str(
                self.declare_parameter(
                    "ros_topics.config_output_topic", "/usv/cmd/config/raw"
                ).value
            ),
            QoSProfile(depth=10),
        )

        self._command_dispatcher = CommandDispatcher(
            device_id=self._device_id,
            publish_control=self._publish_control_raw,
            publish_config=self._publish_config_raw,
            apply_runtime_config=self._apply_runtime_config,
        )

        self._state_subscription = self.create_subscription(
            String,
            str(self.declare_parameter("ros_topics.state_input_topic", "/usv/state").value),
            lambda msg: self._handle_telemetry_message(MSG_TYPE_STATE, msg),
            QoSProfile(depth=10),
        )
        self._vision_subscription = self.create_subscription(
            String,
            str(
                self.declare_parameter(
                    "ros_topics.vision_input_topic", "/usv/vision/metadata"
                ).value
            ),
            lambda msg: self._handle_telemetry_message(MSG_TYPE_VISION, msg),
            qos_profile_sensor_data,
        )
        self._radar_subscription = self.create_subscription(
            String,
            str(
                self.declare_parameter(
                    "ros_topics.radar_input_topic", "/usv/radar/targets"
                ).value
            ),
            lambda msg: self._handle_telemetry_message(MSG_TYPE_RADAR, msg),
            qos_profile_sensor_data,
        )

        client_id = str(
            self.declare_parameter("broker.client_id", f"usv-mqtt-{self._device_id}").value
        )
        mqtt_config = MqttTransportConfig(
            host=str(self.declare_parameter("broker.host", "127.0.0.1").value),
            port=int(self.declare_parameter("broker.port", 1883).value),
            client_id=client_id,
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
                Subscription(self._mqtt_topics[MSG_TYPE_CONTROL], TOPIC_SPECS[MSG_TYPE_CONTROL].qos),
                Subscription(self._mqtt_topics[MSG_TYPE_CONFIG], TOPIC_SPECS[MSG_TYPE_CONFIG].qos),
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

    def _publish_control_raw(self, raw_json: str) -> None:
        self._control_publisher.publish(String(data=raw_json))

    def _publish_config_raw(self, raw_json: str) -> None:
        self._config_publisher.publish(String(data=raw_json))

    def _handle_connection_state(self, connected: bool) -> None:
        if connected:
            self._logger.info("MQTT transport connected.")
        else:
            self._logger.warning("MQTT transport disconnected.")

    def _handle_telemetry_message(self, msg_type: str, ros_message: String) -> None:
        limiter = self._rate_limiters[msg_type]
        if not limiter.allow():
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
        spec = spec_for_topic(topic, self._device_id)
        if spec is None:
            self._logger.warning(f"Ignoring message on unknown topic: {topic}")
            return

        try:
            if spec.key == MSG_TYPE_CONTROL:
                result = self._command_dispatcher.handle_control(raw_payload)
            elif spec.key == MSG_TYPE_CONFIG:
                result = self._command_dispatcher.handle_config(raw_payload)
            else:
                self._logger.warning(f"Ignoring unsupported inbound topic: {topic}")
                return
            self._logger.info(f"Processed inbound {result.message_type} message.")
        except ProtocolError as exc:
            self._logger.warning(f"Rejected inbound message on {topic}: {exc}")
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.error(f"Unexpected error on inbound message: {exc}")

    def _apply_runtime_config(self, config: Dict[str, Any]) -> None:
        rate_key_to_type = {
            "state_rate_hz": MSG_TYPE_STATE,
            "vision_rate_hz": MSG_TYPE_VISION,
            "radar_rate_hz": MSG_TYPE_RADAR,
        }
        for key, value in config.items():
            if key in rate_key_to_type:
                self._rate_limiters[rate_key_to_type[key]].set_rate(float(value))
                self._logger.info(f"Updated {key} to {float(value):.2f} Hz")
            elif key == "radar_safe_distance_m":
                self._logger.info(
                    f"Forwarded radar_safe_distance_m={float(value):.3f}"
                )


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
