"""
Key management and database operations for Lodis - Redis-compatible management commands.
"""

import time
import fnmatch
import random

from .constants import (
    NUM_DATABASES,
    NO_EXPIRATION,
    TYPE_STRING,
    TYPE_LIST,
    TYPE_SET,
    TYPE_ZSET,
    TYPE_HASH
)


class ManagementMixin:
    """
    Mixin class providing Redis-compatible key management and database operations.
    """

    # Key Management Operations

    def delete(self, *keys):
        """
        Delete one or more keys.

        Args:
            keys: One or more key names to delete

        Returns:
            Number of keys that were deleted
        """
        deleted_count = 0
        with self.mutex:
            for key in keys:
                if key in self._keys:
                    del self._keys[key]
                    deleted_count += 1

        return deleted_count

    def keys(self, pattern='*'):
        """
        Return all keys matching pattern.

        Args:
            pattern: Glob pattern to match (default '*' for all)

        Returns:
            List of keys matching pattern
        """
        _matching_keys = []
        _tmp_keys = self._keys.copy()

        for key in _tmp_keys:
            data_type, _ = self._is_expired(key)
            if data_type is not None:  # Key exists and not expired
                if fnmatch.fnmatch(key, pattern):
                    _matching_keys.append(key)

        return sorted(_matching_keys)

    def exists(self, *keys):
        """
        Check if keys exist.

        Args:
            keys: One or more key names

        Returns:
            Number of existing keys
        """
        count = 0
        for key in keys:
            data_type, _ = self._is_expired(key)
            if data_type is not None:
                count += 1

        return count

    def type(self, key):
        """
        Determine the type stored at key (Redis TYPE command).

        Args:
            key: The key name

        Returns:
            String indicating type: 'string', 'list', 'set', 'zset', 'hash', or 'none'
        """
        data_type, _ = self._is_expired(key)

        if data_type is None:
            return 'none'
        elif data_type == TYPE_STRING:
            return 'string'
        elif data_type == TYPE_LIST:
            return 'list'
        elif data_type == TYPE_SET:
            return 'set'
        elif data_type == TYPE_ZSET:
            return 'zset'
        elif data_type == TYPE_HASH:
            return 'hash'
        else:
            return 'none'

    def rename(self, key, newkey):
        """
        Rename a key (Redis RENAME command).

        Args:
            key: The old key name
            newkey: The new key name

        Returns:
            True if successful

        Raises:
            KeyError: If key doesn't exist
        """
        data_type, _ = self._is_expired(key)
        if data_type is None:
            raise KeyError("no such key")

        with self.mutex:
            # Copy the key data
            self._keys[newkey] = self._keys[key]
            # Delete the old key
            del self._keys[key]

        return True

    def renamenx(self, key, newkey):
        """
        Rename key to newkey only if newkey doesn't exist (Redis RENAMENX command).

        Args:
            key: The old key name
            newkey: The new key name

        Returns:
            1 if key was renamed, 0 if newkey already exists

        Raises:
            KeyError: If key doesn't exist
        """
        data_type, _ = self._is_expired(key)
        if data_type is None:
            raise KeyError("no such key")

        # Check if newkey exists
        newkey_type, _ = self._is_expired(newkey)
        if newkey_type is not None:
            return 0

        with self.mutex:
            self._keys[newkey] = self._keys[key]
            del self._keys[key]

        return 1

    def persist(self, key):
        """
        Remove expiration from key (Redis PERSIST command).

        Args:
            key: The key name

        Returns:
            1 if TTL was removed, 0 if key doesn't exist or has no TTL
        """
        data_type, data = self._is_expired(key)
        if data_type is None:
            return 0

        # Check if key already has no expiration
        expire, _, _ = self._keys[key]
        if expire >= time.time() + NO_EXPIRATION - 1:
            # Already persistent (no meaningful expiration)
            return 0

        # Set expiration to "no expiration"
        new_expire = time.time() + NO_EXPIRATION
        with self.mutex:
            self._keys[key] = (new_expire, data_type, data)

        return 1

    def randomkey(self):
        """
        Return a random key from the current database (Redis RANDOMKEY command).

        Returns:
            Random key name, or None if database is empty
        """
        # Get all non-expired keys
        valid_keys = []
        for key in self._keys.copy():
            data_type, _ = self._is_expired(key)
            if data_type is not None:
                valid_keys.append(key)

        if not valid_keys:
            return None

        return random.choice(valid_keys)

    def scan(self, cursor=0, match=None, count=None):
        """
        Incrementally iterate over keys (Redis SCAN command).

        Args:
            cursor: The cursor position (0 to start)
            match: Pattern to match keys (optional)
            count: Hint for number of keys to return (optional, default 10)

        Returns:
            Tuple of (next_cursor, list_of_keys)
        """
        if count is None:
            count = 10

        # Get all non-expired keys
        all_keys = []
        for key in self._keys.copy():
            data_type, _ = self._is_expired(key)
            if data_type is not None:
                if match is None or fnmatch.fnmatch(key, match):
                    all_keys.append(key)

        all_keys = sorted(all_keys)

        # Get slice of keys starting from cursor
        start = cursor
        end = start + count
        result_keys = all_keys[start:end]

        # Calculate next cursor (0 if we've reached the end)
        next_cursor = end if end < len(all_keys) else 0

        return (next_cursor, result_keys)

    # Expiration Operations

    def expire(self, key, seconds):
        """
        Set expiration on key in seconds.

        Args:
            key: The key name
            seconds: Expiration time in seconds

        Returns:
            True if timeout was set, False if key doesn't exist
        """
        # Check if key exists
        if key in self._keys:
            data_type, data = self._is_expired(key)
            if data_type is not None:
                expire = time.time() + seconds
                with self.mutex:
                    self._keys[key] = (expire, data_type, data)
                return True

        return False

    def ttl(self, key):
        """
        Get time to live for key in seconds.

        Args:
            key: The key name

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist
        """
        if key in self._keys:
            entry = self._keys.get(key, None)
            if entry is None:
                return -2  # Key doesn't exist

            expire, data_type, data = entry

            current_time = time.time()
            if expire < current_time:
                # Key expired, clean it up
                with self.mutex:
                    del self._keys[key]
                return -2

            # Check if it's effectively non-expiring (our 100-year hack)
            if expire - current_time > (50 * 365 * 24 * 3600):  # More than 50 years
                return -1  # No expiration

            return int(expire - current_time)

        return -2

    def pttl(self, key):
        """
        Get time to live for key in milliseconds (Redis PTTL command).

        Args:
            key: The key name

        Returns:
            TTL in milliseconds, -1 if no expiration, -2 if key doesn't exist
        """
        if key in self._keys:
            entry = self._keys.get(key, None)
            if entry is None:
                return -2

            expire, data_type, data = entry

            current_time = time.time()
            if expire < current_time:
                # Key expired
                with self.mutex:
                    del self._keys[key]
                return -2

            # Check if it's effectively non-expiring
            if expire - current_time > (50 * 365 * 24 * 3600):
                return -1

            return int((expire - current_time) * 1000)

        return -2

    def expireat(self, key, timestamp):
        """
        Set expiration to Unix timestamp in seconds (Redis EXPIREAT command).

        Args:
            key: The key name
            timestamp: Unix timestamp in seconds

        Returns:
            1 if timeout was set, 0 if key doesn't exist
        """
        if key in self._keys:
            data_type, data = self._is_expired(key)
            if data_type is not None:
                with self.mutex:
                    self._keys[key] = (timestamp, data_type, data)
                return 1

        return 0

    def pexpire(self, key, milliseconds):
        """
        Set expiration in milliseconds (Redis PEXPIRE command).

        Args:
            key: The key name
            milliseconds: Expiration time in milliseconds

        Returns:
            1 if timeout was set, 0 if key doesn't exist
        """
        if key in self._keys:
            data_type, data = self._is_expired(key)
            if data_type is not None:
                expire = time.time() + (milliseconds / 1000.0)
                with self.mutex:
                    self._keys[key] = (expire, data_type, data)
                return 1

        return 0

    def pexpireat(self, key, timestamp_ms):
        """
        Set expiration to Unix timestamp in milliseconds (Redis PEXPIREAT command).

        Args:
            key: The key name
            timestamp_ms: Unix timestamp in milliseconds

        Returns:
            1 if timeout was set, 0 if key doesn't exist
        """
        if key in self._keys:
            data_type, data = self._is_expired(key)
            if data_type is not None:
                timestamp = timestamp_ms / 1000.0
                with self.mutex:
                    self._keys[key] = (timestamp, data_type, data)
                return 1

        return 0  # Key doesn't exist

    # Database Operations

    def select(self, db):
        """
        Switch to a different database.

        Args:
            db: Database number (0-15)

        Returns:
            True if successful

        Raises:
            ValueError: If db is not a valid database number
        """
        if not isinstance(db, int) or db < 0 or db >= NUM_DATABASES:
            raise ValueError(f"invalid DB index: {db} (must be 0-{NUM_DATABASES - 1})")

        self._current_db = db
        return True

    def flushdb(self):
        """
        Delete all keys from the current database only.

        Returns:
            True
        """
        with self.mutex:
            self._databases[self._current_db].clear()

        return True

    def flushall(self):
        """
        Delete all keys from all databases.

        Returns:
            True
        """
        with self.mutex:
            for db_num in range(NUM_DATABASES):
                self._databases[db_num].clear()

        return True

    def ping(self, message=None):
        """
        Test server connectivity (Redis PING command).

        Args:
            message: Optional message to echo back

        Returns:
            True if no message provided, otherwise returns the message
        """
        if message is None:
            return True
        return message

    def dbsize(self):
        """
        Return the number of keys in the current database (Redis DBSIZE command).

        Returns:
            Number of keys in current database
        """
        count = 0
        for key in self._keys.copy():
            data_type, _ = self._is_expired(key)
            if data_type is not None:
                count += 1
        return count
