"""MQTT transport wrapper with reconnect and presence handling."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from itertools import count
from typing import Callable, Dict, Iterable, Optional

try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:  # pragma: no cover - environment-specific
    mqtt = None

from usv_mqtt_bridge.protocol import MSG_TYPE_STATUS, topic_for
from usv_mqtt_bridge.serializers import build_envelope, serialize_envelope


ConnectionStateCallback = Callable[[bool], None]
MessageCallback = Callable[[str, bytes], None]


@dataclass(frozen=True)
class Subscription:
    """Subscription request."""

    topic: str
    qos: int


@dataclass(frozen=True)
class MqttTransportConfig:
    """Connection settings for the MQTT transport."""

    host: str
    port: int
    client_id: str
    device_id: str
    keepalive_sec: int = 15
    username: Optional[str] = None
    password: Optional[str] = None
    reconnect_initial_backoff_sec: float = 1.0
    reconnect_max_backoff_sec: float = 30.0


def compute_backoff(attempt: int, initial: float, maximum: float) -> float:
    """Return the exponential backoff delay for a reconnect attempt."""

    return min(initial * (2**attempt), maximum)


class MqttClient:
    """Thin wrapper around paho-mqtt with manual reconnect control."""

    def __init__(
        self,
        config: MqttTransportConfig,
        *,
        subscriptions: Optional[Iterable[Subscription]] = None,
        on_message: Optional[MessageCallback] = None,
        on_connection_state_change: Optional[ConnectionStateCallback] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        if mqtt is None:
            raise RuntimeError(
                "paho-mqtt is required to use MqttClient. Install it with 'pip install paho-mqtt'."
            )
        self._config = config
        self._logger = logger or logging.getLogger(__name__)
        self._on_message_cb = on_message
        self._on_connection_state_change = on_connection_state_change
        self._subscriptions: Dict[str, Subscription] = {
            subscription.topic: subscription for subscription in subscriptions or []
        }
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()
        self._state_lock = threading.Lock()
        self._reconnect_thread: Optional[threading.Thread] = None
        self._status_seq = count(1)

        self._client = mqtt.Client(client_id=config.client_id, clean_session=True)
        if config.username:
            self._client.username_pw_set(config.username, config.password)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.will_set(
            topic_for(config.device_id, MSG_TYPE_STATUS),
            payload=self._presence_payload("offline"),
            qos=1,
            retain=True,
        )

    @property
    def is_connected(self) -> bool:
        """Return whether the MQTT client is connected."""

        return self._connected_event.is_set()

    def connect(self) -> None:
        """Connect to the broker and start the network loop."""

        self._stop_event.clear()
        self._logger.info(
            "Connecting to MQTT broker at %s:%s", self._config.host, self._config.port
        )
        self._client.connect(
            self._config.host,
            port=self._config.port,
            keepalive=self._config.keepalive_sec,
        )
        self._client.loop_start()

    def disconnect(self) -> None:
        """Stop reconnect attempts and disconnect gracefully."""

        self._stop_event.set()
        if self.is_connected:
            try:
                self.publish(
                    topic_for(self._config.device_id, MSG_TYPE_STATUS),
                    self._presence_payload("offline"),
                    qos=1,
                    retain=True,
                    require_connection=False,
                )
            except RuntimeError:
                pass
        self._client.loop_stop()
        self._client.disconnect()
        self._connected_event.clear()

    def add_subscription(self, topic: str, qos: int) -> None:
        """Register a subscription and subscribe immediately if connected."""

        self._subscriptions[topic] = Subscription(topic=topic, qos=qos)
        if self.is_connected:
            self._client.subscribe(topic, qos=qos)

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int,
        retain: bool = False,
        require_connection: bool = True,
    ) -> None:
        """Publish a message and optionally require an active connection."""

        if require_connection and not self.is_connected:
            raise RuntimeError("MQTT client is not connected.")
        result = self._client.publish(topic, payload=payload, qos=qos, retain=retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed with rc={result.rc}")

    def _presence_payload(self, state: str) -> str:
        envelope = build_envelope(
            device_id=self._config.device_id,
            msg_type=MSG_TYPE_STATUS,
            seq=next(self._status_seq),
            payload={"state": state},
        )
        return serialize_envelope(envelope)

    def _on_connect(self, client, userdata, flags, rc) -> None:  # noqa: ANN001, ANN201
        if rc != 0:
            self._logger.error("MQTT connect failed with rc=%s", rc)
            return

        self._logger.info("MQTT connected.")
        self._connected_event.set()
        for subscription in self._subscriptions.values():
            client.subscribe(subscription.topic, qos=subscription.qos)
        self.publish(
            topic_for(self._config.device_id, MSG_TYPE_STATUS),
            self._presence_payload("online"),
            qos=1,
            retain=True,
            require_connection=False,
        )
        if self._on_connection_state_change is not None:
            self._on_connection_state_change(True)

    def _on_disconnect(self, client, userdata, rc) -> None:  # noqa: ANN001, ANN201
        self._connected_event.clear()
        if self._on_connection_state_change is not None:
            self._on_connection_state_change(False)

        if self._stop_event.is_set():
            self._logger.info("MQTT disconnected cleanly.")
            return

        self._logger.warning("MQTT disconnected unexpectedly with rc=%s", rc)
        self._ensure_reconnect_thread()

    def _on_message(self, client, userdata, message) -> None:  # noqa: ANN001, ANN201
        if self._on_message_cb is not None:
            self._on_message_cb(message.topic, message.payload)

    def _ensure_reconnect_thread(self) -> None:
        with self._state_lock:
            if self._reconnect_thread and self._reconnect_thread.is_alive():
                return
            self._reconnect_thread = threading.Thread(
                target=self._reconnect_loop,
                name="mqtt-reconnect",
                daemon=True,
            )
            self._reconnect_thread.start()

    def _reconnect_loop(self) -> None:
        attempt = 0
        while not self._stop_event.is_set():
            delay = compute_backoff(
                attempt,
                self._config.reconnect_initial_backoff_sec,
                self._config.reconnect_max_backoff_sec,
            )
            self._logger.info("Reconnecting to MQTT broker in %.1f seconds", delay)
            time.sleep(delay)
            if self._stop_event.is_set():
                return
            try:
                self._client.reconnect()
                return
            except Exception as exc:  # pragma: no cover - defensive logging
                self._logger.warning("MQTT reconnect attempt failed: %s", exc)
                attempt += 1
