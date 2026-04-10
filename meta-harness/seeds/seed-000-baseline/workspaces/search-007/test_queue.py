"""
test_queue.py – Unit tests for NotificationQueue.
"""
import sys
sys.path.insert(0, "/tmp/search-007")

import pytest
from providers import Notification
from queue import NotificationQueue


def notif(nid, priority=5):
    return Notification(id=nid, recipient="r@x.com",
                        subject="s", body="b", priority=priority)


class TestNotificationQueue:
    def test_initial_empty(self):
        q = NotificationQueue()
        assert q.is_empty()
        assert q.size() == 0

    def test_enqueue_dequeue(self):
        q = NotificationQueue()
        n = notif("a")
        q.enqueue(n)
        assert q.size() == 1
        assert not q.is_empty()
        result = q.dequeue()
        assert result is n
        assert q.is_empty()

    def test_priority_order(self):
        q = NotificationQueue()
        q.enqueue(notif("low", priority=9))
        q.enqueue(notif("high", priority=1))
        q.enqueue(notif("mid", priority=5))
        assert q.dequeue().id == "high"
        assert q.dequeue().id == "mid"
        assert q.dequeue().id == "low"

    def test_peek_does_not_remove(self):
        q = NotificationQueue()
        n = notif("x")
        q.enqueue(n)
        assert q.peek() is n
        assert q.size() == 1

    def test_dequeue_empty_returns_none(self):
        q = NotificationQueue()
        assert q.dequeue() is None

    def test_peek_empty_returns_none(self):
        q = NotificationQueue()
        assert q.peek() is None

    def test_drain(self):
        q = NotificationQueue()
        for i in range(3):
            q.enqueue(notif(str(i)))
        items = q.drain()
        assert len(items) == 3
        assert q.is_empty()

    def test_fifo_within_same_priority(self):
        q = NotificationQueue()
        q.enqueue(notif("first", priority=5))
        q.enqueue(notif("second", priority=5))
        q.enqueue(notif("third", priority=5))
        assert q.dequeue().id == "first"
        assert q.dequeue().id == "second"
        assert q.dequeue().id == "third"
