from usv_mqtt_bridge.protocol import MSG_TYPE_CONFIG, MSG_TYPE_STATE, spec_for_topic, topic_for


def test_topic_for_state() -> None:
    assert topic_for("001", MSG_TYPE_STATE) == "usv/001/telemetry/state"


def test_spec_for_topic() -> None:
    spec = spec_for_topic("usv/001/cmd/config", "001")
    assert spec is not None
    assert spec.key == MSG_TYPE_CONFIG
