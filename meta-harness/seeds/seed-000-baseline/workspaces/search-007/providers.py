"""
providers.py – Abstract base and concrete notification providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging
import urllib.request
import urllib.error
import json

logger = logging.getLogger(__name__)


@dataclass
class Notification:
    """Represents a single notification message."""
    id: str
    recipient: str
    subject: str
    body: str
    priority: int = 5          # 1 (highest) … 10 (lowest)
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationProvider(ABC):
    """Abstract base class for all notification providers."""

    @abstractmethod
    def send(self, notification: Notification) -> bool:
        """Send a notification. Returns True on success, False on failure."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""


class EmailProvider(NotificationProvider):
    """Simulated e-mail provider (real SMTP would go here)."""

    def __init__(self, smtp_host: str = "localhost", smtp_port: int = 25,
                 fail_on: Optional[str] = None):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._fail_on = fail_on          # recipient address that always fails (testing)
        self._sent: list = []

    @property
    def name(self) -> str:
        return "EmailProvider"

    @property
    def sent(self) -> list:
        return list(self._sent)

    def send(self, notification: Notification) -> bool:
        if self._fail_on and notification.recipient == self._fail_on:
            logger.warning("EmailProvider: forced failure for %s", notification.recipient)
            return False
        # Simulate sending
        self._sent.append(notification)
        logger.info("EmailProvider: sent email to %s (id=%s)", notification.recipient, notification.id)
        return True


class WebhookProvider(NotificationProvider):
    """HTTP webhook provider."""

    def __init__(self, url: str = "http://localhost:9999/hook",
                 timeout: int = 5, fail_always: bool = False):
        self._url = url
        self._timeout = timeout
        self._fail_always = fail_always
        self._sent: list = []

    @property
    def name(self) -> str:
        return "WebhookProvider"

    @property
    def sent(self) -> list:
        return list(self._sent)

    def send(self, notification: Notification) -> bool:
        if self._fail_always:
            logger.warning("WebhookProvider: forced failure (fail_always=True)")
            return False
        payload = json.dumps({
            "id": notification.id,
            "recipient": notification.recipient,
            "subject": notification.subject,
            "body": notification.body,
        }).encode()
        try:
            req = urllib.request.Request(
                self._url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout):
                pass
            self._sent.append(notification)
            logger.info("WebhookProvider: sent webhook for id=%s", notification.id)
            return True
        except (urllib.error.URLError, OSError) as exc:
            logger.warning("WebhookProvider: request failed – %s", exc)
            # In tests the URL won't exist; treat connection error as failure
            return False
