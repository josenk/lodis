"""
Async implementation of Lodis - A lightweight, in-memory key-value store with asyncio support.
Redis-compatible API for drop-in replacement when Redis server is not available.

Usage:
    import lodis.asyncio as lodis

    async def main():
        r = lodis.Redis()
        await r.set("key", "value", ex=300)
        value = await r.get("key")
"""

import time
import fnmatch
import random
import asyncio

from .constants import (
    __version__,
    NUM_DATABASES,
    NO_EXPIRATION,
    TYPE_STRING,
    TYPE_LIST,
    TYPE_SET,
    TYPE_ZSET,
    TYPE_HASH
)


class AsyncLodisBase:
    """
    Async base class for Lodis - provides core structure and helper methods.

    This class provides the fundamental infrastructure including:
    - Storage management
    - Expiration checking
    - Type checking
    - Async safety via asyncio locks
    """

    def __init__(self, host='localhost', port=6379, db=0, decode_responses=False,
                 socket_timeout=None, socket_connect_timeout=None,
                 socket_keepalive=None, socket_keepalive_options=None,
                 connection_pool=None, unix_socket_path=None,
                 encoding='utf-8', encoding_errors='strict',
                 charset=None, errors=None, retry_on_timeout=False,
                 ssl=False, ssl_keyfile=None, ssl_certfile=None,
                 ssl_cert_reqs='required', ssl_ca_certs=None,
                 ssl_ca_cert_dir=None, ssl_ca_data=None, ssl_check_hostname=False,
                 max_connections=None, single_connection_client=False,
                 health_check_interval=0, client_name=None, username=None,
                 password=None, **kwargs):
        """
        Redis-compatible constructor. Connection parameters are ignored since this is in-memory.
        All data is stored locally without any network connections.

        Args:
            db: Database number (0-15, default 0). Redis supports 16 databases by default.
            decode_responses: Whether to decode responses (stored but not used in this implementation)
            **kwargs: Other Redis connection parameters (ignored)
        """
        # All connection parameters are ignored - this is in-memory storage
        self.decode_responses = decode_responses

        # Validate initial database selection
        if not isinstance(db, int) or db < 0 or db >= NUM_DATABASES:
            raise ValueError(f"invalid DB index: {db} (must be 0-{NUM_DATABASES - 1})")

        # Current database selection
        self._current_db = db

        # Storage: dict of dicts, one per database
        # Structure: {db_num: {key: (expire, data_type, data)}}
        # - expire: timestamp when key expires
        # - data_type: one of TYPE_STRING, TYPE_LIST, TYPE_SET, TYPE_ZSET, TYPE_HASH
        # - data: the actual data (type depends on data_type)
        self._databases = {i: {} for i in range(NUM_DATABASES)}

        # Use asyncio.Lock instead of multiprocessing.Lock
        self.mutex = asyncio.Lock()

    @property
    def _keys(self):
        """Get the current database's key storage."""
        return self._databases[self._current_db]

    def _is_expired(self, key):
        """
        Check if key exists and is not expired. Clean up if expired.

        Args:
            key: The key to check

        Returns:
            Tuple of (data_type, data) if key exists and not expired, (None, None) otherwise
        """
        entry = self._keys.get(key, None)
        if entry is None:
            return None, None

        expire, data_type, data = entry

        if expire < time.time():
            # Note: We can't use async context manager in a sync method
            # Deletion will happen in async methods that call this
            return None, None

        return data_type, data

    async def _delete_expired_key(self, key):
        """Helper method to delete expired key with async lock."""
        async with self.mutex:
            if key in self._databases[self._current_db]:
                del self._databases[self._current_db][key]

    def _check_type(self, key, expected_type):
        """
        Check if key exists and has the expected type.
        Raises WRONGTYPE error if key exists but has wrong type.

        Args:
            key: The key to check
            expected_type: Expected data type (TYPE_STRING, TYPE_LIST, etc.)

        Returns:
            True if key doesn't exist or has correct type

        Raises:
            TypeError: If key exists but has wrong type
        """
        data_type, data = self._is_expired(key)
        if data_type is None:
            # Key doesn't exist, which is fine
            return True

        if data_type != expected_type:
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        return True

    def _get_typed_data(self, key, expected_type):
        """
        Get data for key with type checking.

        Args:
            key: The key to retrieve
            expected_type: Expected data type

        Returns:
            Data if key exists and has correct type, None otherwise

        Raises:
            TypeError: If key exists but has wrong type
        """
        data_type, data = self._is_expired(key)
        if data_type is None:
            return None

        if data_type != expected_type:
            raise TypeError("WRONGTYPE Operation against a key holding the wrong kind of value")

        return data


