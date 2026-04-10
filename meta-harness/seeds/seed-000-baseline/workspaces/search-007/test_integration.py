"""
test_integration.py – End-to-end integration test for the full pipeline.
"""
import sys
sys.path.insert(0, "/tmp/search-007")

import pytest
from providers import Notification, EmailProvider, WebhookProvider
from queue import NotificationQueue
from retry import RetryHandler
from notification_service import NotificationService


def make_notif(nid, priority=5, recipient="user@example.com"):
    return Notification(id=nid, recipient=recipient,
                        subject=f"Subject {nid}", body=f"Body {nid}",
                        priority=priority)


class TestIntegrationPipeline:
    """Full pipeline: enqueue → dispatch → provider → retry → result."""

    def test_single_notification_email(self):
        retry = RetryHandler(max_retries=3, base_delay=0, _sleep_fn=lambda _: None)
        svc = NotificationService(retry_handler=retry)
        ep = EmailProvider()
        svc.register_provider(ep)
        svc.enqueue(make_notif("i1"))
        result = svc.dispatch_all()
        assert result["dispatched"] == 1
        assert result["succeeded"] == 1
        assert result["failed"] == 0
        assert len(ep.sent) == 1
        assert ep.sent[0].id == "i1"

    def test_multiple_notifications_priority_order(self):
        retry = RetryHandler(max_retries=1, base_delay=0, _sleep_fn=lambda _: None)
        svc = NotificationService(retry_handler=retry)
        ep = EmailProvider()
        svc.register_provider(ep)
        svc.enqueue(make_notif("low", priority=9))
        svc.enqueue(make_notif("high", priority=1))
        svc.enqueue(make_notif("mid", priority=5))
        svc.dispatch_all()
        ids = [n.id for n in ep.sent]
        assert ids == ["high", "mid", "low"]

    def test_failed_provider_ends_in_dlq(self):
        retry = RetryHandler(max_retries=2, base_delay=0, _sleep_fn=lambda _: None)
        svc = NotificationService(retry_handler=retry)
        ep = EmailProvider(fail_on="bad@example.com")
        svc.register_provider(ep)
        svc.enqueue(make_notif("dlq1", recipient="bad@example.com"))
        result = svc.dispatch_all()
        assert result["failed"] == 1
        assert len(svc.dead_letter_queue) == 1
        assert svc.dead_letter_queue[0].id == "dlq1"

    def test_multiple_providers(self):
        retry = RetryHandler(max_retries=1, base_delay=0, _sleep_fn=lambda _: None)
        svc = NotificationService(retry_handler=retry)
        ep = EmailProvider()
        wp = WebhookProvider(fail_always=True)
        svc.register_provider(ep)
        svc.register_provider(wp)
        svc.enqueue(make_notif("m1"))
        result = svc.dispatch_all()
        # 1 notification × 2 providers
        assert result["dispatched"] == 1
        assert result["succeeded"] == 1   # email OK
        assert result["failed"] == 1      # webhook failed

    def test_queue_empty_after_dispatch(self):
        svc = NotificationService()
        ep = EmailProvider()
        svc.register_provider(ep)
        for i in range(5):
            svc.enqueue(make_notif(str(i)))
        assert svc.queue_size() == 5
        svc.dispatch_all()
        assert svc.queue_size() == 0

    def test_retry_eventually_succeeds(self):
        """Provider fails twice then succeeds; retry makes it through."""
        from unittest.mock import MagicMock
        from providers import NotificationProvider
        p = MagicMock(spec=NotificationProvider)
        p.name = "FlakeyProvider"
        p.send.side_effect = [False, False, True]

        retry = RetryHandler(max_retries=3, base_delay=0, _sleep_fn=lambda _: None)
        svc = NotificationService(retry_handler=retry)
        svc.register_provider(p)
        svc.enqueue(make_notif("flakey"))
        result = svc.dispatch_all()
        assert result["succeeded"] == 1
        assert p.send.call_count == 3

    def test_no_providers_registered(self):
        svc = NotificationService()
        svc.enqueue(make_notif("orphan"))
        result = svc.dispatch_all()
        assert result["dispatched"] == 1
        assert result["succeeded"] == 0
        assert result["failed"] == 0

    def test_unregister_provider(self):
        svc = NotificationService()
        ep = EmailProvider()
        svc.register_provider(ep)
        assert "EmailProvider" in svc.provider_names()
        svc.unregister_provider("EmailProvider")
        assert "EmailProvider" not in svc.provider_names()
