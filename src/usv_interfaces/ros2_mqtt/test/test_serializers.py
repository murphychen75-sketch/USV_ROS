import json

import pytest

from usv_mqtt_bridge.serializers import (
    ProtocolError,
    build_envelope,
    deserialize_command_message,
    serialize_envelope,
    split_payload_and_timestamps,
)


def test_split_payload_and_timestamps_from_envelope() -> None:
    payload, timestamps = split_payload_and_timestamps(
        {
            "timestamps": {"sensor_capture_time": "2026-04-22T10:00:00.000Z"},
            "payload": {"speed_mps": 1.2},
        }
    )
    assert payload == {"speed_mps": 1.2}
    assert timestamps == {"sensor_capture_time": "2026-04-22T10:00:00.000Z"}


def test_serialize_envelope_injects_gateway_timestamp() -> None:
    envelope = build_envelope(
        device_id="001",
        msg_type="state",
        seq=1,
        payload={"battery_pct": 90},
    )
    serialized = serialize_envelope(envelope)
    parsed = json.loads(serialized)
    assert "gateway_publish_time" in parsed["timestamps"]


def test_deserialize_command_rejects_wrong_type() -> None:
    with pytest.raises(ProtocolError):
        deserialize_command_message(
            json.dumps(
                {
                    "timestamps": {"gateway_publish_time": "2026-04-22T10:00:00.000Z"},
                    "device_id": "001",
                    "msg_type": "state",
                    "seq": 1,
                    "payload": {},
                }
            ),
            expected_msg_type="config",
            expected_device_id="001",
        )
