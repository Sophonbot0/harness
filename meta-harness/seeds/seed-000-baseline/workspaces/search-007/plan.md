# Notification System – Plan

## Overview
Build a Python notification system with providers, queue, retry, and full test coverage.

## Definition of Done (15 items)
1. `providers.py` contains abstract `NotificationProvider` base class
2. `providers.py` contains `EmailProvider` with `send()` method
3. `providers.py` contains `WebhookProvider` with `send()` method
4. `queue.py` contains `NotificationQueue` with priority support (heapq)
5. `queue.py` supports enqueue, dequeue, peek, size, and is_empty operations
6. `retry.py` contains `RetryHandler` with exponential backoff
7. `retry.py` supports configurable max_retries and base_delay
8. `retry.py` has a dead letter queue for exhausted retries
9. `notification_service.py` contains `NotificationService` that dispatches to providers
10. `NotificationService` supports registering multiple providers
11. `NotificationService` uses the queue and retry handler
12. `test_providers.py` has unit tests for Email and Webhook providers (≥6 tests)
13. `test_queue.py` has unit tests for NotificationQueue (≥5 tests)
14. `test_retry.py` has unit tests for RetryHandler (≥5 tests)
15. `test_integration.py` has an end-to-end integration test covering full pipeline
