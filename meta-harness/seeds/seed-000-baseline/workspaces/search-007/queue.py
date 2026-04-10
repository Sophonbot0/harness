"""
queue.py – Priority-based notification queue.
"""
import heapq
import threading
from typing import Optional
from providers import Notification


class NotificationQueue:
    """Thread-safe priority queue for Notification objects.

    Lower priority number = higher urgency (min-heap).
    """

    def __init__(self):
        self._heap: list = []
        self._lock = threading.Lock()
        self._counter = 0        # tie-breaker to keep FIFO order within same priority

    def enqueue(self, notification: Notification) -> None:
        """Add a notification. Priority taken from notification.priority."""
        with self._lock:
            heapq.heappush(self._heap, (notification.priority, self._counter, notification))
            self._counter += 1

    def dequeue(self) -> Optional[Notification]:
        """Remove and return the highest-priority notification, or None if empty."""
        with self._lock:
            if not self._heap:
                return None
            _, _, notification = heapq.heappop(self._heap)
            return notification

    def peek(self) -> Optional[Notification]:
        """Return the highest-priority notification without removing it."""
        with self._lock:
            if not self._heap:
                return None
            _, _, notification = self._heap[0]
            return notification

    def size(self) -> int:
        with self._lock:
            return len(self._heap)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._heap) == 0

    def drain(self) -> list:
        """Return all notifications in priority order, clearing the queue."""
        result = []
        while not self.is_empty():
            result.append(self.dequeue())
        return result