class AsyncStringsMixin:
    """
    Async mixin class providing Redis-compatible string operations.
    """

    async def set(self, key, value, ex=None, px=None, nx=False, xx=False):
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

        async with self.mutex:
            self._keys[key] = (expire, TYPE_STRING, value)

        return True

    async def setex(self, key, seconds, value):
        """Set key to value with expiration in seconds (Redis SETEX command)."""
        return await self.set(key, value, ex=seconds)

    async def psetex(self, key, milliseconds, value):
        """Set key to value with expiration in milliseconds (Redis PSETEX command)."""
        return await self.set(key, value, px=milliseconds)

    async def setnx(self, key, value):
        """Set key to value only if key does not exist (Redis SETNX command)."""
        result = await self.set(key, value, nx=True)
        return result is not None

    async def get(self, key):
        """Get value for key."""
        data = self._get_typed_data(key, TYPE_STRING)
        if data is None:
            # Check if it was expired and clean it up
            entry = self._keys.get(key, None)
            if entry is not None:
                expire, _, _ = entry
                if expire < time.time():
                    await self._delete_expired_key(key)
        return data

    async def mget(self, *keys):
        """Get values of multiple keys (Redis MGET command)."""
        return [await self.get(key) for key in keys]

    async def mset(self, mapping):
        """Set multiple keys to multiple values atomically (Redis MSET command)."""
        async with self.mutex:
            expire = time.time() + NO_EXPIRATION
            for key, value in mapping.items():
                self._keys[key] = (expire, TYPE_STRING, value)
        return True

    async def getset(self, key, value):
        """Set key to value and return the old value (Redis GETSET command)."""
        old_value = await self.get(key)
        await self.set(key, value)
        return old_value

    async def append(self, key, value):
        """Append a value to a key (Redis APPEND command)."""
        current = await self.get(key)
        if current is None:
            new_value = str(value)
        else:
            new_value = str(current) + str(value)
        await self.set(key, new_value)
        return len(new_value)

    async def strlen(self, key):
        """Get the length of the value stored at key (Redis STRLEN command)."""
        value = await self.get(key)
        return len(str(value)) if value is not None else 0

    async def getdel(self, key):
        """Get the value of key and delete it atomically (Redis GETDEL command)."""
        value = await self.get(key)
        if value is not None:
            await self.delete(key)
        return value

    async def getex(self, key, ex=None, px=None, exat=None, pxat=None, persist=False):
        """Get the value and optionally set expiration (Redis GETEX command)."""
        value = await self.get(key)

        if value is not None:
            if persist:
                await self.persist(key)
            elif ex is not None:
                await self.expire(key, ex)
            elif px is not None:
                await self.pexpire(key, px)
            elif exat is not None:
                await self.expireat(key, exat)
            elif pxat is not None:
                await self.pexpireat(key, pxat)

        return value

    async def incr(self, key, amount=1):
        """Increment the integer value of key by amount."""
        current_value = self._get_typed_data(key, TYPE_STRING)

        if current_value is None:
            new_value = amount
        else:
            try:
                new_value = int(current_value) + amount
            except (ValueError, TypeError):
                raise ValueError("value is not an integer or out of range")

        expire = time.time() + NO_EXPIRATION
        async with self.mutex:
            self._keys[key] = (expire, TYPE_STRING, new_value)

        return new_value

    async def decr(self, key, amount=1):
        """Decrement the integer value of key by amount."""
        return await self.incr(key, -amount)

    async def incrby(self, key, amount):
        """Increment the integer value of key by amount (Redis INCRBY command)."""
        return await self.incr(key, amount)

    async def decrby(self, key, amount):
        """Decrement the integer value of key by amount (Redis DECRBY command)."""
        return await self.decr(key, amount)

    async def incrbyfloat(self, key, amount):
        """Increment the float value of key by amount (Redis INCRBYFLOAT command)."""
        current_value = self._get_typed_data(key, TYPE_STRING)

        if current_value is None:
            new_value = float(amount)
        else:
            try:
                new_value = float(current_value) + float(amount)
            except (ValueError, TypeError):
                raise ValueError("value is not a valid float")

        expire = time.time() + NO_EXPIRATION
        async with self.mutex:
            self._keys[key] = (expire, TYPE_STRING, new_value)

        return new_value


