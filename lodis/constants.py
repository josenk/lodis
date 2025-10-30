"""
Constants and configuration for Lodis.
"""

__version__ = "1.0.0"

# Redis supports 16 databases by default (0-15)
NUM_DATABASES = 16

# Default expiration time for keys without explicit TTL (100 years in seconds)
NO_EXPIRATION = 365 * 24 * 3600 * 100

# Data type constants for Redis-compatible data structures
TYPE_STRING = 'string'
TYPE_LIST = 'list'
TYPE_SET = 'set'
TYPE_ZSET = 'zset'
TYPE_HASH = 'hash'
