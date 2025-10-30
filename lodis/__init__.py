"""
Lodis - A lightweight, in-memory key-value store with TTL expiration.
Redis-compatible API for drop-in replacement when Redis server is not available.
"""

from .constants import __version__
from .core import Lodis

# Provide Redis alias for drop-in replacement
Redis = Lodis

__all__ = ["Lodis", "Redis", "__version__"]
