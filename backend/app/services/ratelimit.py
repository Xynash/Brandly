import math
import time
from collections import defaultdict, deque
from threading import Lock


class SlidingWindowLimiter:
    """In-memory limiter: at most `limit` hits per key within `window` seconds.

    Lives inside one server process. When Brandly runs on several servers, this moves to Redis.
    """

    def __init__(self, window_seconds: float = 60.0):
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._next_cleanup = float("-inf")

    def hit(self, key: str, limit: int, now: float | None = None) -> int | None:
        """Record a hit. Returns None if allowed, else the seconds to wait before retrying."""
        if limit <= 0:
            return math.ceil(self.window)
        now = time.monotonic() if now is None else now
        with self._lock:
            if now >= self._next_cleanup:
                cutoff = now - self.window
                for expired in [key for key, hits in self._hits.items() if hits[-1] <= cutoff]:
                    del self._hits[expired]
                self._next_cleanup = now + self.window
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, math.ceil(hits[0] + self.window - now))
            hits.append(now)
            return None
