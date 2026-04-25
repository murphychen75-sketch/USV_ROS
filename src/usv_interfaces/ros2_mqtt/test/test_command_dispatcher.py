import json

import pytest

from usv_mqtt_bridge.command_dispatcher import CommandDispatcher
from usv_mqtt_bridge.serializers import ProtocolError


def test_handle_control_publishes_raw_payload() -> None:
    published = []
    dispatcher = CommandDispatcher(
        device_id="001",
        publish_control=published.append,
        publish_config=lambda value: None,
    )

    dispatcher.handle_control(
        json.dumps(
            {
                "timestamps": {"gateway_publish_time": "2026-04-22T10:00:00.000Z"},
                "device_id": "001",
                "msg_type": "control",
                "seq": 1,
                "payload": {"mode": "auto"},
            }
        )
    )

    assert published == ['{"mode":"auto"}']


def test_handle_config_applies_runtime_config() -> None:
    applied = []
    dispatcher = CommandDispatcher(
        device_id="001",
        publish_control=lambda value: None,
        publish_config=lambda value: None,
        apply_runtime_config=applied.append,
    )

    result = dispatcher.handle_config(
        json.dumps(
            {
                "timestamps": {"gateway_publish_time": "2026-04-22T10:00:00.000Z"},
                "device_id": "001",
                "msg_type": "config",
                "seq": 1,
                "payload": {"state_rate_hz": 5.0},
            }
        )
    )

    assert applied == [{"state_rate_hz": 5.0}]
    assert result.applied_config == {"state_rate_hz": 5.0}


def test_handle_config_rejects_unknown_field() -> None:
    dispatcher = CommandDispatcher(
        device_id="001",
        publish_control=lambda value: None,
        publish_config=lambda value: None,
    )

    with pytest.raises(ProtocolError):
        dispatcher.handle_config(
            json.dumps(
                {
                    "timestamps": {"gateway_publish_time": "2026-04-22T10:00:00.000Z"},
                    "device_id": "001",
                    "msg_type": "config",
                    "seq": 1,
                    "payload": {"bad_field": 5.0},
                }
            )
        )