class AsyncListsMixin:
    """
    Async mixin class providing Redis-compatible list operations.
    """

    async def lpush(self, key, *values):
        """Insert all the specified values at the head of the list stored at key."""
        self._check_type(key, TYPE_LIST)

        data_type, current_list = self._is_expired(key)

        if current_list is None:
            current_list = []

        for value in values:
            current_list.insert(0, value)

        expire = time.time() + NO_EXPIRATION
        async with self.mutex:
            self._keys[key] = (expire, TYPE_LIST, current_list)

        return len(current_list)

    async def rpush(self, key, *values):
        """Insert all the specified values at the tail of the list stored at key."""
        self._check_type(key, TYPE_LIST)

        data_type, current_list = self._is_expired(key)

        if current_list is None:
            current_list = []

        current_list.extend(values)

        expire = time.time() + NO_EXPIRATION
        async with self.mutex:
            self._keys[key] = (expire, TYPE_LIST, current_list)

        return len(current_list)

    async def lpop(self, key, count=None):
        """Remove and return the first element(s) of the list stored at key."""
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return None

        if count is None:
            if len(current_list) == 0:
                return None

            value = current_list.pop(0)

            if len(current_list) == 0:
                async with self.mutex:
                    del self._keys[key]
            else:
                entry = self._keys[key]
                expire, data_type, _ = entry
                async with self.mutex:
                    self._keys[key] = (expire, data_type, current_list)

            return value
        else:
            if count <= 0:
                return []

            pop_count = min(count, len(current_list))
            values = [current_list.pop(0) for _ in range(pop_count)]

            if len(current_list) == 0:
                async with self.mutex:
                    del self._keys[key]
            else:
                entry = self._keys[key]
                expire, data_type, _ = entry
                async with self.mutex:
                    self._keys[key] = (expire, data_type, current_list)

            return values

    async def rpop(self, key, count=None):
        """Remove and return the last element(s) of the list stored at key."""
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return None

        if count is None:
            if len(current_list) == 0:
                return None

            value = current_list.pop()

            if len(current_list) == 0:
                async with self.mutex:
                    del self._keys[key]
            else:
                entry = self._keys[key]
                expire, data_type, _ = entry
                async with self.mutex:
                    self._keys[key] = (expire, data_type, current_list)

            return value
        else:
            if count <= 0:
                return []

            pop_count = min(count, len(current_list))
            values = [current_list.pop() for _ in range(pop_count)]

            if len(current_list) == 0:
                async with self.mutex:
                    del self._keys[key]
            else:
                entry = self._keys[key]
                expire, data_type, _ = entry
                async with self.mutex:
                    self._keys[key] = (expire, data_type, current_list)

            return values

    async def lrange(self, key, start, stop):
        """Return the specified elements of the list stored at key."""
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return []

        if stop >= 0:
            stop = stop + 1
        elif stop == -1:
            stop = None
        else:
            stop = stop + 1

        return current_list[start:stop]

    async def llen(self, key):
        """Return the length of the list stored at key."""
        current_list = self._get_typed_data(key, TYPE_LIST)
        if current_list is None:
            return 0
        return len(current_list)

    async def lindex(self, key, index):
        """Return the element at index in the list stored at key."""
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return None

        try:
            return current_list[index]
        except IndexError:
            return None

    async def lset(self, key, index, value):
        """Set the list element at index to value."""
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            raise ValueError("no such key")

        try:
            current_list[index] = value
        except IndexError:
            raise ValueError("index out of range")

        entry = self._keys[key]
        expire, data_type, _ = entry
        async with self.mutex:
            self._keys[key] = (expire, data_type, current_list)

        return True

    async def ltrim(self, key, start, stop):
        """Trim an existing list so that it will contain only the specified range of elements."""
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return True

        if stop >= 0:
            stop = stop + 1
        elif stop == -1:
            stop = None
        else:
            stop = stop + 1

        trimmed_list = current_list[start:stop]

        if len(trimmed_list) == 0:
            async with self.mutex:
                del self._keys[key]
        else:
            entry = self._keys[key]
            expire, data_type, _ = entry
            async with self.mutex:
                self._keys[key] = (expire, data_type, trimmed_list)

        return True

    async def lrem(self, key, count, value):
        """Remove the first count occurrences of elements equal to value from the list."""
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return 0

        removed = 0

        if count == 0:
            removed = current_list.count(value)
            current_list[:] = [item for item in current_list if item != value]
        elif count > 0:
            for _ in range(count):
                try:
                    current_list.remove(value)
                    removed += 1
                except ValueError:
                    break
        else:
            count = abs(count)
            for _ in range(count):
                try:
                    idx = len(current_list) - 1 - current_list[::-1].index(value)
                    current_list.pop(idx)
                    removed += 1
                except ValueError:
                    break

        if len(current_list) == 0:
            async with self.mutex:
                del self._keys[key]
        else:
            entry = self._keys[key]
            expire, data_type, _ = entry
            async with self.mutex:
                self._keys[key] = (expire, data_type, current_list)

        return removed

    async def rpoplpush(self, source, destination):
        """Atomically pop element from source list tail and push to destination list head."""
        element = await self.rpop(source)

        if element is None:
            return None

        await self.lpush(destination, element)
        return element

    async def blpop(self, *keys, timeout=0):
        """Blocking left pop - non-blocking in lodis async implementation."""
        for key in keys:
            element = await self.lpop(key)
            if element is not None:
                return (key, element)
        return None

    async def brpop(self, *keys, timeout=0):
        """Blocking right pop - non-blocking in lodis async implementation."""
        for key in keys:
            element = await self.rpop(key)
            if element is not None:
                return (key, element)
        return None

    async def brpoplpush(self, source, destination, timeout=0):
        """Blocking version of rpoplpush - non-blocking in lodis async implementation."""
        return await self.rpoplpush(source, destination)


