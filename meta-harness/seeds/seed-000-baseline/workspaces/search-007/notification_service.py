"""
notification_service.py – NotificationService orchestrating providers, queue, and retry.
"""
import logging
import threading
from typing import Dict, List, Optional
from providers import Notification, NotificationProvider
from queue import NotificationQueue
from retry import RetryHandler

logger = logging.getLogger(__name__)


class NotificationService:
    """Central service that enqueues notifications and dispatches them.

    Providers are registered by name.  dispatch_all() drains the queue and
    attempts delivery via all registered providers using the RetryHandler.
    """

    def __init__(self, retry_handler: Optional[RetryHandler] = None):
        self._providers: Dict[str, NotificationProvider] = {}
        self._queue = NotificationQueue()
        self._retry = retry_handler or RetryHandler(max_retries=3, base_delay=0.0)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Provider management
    # ------------------------------------------------------------------ #

    def register_provider(self, provider: NotificationProvider) -> None:
        with self._lock:
            self._providers[provider.name] = provider
            logger.info("NotificationService: registered provider '%s'", provider.name)

    def unregister_provider(self, name: str) -> bool:
        with self._lock:
            if name in self._providers:
                del self._providers[name]
                return True
            return False

    def provider_names(self) -> List[str]:
        with self._lock:
            return list(self._providers.keys())

    # ------------------------------------------------------------------ #
    # Queue management
    # ------------------------------------------------------------------ #

    def enqueue(self, notification: Notification) -> None:
        self._queue.enqueue(notification)
        logger.info("NotificationService: enqueued id=%s priority=%d",
                    notification.id, notification.priority)

    def queue_size(self) -> int:
        return self._queue.size()

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #

    def dispatch_all(self) -> Dict[str, int]:
        """Drain the queue and dispatch every notification to every provider.

        Returns a summary dict:
          {"dispatched": N, "succeeded": N, "failed": N}
        """
        results = {"dispatched": 0, "succeeded": 0, "failed": 0}
        with self._lock:
            providers = dict(self._providers)

        while not self._queue.is_empty():
            notification = self._queue.dequeue()
            if notification is None:
                break
            results["dispatched"] += 1
            for pname, provider in providers.items():
                ok = self._retry.send_with_retry(provider, notification)
                if ok:
                    results["succeeded"] += 1
                else:
                    results["failed"] += 1
                    logger.error(
                        "NotificationService: notification id=%s FAILED on provider '%s'",
                        notification.id, pname
                    )

        return results

    @property
    def dead_letter_queue(self) -> list:
        return self._retry.dead_letter_queue
