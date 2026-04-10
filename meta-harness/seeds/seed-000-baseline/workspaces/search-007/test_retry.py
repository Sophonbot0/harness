"""
test_retry.py – Unit tests for RetryHandler.
"""
import sys
sys.path.insert(0, "/tmp/search-007")

import pytest
from unittest.mock import MagicMock, call
from providers import Notification, NotificationProvider
from retry import RetryHandler


def make_notif(nid="n1"):
    return Notification(id=nid, recipient="u@x.com",
                        subject="s", body="b", priority=5)


def make_provider(*, always_fail=False, fail_times=0):
    """Return a mock provider."""
    provider = MagicMock(spec=NotificationProvider)
    provider.name = "MockProvider"
    if always_fail:
        provider.send.return_value = False
    elif fail_times > 0:
        provider.send.side_effect = ([False] * fail_times) + [True]
    else:
        provider.send.return_value = True
    return provider


class TestRetryHandler:
    def test_success_first_try(self):
        handler = RetryHandler(max_retries=3, base_delay=0)
        p = make_provider()
        result = handler.send_with_retry(p, make_notif())
        assert result is True
        assert p.send.call_count == 1

    def test_retries_on_failure_then_succeeds(self):
        sleep_calls = []
        handler = RetryHandler(max_retries=3, base_delay=0.1,
                               _sleep_fn=sleep_calls.append)
        p = make_provider(fail_times=2)
        result = handler.send_with_retry(p, make_notif())
        assert result is True
        assert p.send.call_count == 3
        assert len(sleep_calls) == 2  # slept between attempts

    def test_exponential_backoff_delays(self):
        delays = []
        handler = RetryHandler(max_retries=4, base_delay=1.0, backoff_factor=2.0,
                               _sleep_fn=delays.append)
        p = make_provider(always_fail=True)
        handler.send_with_retry(p, make_notif())
        # 3 sleeps between 4 attempts
        assert delays == [1.0, 2.0, 4.0]

    def test_all_retries_exhausted_adds_to_dlq(self):
        handler = RetryHandler(max_retries=3, base_delay=0, _sleep_fn=lambda _: None)
        p = make_provider(always_fail=True)
        n = make_notif("dead")
        result = handler.send_with_retry(p, n)
        assert result is False
        assert len(handler.dead_letter_queue) == 1
        assert handler.dead_letter_queue[0].id == "dead"

    def test_clear_dead_letter(self):
        handler = RetryHandler(max_retries=1, base_delay=0, _sleep_fn=lambda _: None)
        p = make_provider(always_fail=True)
        handler.send_with_retry(p, make_notif())
        assert len(handler.dead_letter_queue) == 1
        handler.clear_dead_letter()
        assert handler.dead_letter_queue == []

    def test_max_retries_one_no_sleep(self):
        """With max_retries=1 there should be no sleep call."""
        delays = []
        handler = RetryHandler(max_retries=1, base_delay=1.0, _sleep_fn=delays.append)
        p = make_provider(always_fail=True)
        handler.send_with_retry(p, make_notif())
        assert delays == []

    def test_invalid_max_retries_raises(self):
        with pytest.raises(ValueError):
            RetryHandler(max_retries=0)

    def test_delay_cap_respected(self):
        delays = []
        handler = RetryHandler(max_retries=5, base_delay=10.0, backoff_factor=10.0,
                               delay_cap=20.0, _sleep_fn=delays.append)
        p = make_provider(always_fail=True)
        handler.send_with_retry(p, make_notif())
        assert all(d <= 20.0 for d in delays)