class AsyncSetsMixin:
    """
    Async mixin class providing Redis-compatible set operations.
    """

    async def sadd(self, key, *members):
        """Add one or more members to a set."""
        self._check_type(key, TYPE_SET)

        data_type, current_set = self._is_expired(key)

        if current_set is None:
            current_set = set()

        initial_size = len(current_set)
        current_set.update(members)
        added_count = len(current_set) - initial_size

        expire = time.time() + NO_EXPIRATION
        async with self.mutex:
            self._keys[key] = (expire, TYPE_SET, current_set)

        return added_count

    async def srem(self, key, *members):
        """Remove one or more members from a set."""
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return 0

        initial_size = len(current_set)
        for member in members:
            current_set.discard(member)
        removed_count = initial_size - len(current_set)

        if len(current_set) == 0:
            async with self.mutex:
                del self._keys[key]
        else:
            entry = self._keys[key]
            expire, data_type, _ = entry
            async with self.mutex:
                self._keys[key] = (expire, data_type, current_set)

        return removed_count

    async def smembers(self, key):
        """Get all members of a set."""
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return set()

        return current_set.copy()

    async def sismember(self, key, member):
        """Check if member is in the set."""
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return 0

        return 1 if member in current_set else 0

    async def scard(self, key):
        """Get the number of members in a set."""
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return 0

        return len(current_set)

    async def spop(self, key, count=None):
        """Remove and return one or more random members from a set."""
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return None if count is None else set()

        if len(current_set) == 0:
            return None if count is None else set()

        if count is None:
            member = current_set.pop()

            if len(current_set) == 0:
                async with self.mutex:
                    del self._keys[key]
            else:
                entry = self._keys[key]
                expire, data_type, _ = entry
                async with self.mutex:
                    self._keys[key] = (expire, data_type, current_set)

            return member
        else:
            if count <= 0:
                return set()

            pop_count = min(count, len(current_set))
            members = set(random.sample(list(current_set), pop_count))

            current_set -= members

            if len(current_set) == 0:
                async with self.mutex:
                    del self._keys[key]
            else:
                entry = self._keys[key]
                expire, data_type, _ = entry
                async with self.mutex:
                    self._keys[key] = (expire, data_type, current_set)

            return members

    async def srandmember(self, key, count=None):
        """Return one or more random members from a set without removing them."""
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return None if count is None else []

        if len(current_set) == 0:
            return None if count is None else []

        if count is None:
            return random.choice(list(current_set))
        else:
            if count <= 0:
                return []

            sample_count = min(abs(count), len(current_set))
            return random.sample(list(current_set), sample_count)

    async def sinter(self, *keys):
        """Return the intersection of multiple sets."""
        if not keys:
            return set()

        result_set = self._get_typed_data(keys[0], TYPE_SET)
        if result_set is None:
            return set()

        result_set = result_set.copy()

        for key in keys[1:]:
            other_set = self._get_typed_data(key, TYPE_SET)
            if other_set is None:
                return set()
            result_set &= other_set

        return result_set

    async def sunion(self, *keys):
        """Return the union of multiple sets."""
        result_set = set()

        for key in keys:
            current_set = self._get_typed_data(key, TYPE_SET)
            if current_set is not None:
                result_set |= current_set

        return result_set

    async def sdiff(self, *keys):
        """Return the difference of multiple sets."""
        if not keys:
            return set()

        result_set = self._get_typed_data(keys[0], TYPE_SET)
        if result_set is None:
            return set()

        result_set = result_set.copy()

        for key in keys[1:]:
            other_set = self._get_typed_data(key, TYPE_SET)
            if other_set is not None:
                result_set -= other_set

        return result_set

    async def smove(self, source, destination, member):
        """Move a member from one set to another."""
        self._check_type(source, TYPE_SET)
        self._check_type(destination, TYPE_SET)

        source_set = self._get_typed_data(source, TYPE_SET)

        if source_set is None or member not in source_set:
            return 0

        source_set.discard(member)

        if len(source_set) == 0:
            async with self.mutex:
                del self._keys[source]
        else:
            entry = self._keys[source]
            expire, data_type, _ = entry
            async with self.mutex:
                self._keys[source] = (expire, data_type, source_set)

        data_type, dest_set = self._is_expired(destination)
        if dest_set is None:
            dest_set = set()

        dest_set.add(member)

        expire = time.time() + NO_EXPIRATION
        async with self.mutex:
            self._keys[destination] = (expire, TYPE_SET, dest_set)

        return 1


