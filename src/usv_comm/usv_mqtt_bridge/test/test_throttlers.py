from usv_mqtt_bridge.throttlers import RateLimiter


def test_rate_limiter_blocks_second_call_in_same_window() -> None:
    current_time = {"value": 0.0}
    limiter = RateLimiter(2.0, clock=lambda: current_time["value"])

    assert limiter.allow() is True
    assert limiter.allow() is False

    current_time["value"] = 0.5
    assert limiter.allow() is True


def test_rate_limiter_can_change_rate() -> None:
    current_time = {"value": 0.0}
    limiter = RateLimiter(1.0, clock=lambda: current_time["value"])

    assert limiter.allow() is True
    limiter.set_rate(4.0)
    assert limiter.allow() is True
