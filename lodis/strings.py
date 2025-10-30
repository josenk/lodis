"""
String operations for Lodis - Redis-compatible string commands.
"""

import time

from .constants import NO_EXPIRATION, TYPE_STRING


class StringsMixin:
    """
    Mixin class providing Redis-compatible string operations.
    """

    def set(self, key, value, ex=None, px=None, nx=False, xx=False):
        """
        Set key to value with optional expiration and conditions.

        Args:
            key: The key name
            value: The value to store
            ex: Expire time in seconds
            px: Expire time in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key already exists

        Returns:
            True if successful, None if nx/xx conditions not met
        """
        # Check nx/xx conditions
        data_type, _ = self._is_expired(key)
        key_exists = data_type is not None

        if nx and key_exists:
            return None
        if xx and not key_exists:
            return None

        # Calculate expiration
        if ex is not None:
            expire = time.time() + ex
        elif px is not None:
            expire = time.time() + (px / 1000.0)
        else:
            # No expiration - use very large timestamp
            expire = time.time() + NO_EXPIRATION

        with self.mutex:
            self._keys[key] = (expire, TYPE_STRING, value)

        return True

    def setex(self, key, seconds, value):
        """
        Set key to value with expiration in seconds (Redis SETEX command).

        Args:
            key: The key name
            seconds: Expiration time in seconds
            value: The value to store

        Returns:
            True if successful
        """
        return self.set(key, value, ex=seconds)

    def psetex(self, key, milliseconds, value):
        """
        Set key to value with expiration in milliseconds (Redis PSETEX command).

        Args:
            key: The key name
            milliseconds: Expiration time in milliseconds
            value: The value to store

        Returns:
            True if successful
        """
        return self.set(key, value, px=milliseconds)

    def setnx(self, key, value):
        """
        Set key to value only if key does not exist (Redis SETNX command).

        Args:
            key: The key name
            value: The value to store

        Returns:
            True if key was set, False if key already exists
        """
        result = self.set(key, value, nx=True)
        return result is not None

    def get(self, key):
        """
        Get value for key.

        Args:
            key: The key name

        Returns:
            Value if key exists and not expired, None otherwise
        """
        return self._get_typed_data(key, TYPE_STRING)

    def mget(self, *keys):
        """
        Get values of multiple keys (Redis MGET command).

        Args:
            keys: One or more key names

        Returns:
            List of values (None for keys that don't exist)
        """
        return [self.get(key) for key in keys]

    def mset(self, mapping):
        """
        Set multiple keys to multiple values atomically (Redis MSET command).

        Args:
            mapping: Dictionary of key-value pairs

        Returns:
            True if successful
        """
        with self.mutex:
            expire = time.time() + NO_EXPIRATION
            for key, value in mapping.items():
                self._keys[key] = (expire, TYPE_STRING, value)
        return True

    def getset(self, key, value):
        """
        Set key to value and return the old value (Redis GETSET command).

        Args:
            key: The key name
            value: The new value to set

        Returns:
            Old value if key existed, None otherwise
        """
        old_value = self.get(key)
        self.set(key, value)
        return old_value

    def append(self, key, value):
        """
        Append a value to a key (Redis APPEND command).

        Args:
            key: The key name
            value: The value to append

        Returns:
            Length of the string after append
        """
        current = self.get(key)
        if current is None:
            # Key doesn't exist, create it with the value
            new_value = str(value)
        else:
            # Append to existing value
            new_value = str(current) + str(value)

        self.set(key, new_value)
        return len(new_value)

    def strlen(self, key):
        """
        Get the length of the value stored at key (Redis STRLEN command).

        Args:
            key: The key name

        Returns:
            Length of string, or 0 if key doesn't exist
        """
        value = self.get(key)
        return len(str(value)) if value is not None else 0

    def getdel(self, key):
        """
        Get the value of key and delete it atomically (Redis GETDEL command).

        Args:
            key: The key name

        Returns:
            Value if key existed, None otherwise
        """
        value = self.get(key)
        if value is not None:
            self.delete(key)
        return value

    def getex(self, key, ex=None, px=None, exat=None, pxat=None, persist=False):
        """
        Get the value and optionally set expiration (Redis GETEX command).

        Args:
            key: The key name
            ex: Expire time in seconds
            px: Expire time in milliseconds
            exat: Expire at Unix timestamp in seconds
            pxat: Expire at Unix timestamp in milliseconds
            persist: Remove expiration

        Returns:
            Value if key exists, None otherwise
        """
        value = self.get(key)

        if value is not None:
            if persist:
                self.persist(key)
            elif ex is not None:
                self.expire(key, ex)
            elif px is not None:
                self.pexpire(key, px)
            elif exat is not None:
                self.expireat(key, exat)
            elif pxat is not None:
                self.pexpireat(key, pxat)

        return value

    def incr(self, key, amount=1):
        """
        Increment the integer value of key by amount.
        If key doesn't exist, set it to amount.

        Args:
            key: The key name
            amount: Amount to increment by (default 1)

        Returns:
            New value after increment
        """
        # Check if key exists as a string value
        current_value = self._get_typed_data(key, TYPE_STRING)

        if current_value is None:
            # Key doesn't exist, start from 0
            new_value = amount
        else:
            try:
                # Try to convert existing value to int and increment
                new_value = int(current_value) + amount
            except (ValueError, TypeError):
                raise ValueError("value is not an integer or out of range")

        # Store the new value with no expiration (like Redis default)
        expire = time.time() + NO_EXPIRATION
        with self.mutex:
            self._keys[key] = (expire, TYPE_STRING, new_value)

        return new_value

    def decr(self, key, amount=1):
        """
        Decrement the integer value of key by amount.
        If key doesn't exist, set it to -amount.

        Args:
            key: The key name
            amount: Amount to decrement by (default 1)

        Returns:
            New value after decrement
        """
        return self.incr(key, -amount)

    def incrby(self, key, amount):
        """
        Increment the integer value of key by amount (Redis INCRBY command).
        Alias for incr(key, amount).

        Args:
            key: The key name
            amount: Amount to increment by

        Returns:
            New value after increment
        """
        return self.incr(key, amount)

    def decrby(self, key, amount):
        """
        Decrement the integer value of key by amount (Redis DECRBY command).
        Alias for decr(key, amount).

        Args:
            key: The key name
            amount: Amount to decrement by

        Returns:
            New value after decrement
        """
        return self.decr(key, amount)

    def incrbyfloat(self, key, amount):
        """
        Increment the float value of key by amount (Redis INCRBYFLOAT command).

        Args:
            key: The key name
            amount: Amount to increment by (float)

        Returns:
            New value after increment as a float
        """
        current_value = self._get_typed_data(key, TYPE_STRING)

        if current_value is None:
            # Key doesn't exist, start from 0
            new_value = float(amount)
        else:
            try:
                # Try to convert existing value to float and increment
                new_value = float(current_value) + float(amount)
            except (ValueError, TypeError):
                raise ValueError("value is not a valid float")

        # Store the new value
        expire = time.time() + NO_EXPIRATION
        with self.mutex:
            self._keys[key] = (expire, TYPE_STRING, new_value)

        return new_value
