"""
rate_limiter.py - In-memory sliding window rate limiter
"""
import time
from collections import defaultdict, deque
import threading


class RateLimiter:
    """
    Sliding window rate limiter.
    Allows `max_requests` per `window_seconds` per client key.
    """

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._windows: dict[str, deque] = defaultdict(deque)

    def is_allowed(self, client_key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            dq = self._windows[client_key]
            # Remove expired timestamps
            while dq and dq[0] <= cutoff:
                dq.popleft()
            if len(dq) >= self.max_requests:
                return False
            dq.append(now)
            return True

    def reset(self, client_key: str):
        with self._lock:
            self._windows[client_key] = deque()

    def remaining(self, client_key: str) -> int:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            dq = self._windows[client_key]
            while dq and dq[0] <= cutoff:
                dq.popleft()
            return max(0, self.max_requests - len(dq))
