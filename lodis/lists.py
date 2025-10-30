"""
List operations for Lodis - Redis-compatible list commands.
"""

import time

from .constants import NO_EXPIRATION, TYPE_LIST


class ListsMixin:
    """
    Mixin class providing Redis-compatible list operations.
    """

    def lpush(self, key, *values):
        """
        Insert all the specified values at the head of the list stored at key.
        If key does not exist, it is created as empty list before performing the push operations.

        Args:
            key: The key name
            values: One or more values to push

        Returns:
            The length of the list after the push operations

        Raises:
            TypeError: If key exists but is not a list
        """
        self._check_type(key, TYPE_LIST)

        data_type, current_list = self._is_expired(key)

        if current_list is None:
            # Key doesn't exist, create new list
            current_list = []

        # Insert values at the beginning (left side) in order
        # Redis lpush inserts in reverse order: lpush key a b c -> [c, b, a]
        for value in values:
            current_list.insert(0, value)

        expire = time.time() + NO_EXPIRATION
        with self.mutex:
            self._keys[key] = (expire, TYPE_LIST, current_list)

        return len(current_list)

    def rpush(self, key, *values):
        """
        Insert all the specified values at the tail of the list stored at key.
        If key does not exist, it is created as empty list before performing the push operations.

        Args:
            key: The key name
            values: One or more values to push

        Returns:
            The length of the list after the push operations

        Raises:
            TypeError: If key exists but is not a list
        """
        self._check_type(key, TYPE_LIST)

        data_type, current_list = self._is_expired(key)

        if current_list is None:
            # Key doesn't exist, create new list
            current_list = []

        # Append values at the end (right side)
        current_list.extend(values)

        expire = time.time() + NO_EXPIRATION
        with self.mutex:
            self._keys[key] = (expire, TYPE_LIST, current_list)

        return len(current_list)

    def lpop(self, key, count=None):
        """
        Remove and return the first element(s) of the list stored at key.

        Args:
            key: The key name
            count: Number of elements to pop (None for single element)

        Returns:
            The value of the first element, or None when key does not exist.
            If count is specified, returns a list of popped elements.

        Raises:
            TypeError: If key exists but is not a list
        """
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return None

        if count is None:
            # Pop single element
            if len(current_list) == 0:
                return None

            value = current_list.pop(0)

            # If list is now empty, delete the key
            if len(current_list) == 0:
                with self.mutex:
                    del self._keys[key]
            else:
                # Update the list
                entry = self._keys[key]
                expire, data_type, _ = entry
                with self.mutex:
                    self._keys[key] = (expire, data_type, current_list)

            return value
        else:
            # Pop multiple elements
            if count <= 0:
                return []

            pop_count = min(count, len(current_list))
            values = [current_list.pop(0) for _ in range(pop_count)]

            # If list is now empty, delete the key
            if len(current_list) == 0:
                with self.mutex:
                    del self._keys[key]
            else:
                # Update the list
                entry = self._keys[key]
                expire, data_type, _ = entry
                with self.mutex:
                    self._keys[key] = (expire, data_type, current_list)

            return values

    def rpop(self, key, count=None):
        """
        Remove and return the last element(s) of the list stored at key.

        Args:
            key: The key name
            count: Number of elements to pop (None for single element)

        Returns:
            The value of the last element, or None when key does not exist.
            If count is specified, returns a list of popped elements.

        Raises:
            TypeError: If key exists but is not a list
        """
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return None

        if count is None:
            # Pop single element
            if len(current_list) == 0:
                return None

            value = current_list.pop()

            # If list is now empty, delete the key
            if len(current_list) == 0:
                with self.mutex:
                    del self._keys[key]
            else:
                # Update the list
                entry = self._keys[key]
                expire, data_type, _ = entry
                with self.mutex:
                    self._keys[key] = (expire, data_type, current_list)

            return value
        else:
            # Pop multiple elements
            if count <= 0:
                return []

            pop_count = min(count, len(current_list))
            values = [current_list.pop() for _ in range(pop_count)]

            # If list is now empty, delete the key
            if len(current_list) == 0:
                with self.mutex:
                    del self._keys[key]
            else:
                # Update the list
                entry = self._keys[key]
                expire, data_type, _ = entry
                with self.mutex:
                    self._keys[key] = (expire, data_type, current_list)

            return values

    def lrange(self, key, start, stop):
        """
        Return the specified elements of the list stored at key.
        The offsets start and stop are zero-based indexes.
        These offsets can also be negative numbers indicating offsets starting at the end of the list.

        Args:
            key: The key name
            start: Start index (inclusive)
            stop: Stop index (inclusive, unlike Python slicing)

        Returns:
            List of elements in the specified range, or empty list if key doesn't exist

        Raises:
            TypeError: If key exists but is not a list
        """
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return []

        # Redis LRANGE uses inclusive end, Python slicing uses exclusive end
        # So we need to add 1 to stop
        if stop >= 0:
            stop = stop + 1
        elif stop == -1:
            # Special case: -1 means last element (inclusive)
            stop = None
        else:
            # For negative indices, we still add 1
            stop = stop + 1

        return current_list[start:stop]

    def llen(self, key):
        """
        Return the length of the list stored at key.

        Args:
            key: The key name

        Returns:
            The length of the list, or 0 when key does not exist

        Raises:
            TypeError: If key exists but is not a list
        """
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return 0

        return len(current_list)

    def lindex(self, key, index):
        """
        Return the element at index in the list stored at key.
        The index is zero-based. Negative indices can be used to designate
        elements starting at the tail of the list.

        Args:
            key: The key name
            index: Index of the element to retrieve

        Returns:
            The requested element, or None when index is out of range or key doesn't exist

        Raises:
            TypeError: If key exists but is not a list
        """
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return None

        try:
            return current_list[index]
        except IndexError:
            return None

    def lset(self, key, index, value):
        """
        Set the list element at index to value.

        Args:
            key: The key name
            index: Index of the element to set
            value: The new value

        Returns:
            True if successful

        Raises:
            TypeError: If key exists but is not a list
            ValueError: If the index is out of range or key doesn't exist
        """
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            raise ValueError("no such key")

        try:
            current_list[index] = value
        except IndexError:
            raise ValueError("index out of range")

        # Update the list
        entry = self._keys[key]
        expire, data_type, _ = entry
        with self.mutex:
            self._keys[key] = (expire, data_type, current_list)

        return True

    def ltrim(self, key, start, stop):
        """
        Trim an existing list so that it will contain only the specified range of elements.
        Both start and stop are zero-based indexes where 0 is the first element.

        Args:
            key: The key name
            start: Start index (inclusive)
            stop: Stop index (inclusive)

        Returns:
            True

        Raises:
            TypeError: If key exists but is not a list
        """
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return True

        # Redis LTRIM uses inclusive end, Python slicing uses exclusive end
        if stop >= 0:
            stop = stop + 1
        elif stop == -1:
            stop = None
        else:
            stop = stop + 1

        trimmed_list = current_list[start:stop]

        if len(trimmed_list) == 0:
            # Delete the key if list becomes empty
            with self.mutex:
                del self._keys[key]
        else:
            # Update the list
            entry = self._keys[key]
            expire, data_type, _ = entry
            with self.mutex:
                self._keys[key] = (expire, data_type, trimmed_list)

        return True

    def lrem(self, key, count, value):
        """
        Remove the first count occurrences of elements equal to value from the list stored at key.
        The count argument influences the operation in the following ways:
        - count > 0: Remove elements equal to value moving from head to tail.
        - count < 0: Remove elements equal to value moving from tail to head.
        - count = 0: Remove all elements equal to value.

        Args:
            key: The key name
            count: Number and direction of elements to remove
            value: The value to remove

        Returns:
            The number of removed elements

        Raises:
            TypeError: If key exists but is not a list
        """
        current_list = self._get_typed_data(key, TYPE_LIST)

        if current_list is None:
            return 0

        removed = 0

        if count == 0:
            # Remove all occurrences
            removed = current_list.count(value)
            current_list[:] = [item for item in current_list if item != value]
        elif count > 0:
            # Remove from head to tail
            for _ in range(count):
                try:
                    current_list.remove(value)
                    removed += 1
                except ValueError:
                    break
        else:
            # Remove from tail to head
            count = abs(count)
            for _ in range(count):
                try:
                    # Find last occurrence
                    idx = len(current_list) - 1 - current_list[::-1].index(value)
                    current_list.pop(idx)
                    removed += 1
                except ValueError:
                    break

        if len(current_list) == 0:
            # Delete the key if list becomes empty
            with self.mutex:
                del self._keys[key]
        else:
            # Update the list
            entry = self._keys[key]
            expire, data_type, _ = entry
            with self.mutex:
                self._keys[key] = (expire, data_type, current_list)

        return removed

    def rpoplpush(self, source, destination):
        """
        Atomically pop element from source list tail and push to destination list head (Redis RPOPLPUSH command).

        Args:
            source: Source list key
            destination: Destination list key

        Returns:
            The element moved, or None if source is empty

        Raises:
            TypeError: If source or destination exists but is not a list
        """
        # Pop from source
        element = self.rpop(source)

        if element is None:
            return None

        # Push to destination
        self.lpush(destination, element)

        return element

    def blpop(self, *keys, timeout=0):
        """
        Blocking left pop - pop element from first non-empty list (Redis BLPOP command).

        Note: In lodis (in-memory implementation), this is non-blocking and immediately
        returns None if all lists are empty. True blocking behavior requires
        a client-server architecture.

        Args:
            keys: One or more list keys to check
            timeout: Timeout in seconds (ignored in lodis)

        Returns:
            Tuple of (key, value) if element found, None if all lists empty

        Raises:
            TypeError: If key exists but is not a list
        """
        # Try each key in order
        for key in keys:
            element = self.lpop(key)
            if element is not None:
                return (key, element)

        return None

    def brpop(self, *keys, timeout=0):
        """
        Blocking right pop - pop element from first non-empty list (Redis BRPOP command).

        Note: In lodis (in-memory implementation), this is non-blocking and immediately
        returns None if all lists are empty. True blocking behavior requires
        a client-server architecture.

        Args:
            keys: One or more list keys to check
            timeout: Timeout in seconds (ignored in lodis)

        Returns:
            Tuple of (key, value) if element found, None if all lists empty

        Raises:
            TypeError: If key exists but is not a list
        """
        # Try each key in order
        for key in keys:
            element = self.rpop(key)
            if element is not None:
                return (key, element)

        return None

    def brpoplpush(self, source, destination, timeout=0):
        """
        Blocking version of rpoplpush (Redis BRPOPLPUSH command).

        Note: In lodis (in-memory implementation), this is non-blocking and immediately
        returns None if source is empty. True blocking behavior requires
        a client-server architecture.

        Args:
            source: Source list key
            destination: Destination list key
            timeout: Timeout in seconds (ignored in lodis)

        Returns:
            The element moved, or None if source is empty

        Raises:
            TypeError: If source or destination exists but is not a list
        """
        return self.rpoplpush(source, destination)
