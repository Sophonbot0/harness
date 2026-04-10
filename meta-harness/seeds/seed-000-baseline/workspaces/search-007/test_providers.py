"""
test_providers.py – Unit tests for EmailProvider and WebhookProvider.
"""
import sys
sys.path.insert(0, "/tmp/search-007")

import pytest
from providers import Notification, EmailProvider, WebhookProvider, NotificationProvider


def make_notif(nid="n1", recipient="user@example.com", priority=5):
    return Notification(id=nid, recipient=recipient,
                        subject="Hello", body="World", priority=priority)


# ── Abstract base ────────────────────────────────────────────────────────────

def test_provider_is_abstract():
    with pytest.raises(TypeError):
        NotificationProvider()  # type: ignore


# ── EmailProvider ────────────────────────────────────────────────────────────

class TestEmailProvider:
    def test_name(self):
        ep = EmailProvider()
        assert ep.name == "EmailProvider"

    def test_send_success(self):
        ep = EmailProvider()
        n = make_notif()
        assert ep.send(n) is True

    def test_sent_list_updated(self):
        ep = EmailProvider()
        n = make_notif()
        ep.send(n)
        assert len(ep.sent) == 1
        assert ep.sent[0] is n

    def test_forced_failure(self):
        ep = EmailProvider(fail_on="bad@example.com")
        n = make_notif(recipient="bad@example.com")
        assert ep.send(n) is False

    def test_forced_failure_does_not_update_sent(self):
        ep = EmailProvider(fail_on="bad@example.com")
        n = make_notif(recipient="bad@example.com")
        ep.send(n)
        assert ep.sent == []

    def test_multiple_sends(self):
        ep = EmailProvider()
        for i in range(5):
            ep.send(make_notif(nid=str(i)))
        assert len(ep.sent) == 5


# ── WebhookProvider ──────────────────────────────────────────────────────────

class TestWebhookProvider:
    def test_name(self):
        wp = WebhookProvider()
        assert wp.name == "WebhookProvider"

    def test_fail_always(self):
        wp = WebhookProvider(fail_always=True)
        assert wp.send(make_notif()) is False

    def test_fail_always_does_not_update_sent(self):
        wp = WebhookProvider(fail_always=True)
        wp.send(make_notif())
        assert wp.sent == []

    def test_connection_error_returns_false(self):
        """URL that won't connect should return False, not raise."""
        wp = WebhookProvider(url="http://127.0.0.1:19999/nonexistent", timeout=1)
        result = wp.send(make_notif())
        assert result is False

    def test_sent_list_after_success(self):
        """If a real server responds 200, sent list is updated."""
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                self.rfile.read(length)
                self.send_response(200)
                self.end_headers()
            def log_message(self, *args): pass

        server = HTTPServer(("127.0.0.1", 0), _Handler)
        port = server.server_address[1]
        t = threading.Thread(target=server.handle_request)
        t.start()
        wp = WebhookProvider(url=f"http://127.0.0.1:{port}/hook")
        n = make_notif()
        assert wp.send(n) is True
        assert len(wp.sent) == 1
        t.join()
