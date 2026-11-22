"""Conservative per-process safeguards for paid Sarvam calls.

Production deployments with multiple workers or replicas must add a shared quota
and concurrency limiter (for example Redis); this limiter is intentionally local.
"""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager
import threading
import time
from typing import Iterator


class RequestLimitExceeded(RuntimeError):
    """The caller exceeded a local user quota or provider concurrency cap."""


class SarvamRequestLimiter:
    MAX_TRACKED_USERS = 10_000

    def __init__(
        self,
        *,
        per_minute: int = 10,
        per_hour: int = 60,
        max_concurrent: int = 2,
    ) -> None:
        if per_minute < 1 or per_hour < per_minute or max_concurrent < 1:
            raise ValueError("Sarvam limiter limits must be positive and internally consistent.")
        self.per_minute = per_minute
        self.per_hour = per_hour
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(max_concurrent)
        self._requests: dict[str, deque[float]] = {}

    @contextmanager
    def provider_slot(self, user_id: str) -> Iterator[None]:
        now = time.monotonic()
        with self._lock:
            timestamps = self._requests.get(user_id)
            if timestamps is None:
                if len(self._requests) >= self.MAX_TRACKED_USERS:
                    for key, values in list(self._requests.items()):
                        while values and now - values[0] >= 3600:
                            values.popleft()
                        if not values:
                            self._requests.pop(key, None)
                    if len(self._requests) >= self.MAX_TRACKED_USERS:
                        raise RequestLimitExceeded("Sarvam is busy. Please retry later.")
                timestamps = deque()
                self._requests[user_id] = timestamps
            while timestamps and now - timestamps[0] >= 3600:
                timestamps.popleft()
            minute_count = sum(now - value < 60 for value in timestamps)
            if minute_count >= self.per_minute or len(timestamps) >= self.per_hour:
                if not timestamps:
                    self._requests.pop(user_id, None)
                raise RequestLimitExceeded("Sarvam request quota exceeded. Please retry later.")
            if not self._slots.acquire(blocking=False):
                if not timestamps:
                    self._requests.pop(user_id, None)
                raise RequestLimitExceeded("Sarvam is busy. Please retry shortly.")
            timestamps.append(now)
            if len(self._requests) > 10_000:
                for key, values in list(self._requests.items()):
                    while values and now - values[0] >= 3600:
                        values.popleft()
                    if not values:
                        self._requests.pop(key, None)
        try:
            yield
        finally:
            self._slots.release()
