import threading


class ThreadSafeCounter:
    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._count += 1

    def get(self):
        with self._lock:
            return self._count

    def reset(self):
        with self._lock:
            self._count = 0
