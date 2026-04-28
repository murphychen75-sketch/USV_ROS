from usv_mqtt_bridge.protocol import MSG_TYPE_MODE, MSG_TYPE_STATUS, spec_for_topic, topic_for


def test_topic_for_status() -> None:
    assert (
        topic_for("M10", "USV_N0001", MSG_TYPE_STATUS)
        == "/sys/M10/USV_N0001/thing/property/status"
    )


def test_spec_for_topic() -> None:
    spec = spec_for_topic("/sys/M10/USV_N0001/thing/service/mode", "M10", "USV_N0001")
    assert spec is not None
    assert spec.key == MSG_TYPE_MODE
