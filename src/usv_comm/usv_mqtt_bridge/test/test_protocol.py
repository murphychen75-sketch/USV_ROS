from usv_mqtt_bridge.protocol import MSG_TYPE_MODE, MSG_TYPE_STATUS, spec_for_topic, topic_for


def test_topic_for_status() -> None:
    assert (
        topic_for("M10", "USV_N0001", "JETSON01", MSG_TYPE_STATUS)
        == "/M10/USV_N0001/JETSON01/status"
    )


def test_spec_for_topic() -> None:
    spec = spec_for_topic("/M10/USV_N0001/JETSON01/mode", "M10", "USV_N0001", "JETSON01")
    assert spec is not None
    assert spec.key == MSG_TYPE_MODE
