from usv_mqtt_bridge.mqtt_client import compute_backoff


def test_compute_backoff_caps_at_maximum() -> None:
    assert compute_backoff(0, 1.0, 30.0) == 1.0
    assert compute_backoff(1, 1.0, 30.0) == 2.0
    assert compute_backoff(5, 1.0, 30.0) == 30.0
