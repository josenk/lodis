"""
Core implementation of Lodis - A lightweight, in-memory key-value store.
Redis-compatible API for drop-in replacement when Redis server is not available.

This module assembles all the mixin classes into the main Lodis class.
"""

from .base import LodisBase
from .strings import StringsMixin
from .lists import ListsMixin
from .sets import SetsMixin
from .sorted_sets import SortedSetsMixin
from .management import ManagementMixin


class Lodis(LodisBase, StringsMixin, ListsMixin, SetsMixin, SortedSetsMixin, ManagementMixin):
    """
    Redis-compatible in-memory key-value store with TTL expiration support.

    This class provides a subset of Redis functionality for use when a Redis
    server is not available or not needed. All data is stored in memory and
    thread-safe operations are provided via mutex locks.

    The class is composed of the following mixins:
    - LodisBase: Core structure and helper methods
    - StringsMixin: String operations (GET, SET, INCR, etc.)
    - ListsMixin: List operations (LPUSH, RPUSH, LPOP, etc.)
    - SetsMixin: Set operations (SADD, SREM, SINTER, etc.)
    - SortedSetsMixin: Sorted set operations (ZADD, ZRANGE, etc.)
    - ManagementMixin: Key management and database operations
    """
    pass
