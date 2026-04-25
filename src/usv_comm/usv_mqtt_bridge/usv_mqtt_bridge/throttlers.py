"""Rate-limiting helpers for telemetry publishing."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable


Clock = Callable[[], float]


@dataclass
class RateLimiter:
    """Allow one event per configured rate window."""

    rate_hz: float
    clock: Clock = time.monotonic

    def __post_init__(self) -> None:
        self._next_allowed_time = 0.0
        self.set_rate(self.rate_hz)

    def set_rate(self, rate_hz: float) -> None:
        """Update the rate limit in hertz."""

        if rate_hz <= 0:
            raise ValueError("rate_hz must be positive.")
        self.rate_hz = rate_hz
        self._period = 1.0 / rate_hz
        self._next_allowed_time = 0.0

    def allow(self) -> bool:
        """Return True if an event can pass right now."""

        now = self.clock()
        if now + math.ulp(1.0) < self._next_allowed_time:
            return False
        self._next_allowed_time = now + self._period
        return True