class AsyncSortedSetsMixin:
    """
    Async mixin class providing Redis-compatible sorted set operations.
    """

    async def zadd(self, key, mapping, nx=False, xx=False, gt=False, lt=False, ch=False):
        """Add one or more members to a sorted set, or update scores if they already exist."""
        self._check_type(key, TYPE_ZSET)

        data_type, current_zset = self._is_expired(key)

        if current_zset is None:
            current_zset = {}

        added = 0
        changed = 0

        for member, score in mapping.items():
            try:
                score = float(score)
            except (ValueError, TypeError):
                raise ValueError("score value is not a valid float")

            exists = member in current_zset

            if nx and exists:
                continue
            if xx and not exists:
                continue

            if exists:
                old_score = current_zset[member]
                if gt and score <= old_score:
                    continue
                if lt and score >= old_score:
                    continue
                if score != old_score:
                    changed += 1
            else:
                added += 1
                changed += 1

            current_zset[member] = score

        expire = time.time() + NO_EXPIRATION
        async with self.mutex:
            self._keys[key] = (expire, TYPE_ZSET, current_zset)

        return changed if ch else added

    async def zrem(self, key, *members):
        """Remove one or more members from a sorted set."""
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return 0

        removed = 0
        for member in members:
            if member in current_zset:
                del current_zset[member]
                removed += 1

        if len(current_zset) == 0:
            async with self.mutex:
                del self._keys[key]
        else:
            entry = self._keys[key]
            expire, data_type, _ = entry
            async with self.mutex:
                self._keys[key] = (expire, data_type, current_zset)

        return removed

    async def zscore(self, key, member):
        """Get the score of a member in a sorted set."""
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return None

        return current_zset.get(member, None)

    async def zcard(self, key):
        """Get the number of members in a sorted set."""
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return 0

        return len(current_zset)

    async def zincrby(self, key, increment, member):
        """Increment the score of a member in a sorted set."""
        self._check_type(key, TYPE_ZSET)

        data_type, current_zset = self._is_expired(key)

        if current_zset is None:
            current_zset = {}

        try:
            increment = float(increment)
        except (ValueError, TypeError):
            raise ValueError("increment value is not a valid float")

        current_score = current_zset.get(member, 0.0)
        new_score = current_score + increment

        current_zset[member] = new_score

        expire = time.time() + NO_EXPIRATION
        async with self.mutex:
            self._keys[key] = (expire, TYPE_ZSET, current_zset)

        return new_score

    async def zrank(self, key, member):
        """Get the rank (index) of a member in a sorted set (ordered by score, low to high)."""
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None or member not in current_zset:
            return None

        sorted_members = sorted(current_zset.items(), key=lambda x: (x[1], x[0]))

        for rank, (m, _) in enumerate(sorted_members):
            if m == member:
                return rank

        return None

    async def zrevrank(self, key, member):
        """Get the rank (index) of a member in a sorted set (ordered by score, high to low)."""
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None or member not in current_zset:
            return None

        sorted_members = sorted(current_zset.items(), key=lambda x: (-x[1], x[0]))

        for rank, (m, _) in enumerate(sorted_members):
            if m == member:
                return rank

        return None

    async def zrange(self, key, start, stop, withscores=False, desc=False):
        """Return a range of members in a sorted set by index."""
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return []

        if desc:
            sorted_members = sorted(current_zset.items(), key=lambda x: (-x[1], x[0]))
        else:
            sorted_members = sorted(current_zset.items(), key=lambda x: (x[1], x[0]))

        length = len(sorted_members)
        if start < 0:
            start = max(0, length + start)
        if stop < 0:
            stop = max(0, length + stop)

        stop = min(stop + 1, length)

        result_slice = sorted_members[start:stop]

        if withscores:
            return result_slice
        else:
            return [member for member, score in result_slice]

    async def zrevrange(self, key, start, stop, withscores=False):
        """Return a range of members in a sorted set by index (descending order)."""
        return await self.zrange(key, start, stop, withscores=withscores, desc=True)

    async def zrangebyscore(self, key, min_score, max_score, withscores=False):
        """Return members in a sorted set within the given score range."""
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return []

        if min_score == "-inf":
            min_score = float("-inf")
        else:
            min_score = float(min_score)

        if max_score == "+inf":
            max_score = float("inf")
        else:
            max_score = float(max_score)

        filtered = [(m, s) for m, s in current_zset.items() if min_score <= s <= max_score]
        sorted_members = sorted(filtered, key=lambda x: (x[1], x[0]))

        if withscores:
            return sorted_members
        else:
            return [member for member, score in sorted_members]

    async def zcount(self, key, min_score, max_score):
        """Count members in a sorted set within the given score range."""
        result = await self.zrangebyscore(key, min_score, max_score, withscores=False)
        return len(result)

    async def zremrangebyrank(self, key, start, stop):
        """Remove all members in a sorted set within the given rank range."""
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return 0

        members_to_remove = await self.zrange(key, start, stop, withscores=False)

        for member in members_to_remove:
            del current_zset[member]

        if len(current_zset) == 0:
            async with self.mutex:
                del self._keys[key]
        else:
            entry = self._keys[key]
            expire, data_type, _ = entry
            async with self.mutex:
                self._keys[key] = (expire, data_type, current_zset)

        return len(members_to_remove)

    async def zremrangebyscore(self, key, min_score, max_score):
        """Remove all members in a sorted set within the given score range."""
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return 0

        members_to_remove = await self.zrangebyscore(key, min_score, max_score, withscores=False)

        for member in members_to_remove:
            del current_zset[member]

        if len(current_zset) == 0:
            async with self.mutex:
                del self._keys[key]
        else:
            entry = self._keys[key]
            expire, data_type, _ = entry
            async with self.mutex:
                self._keys[key] = (expire, data_type, current_zset)

        return len(members_to_remove)


