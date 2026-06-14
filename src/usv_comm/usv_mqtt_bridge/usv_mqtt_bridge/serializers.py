"""Helpers for JSON serialization and protocol validation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, MutableMapping, Optional, Tuple

from usv_mqtt_bridge.protocol import REQUIRED_ENVELOPE_FIELDS, TIMESTAMP_GATEWAY


class ProtocolError(ValueError):
    """Raised when a message does not satisfy the bridge contract."""


def utc_now_iso() -> str:
    """Return an RFC3339-like UTC timestamp with milliseconds."""

    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def parse_json_text(raw_text: str) -> Any:
    """Parse a JSON string and raise a protocol-specific error on failure."""

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"Invalid JSON payload: {exc}") from exc


def require_mapping(value: Any, context: str) -> Mapping[str, Any]:
    """Ensure the value is a mapping."""

    if not isinstance(value, Mapping):
        raise ProtocolError(f"{context} must be a JSON object.")
    return value


def normalize_timestamps(timestamps: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Copy timestamps and inject the gateway publish time when absent."""

    normalized: Dict[str, Any] = {}
    if timestamps is not None:
        normalized.update(require_mapping(timestamps, "timestamps"))
    normalized.setdefault(TIMESTAMP_GATEWAY, utc_now_iso())
    return normalized


def split_payload_and_timestamps(raw_data: Any) -> Tuple[Any, Optional[Mapping[str, Any]]]:
    """Accept either a raw payload or an existing envelope-like object."""

    if isinstance(raw_data, str):
        raw_data = parse_json_text(raw_data)

    if not isinstance(raw_data, Mapping):
        return raw_data, None

    timestamps = raw_data.get("timestamps")
    if "payload" in raw_data and isinstance(
        raw_data.get("payload"), (Mapping, list, str, int, float, bool, type(None))
    ):
        return raw_data["payload"], timestamps

    payload = dict(raw_data)
    payload.pop("timestamps", None)
    payload.pop("timestamp", None)
    return payload, timestamps or {"source_timestamp": raw_data.get("timestamp")}


def build_envelope(
    *,
    device_id: str,
    msg_type: str,
    seq: int,
    payload: Any,
    timestamps: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the common bridge message envelope."""

    return {
        "timestamps": normalize_timestamps(timestamps),
        "device_id": device_id,
        "msg_type": msg_type,
        "seq": seq,
        "payload": payload,
    }


def serialize_envelope(envelope: Mapping[str, Any]) -> str:
    """Serialize an envelope into compact JSON."""

    validate_envelope(envelope)
    return json.dumps(envelope, separators=(",", ":"), ensure_ascii=True, sort_keys=False)


def validate_envelope(envelope: Mapping[str, Any]) -> None:
    """Validate the common envelope fields."""

    require_mapping(envelope, "envelope")
    missing_fields = [field for field in REQUIRED_ENVELOPE_FIELDS if field not in envelope]
    if missing_fields:
        raise ProtocolError(f"Envelope missing fields: {', '.join(missing_fields)}")

    require_mapping(envelope["timestamps"], "timestamps")
    if not envelope["device_id"]:
        raise ProtocolError("device_id cannot be empty.")
    if not envelope["msg_type"]:
        raise ProtocolError("msg_type cannot be empty.")
    if not isinstance(envelope["seq"], int) or envelope["seq"] < 0:
        raise ProtocolError("seq must be a non-negative integer.")
