"""In-process LRU cache for the redirect hot path.

Redirects are the highest-volume, most latency-sensitive operation. Caching the
``short_code -> long_url`` mapping avoids a database round-trip for popular
links. The interface (``get``/``set``/``invalidate``) is deliberately tiny so it
can be replaced by a distributed cache (e.g. Redis) without touching callers.

The implementation is an ``OrderedDict``-based LRU and is guarded by a lock so it
is safe to share across request threads.
"""

from __future__ import annotations

import threading
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int = 1024) -> None:
        if capacity <= 0:
            raise ValueError("Cache capacity must be positive.")
        self._capacity = capacity
        self._store: "OrderedDict[str, str]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> str | None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self.hits += 1
                return self._store[key]
            self.misses += 1
            return None

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._store[key] = value
            self._store.move_to_end(key)
            if len(self._store) > self._capacity:
                self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
