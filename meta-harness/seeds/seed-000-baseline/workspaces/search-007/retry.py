"""
retry.py – RetryHandler with exponential backoff and dead-letter queue.
"""
import time
import logging
from typing import Callable, List, Optional
from providers import Notification, NotificationProvider

logger = logging.getLogger(__name__)


class RetryHandler:
    """Wraps provider send() with exponential backoff and a dead-letter queue.

    Parameters
    ----------
    max_retries : int
        Maximum number of attempts (including the first try).
    base_delay  : float
        Initial delay in seconds; doubles on each subsequent retry.
    backoff_factor : float
        Multiplier applied to the delay on each retry (default 2.0).
    delay_cap   : float
        Maximum delay between retries in seconds.
    _sleep_fn   : callable (injected for tests to avoid real sleeping)
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 backoff_factor: float = 2.0, delay_cap: float = 60.0,
                 _sleep_fn: Optional[Callable[[float], None]] = None):
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.delay_cap = delay_cap
        self._sleep = _sleep_fn if _sleep_fn is not None else time.sleep
        self._dead_letter: List[Notification] = []

    @property
    def dead_letter_queue(self) -> List[Notification]:
        return list(self._dead_letter)

    def send_with_retry(self, provider: NotificationProvider,
                        notification: Notification) -> bool:
        """Attempt to send via *provider*, retrying on failure.

        Returns True if any attempt succeeds, False if all attempts are
        exhausted (notification is added to the dead-letter queue).
        """
        delay = self.base_delay
        for attempt in range(1, self.max_retries + 1):
            success = provider.send(notification)
            if success:
                logger.info("RetryHandler: delivered on attempt %d (id=%s)",
                            attempt, notification.id)
                return True
            if attempt < self.max_retries:
                logger.warning(
                    "RetryHandler: attempt %d failed for id=%s; retrying in %.1fs",
                    attempt, notification.id, delay
                )
                self._sleep(delay)
                delay = min(delay * self.backoff_factor, self.delay_cap)
            else:
                logger.error(
                    "RetryHandler: all %d attempts failed for id=%s; adding to DLQ",
                    self.max_retries, notification.id
                )
        self._dead_letter.append(notification)
        return False

    def clear_dead_letter(self) -> None:
        self._dead_letter.clear()
