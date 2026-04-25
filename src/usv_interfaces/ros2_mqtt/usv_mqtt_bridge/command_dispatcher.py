"""Downlink message validation and ROS-side dispatch helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional

from usv_mqtt_bridge.protocol import (
    ALLOWED_CONFIG_FIELDS,
    ALLOWED_CONTROL_FIELDS,
    MSG_TYPE_CONFIG,
    MSG_TYPE_CONTROL,
)
from usv_mqtt_bridge.serializers import ProtocolError, deserialize_command_message


ConfigCallback = Callable[[Dict[str, Any]], None]
PublishCallback = Callable[[str], None]


@dataclass(frozen=True)
class DispatchResult:
    """Summary of a dispatch operation."""

    message_type: str
    applied_config: Dict[str, Any]
    raw_payload: str


def validate_control_payload(payload: Mapping[str, Any]) -> None:
    """Validate the supported control fields."""

    if not payload:
        raise ProtocolError("control payload cannot be empty.")
    unknown = set(payload.keys()) - ALLOWED_CONTROL_FIELDS
    if unknown:
        raise ProtocolError(f"Unsupported control fields: {sorted(unknown)}")
    if not any(key in payload for key in ("command", "mode", "waypoints", "estop")):
        raise ProtocolError("control payload must contain at least one actionable field.")


def filter_config_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Keep only supported config keys and validate values."""

    if not payload:
        raise ProtocolError("config payload cannot be empty.")
    unknown = set(payload.keys()) - ALLOWED_CONFIG_FIELDS
    if unknown:
        raise ProtocolError(f"Unsupported config fields: {sorted(unknown)}")

    filtered = dict(payload)
    for key in ("state_rate_hz", "vision_rate_hz", "radar_rate_hz", "radar_safe_distance_m"):
        if key in filtered and filtered[key] <= 0:
            raise ProtocolError(f"{key} must be positive.")
    return filtered


class CommandDispatcher:
    """Validate and forward downlink messages into ROS-friendly strings."""

    def __init__(
        self,
        *,
        device_id: str,
        publish_control: PublishCallback,
        publish_config: PublishCallback,
        apply_runtime_config: Optional[ConfigCallback] = None,
    ) -> None:
        self._device_id = device_id
        self._publish_control = publish_control
        self._publish_config = publish_config
        self._apply_runtime_config = apply_runtime_config

    def handle_control(self, raw_payload: bytes | str) -> DispatchResult:
        """Validate and publish a control message."""

        envelope = deserialize_command_message(
            raw_payload,
            expected_msg_type=MSG_TYPE_CONTROL,
            expected_device_id=self._device_id,
        )
        payload = envelope["payload"]
        validate_control_payload(payload)
        raw_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
        self._publish_control(raw_json)
        return DispatchResult(
            message_type=MSG_TYPE_CONTROL,
            applied_config={},
            raw_payload=raw_json,
        )

    def handle_config(self, raw_payload: bytes | str) -> DispatchResult:
        """Validate, apply and publish a config message."""

        envelope = deserialize_command_message(
            raw_payload,
            expected_msg_type=MSG_TYPE_CONFIG,
            expected_device_id=self._device_id,
        )
        payload = filter_config_payload(envelope["payload"])
        if self._apply_runtime_config is not None:
            self._apply_runtime_config(payload)
        raw_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
        self._publish_config(raw_json)
        return DispatchResult(
            message_type=MSG_TYPE_CONFIG,
            applied_config=payload,
            raw_payload=raw_json,
        )