class AsyncManagementMixin:
    """
    Async mixin class providing Redis-compatible key management and database operations.
    """

    async def delete(self, *keys):
        """Delete one or more keys."""
        deleted_count = 0
        async with self.mutex:
            for key in keys:
                if key in self._keys:
                    del self._keys[key]
                    deleted_count += 1

        return deleted_count

    async def keys(self, pattern='*'):
        """Return all keys matching pattern."""
        _matching_keys = []
        _tmp_keys = self._keys.copy()

        for key in _tmp_keys:
            data_type, _ = self._is_expired(key)
            if data_type is not None:
                if fnmatch.fnmatch(key, pattern):
                    _matching_keys.append(key)

        return sorted(_matching_keys)

    async def exists(self, *keys):
        """Check if keys exist."""
        count = 0
        for key in keys:
            data_type, _ = self._is_expired(key)
            if data_type is not None:
                count += 1

        return count

    async def type(self, key):
        """Determine the type stored at key (Redis TYPE command)."""
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

    async def rename(self, key, newkey):
        """Rename a key (Redis RENAME command)."""
        data_type, _ = self._is_expired(key)
        if data_type is None:
            raise KeyError("no such key")

        async with self.mutex:
            self._keys[newkey] = self._keys[key]
            del self._keys[key]

        return True

    async def renamenx(self, key, newkey):
        """Rename key to newkey only if newkey doesn't exist (Redis RENAMENX command)."""
        data_type, _ = self._is_expired(key)
        if data_type is None:
            raise KeyError("no such key")

        newkey_type, _ = self._is_expired(newkey)
        if newkey_type is not None:
            return 0

        async with self.mutex:
            self._keys[newkey] = self._keys[key]
            del self._keys[key]

        return 1

    async def persist(self, key):
        """Remove expiration from key (Redis PERSIST command)."""
        data_type, data = self._is_expired(key)
        if data_type is None:
            return 0

        expire, _, _ = self._keys[key]
        if expire >= time.time() + NO_EXPIRATION - 1:
            return 0

        new_expire = time.time() + NO_EXPIRATION
        async with self.mutex:
            self._keys[key] = (new_expire, data_type, data)

        return 1

    async def randomkey(self):
        """Return a random key from the current database (Redis RANDOMKEY command)."""
        valid_keys = []
        for key in self._keys.copy():
            data_type, _ = self._is_expired(key)
            if data_type is not None:
                valid_keys.append(key)

        if not valid_keys:
            return None

        return random.choice(valid_keys)

    async def scan(self, cursor=0, match=None, count=None):
        """Incrementally iterate over keys (Redis SCAN command)."""
        if count is None:
            count = 10

        all_keys = []
        for key in self._keys.copy():
            data_type, _ = self._is_expired(key)
            if data_type is not None:
                if match is None or fnmatch.fnmatch(key, match):
                    all_keys.append(key)

        all_keys = sorted(all_keys)

        start = cursor
        end = start + count
        result_keys = all_keys[start:end]

        next_cursor = end if end < len(all_keys) else 0

        return (next_cursor, result_keys)

    async def expire(self, key, seconds):
        """Set expiration on key in seconds."""
        if key in self._keys:
            data_type, data = self._is_expired(key)
            if data_type is not None:
                expire = time.time() + seconds
                async with self.mutex:
                    self._keys[key] = (expire, data_type, data)
                return True

        return False

    async def ttl(self, key):
        """Get time to live for key in seconds."""
        if key in self._keys:
            entry = self._keys.get(key, None)
            if entry is None:
                return -2

            expire, data_type, data = entry

            current_time = time.time()
            if expire < current_time:
                async with self.mutex:
                    del self._keys[key]
                return -2

            if expire - current_time > (50 * 365 * 24 * 3600):
                return -1

            return int(expire - current_time)

        return -2

    async def pttl(self, key):
        """Get time to live for key in milliseconds (Redis PTTL command)."""
        if key in self._keys:
            entry = self._keys.get(key, None)
            if entry is None:
                return -2

            expire, data_type, data = entry

            current_time = time.time()
            if expire < current_time:
                async with self.mutex:
                    del self._keys[key]
                return -2

            if expire - current_time > (50 * 365 * 24 * 3600):
                return -1

            return int((expire - current_time) * 1000)

        return -2

    async def expireat(self, key, timestamp):
        """Set expiration to Unix timestamp in seconds (Redis EXPIREAT command)."""
        if key in self._keys:
            data_type, data = self._is_expired(key)
            if data_type is not None:
                async with self.mutex:
                    self._keys[key] = (timestamp, data_type, data)
                return 1

        return 0

    async def pexpire(self, key, milliseconds):
        """Set expiration in milliseconds (Redis PEXPIRE command)."""
        if key in self._keys:
            data_type, data = self._is_expired(key)
            if data_type is not None:
                expire = time.time() + (milliseconds / 1000.0)
                async with self.mutex:
                    self._keys[key] = (expire, data_type, data)
                return 1

        return 0

    async def pexpireat(self, key, timestamp_ms):
        """Set expiration to Unix timestamp in milliseconds (Redis PEXPIREAT command)."""
        if key in self._keys:
            data_type, data = self._is_expired(key)
            if data_type is not None:
                timestamp = timestamp_ms / 1000.0
                async with self.mutex:
                    self._keys[key] = (timestamp, data_type, data)
                return 1

        return 0

    async def select(self, db):
        """Switch to a different database."""
        if not isinstance(db, int) or db < 0 or db >= NUM_DATABASES:
            raise ValueError(f"invalid DB index: {db} (must be 0-{NUM_DATABASES - 1})")

        self._current_db = db
        return True

    async def flushdb(self):
        """Delete all keys from the current database only."""
        async with self.mutex:
            self._databases[self._current_db].clear()

        return True

    async def flushall(self):
        """Delete all keys from all databases."""
        async with self.mutex:
            for db_num in range(NUM_DATABASES):
                self._databases[db_num].clear()

        return True

    async def ping(self, message=None):
        """Test server connectivity (Redis PING command)."""
        if message is None:
            return True
        return message

    async def dbsize(self):
        """Return the number of keys in the current database (Redis DBSIZE command)."""
        count = 0
        for key in self._keys.copy():
            data_type, _ = self._is_expired(key)
            if data_type is not None:
                count += 1
        return count


class Lodis(AsyncLodisBase, AsyncStringsMixin, AsyncListsMixin, AsyncSetsMixin,
            AsyncSortedSetsMixin, AsyncManagementMixin):
    """
    Async Redis-compatible in-memory key-value store with TTL expiration support.

    This class provides a subset of Redis functionality for use when a Redis
    server is not available or not needed. All data is stored in memory and
    async-safe operations are provided via asyncio locks.

    Usage:
        import lodis.asyncio as lodis

        async def main():
            r = lodis.Redis()
            await r.set("key", "value", ex=300)
            value = await r.get("key")

        asyncio.run(main())
    """
    pass


# Provide Redis alias for drop-in replacement
Redis = Lodis

__all__ = ["Lodis", "Redis", "__version__"]
