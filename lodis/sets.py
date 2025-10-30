"""
Set operations for Lodis - Redis-compatible set commands.
"""

import time
import random

from .constants import NO_EXPIRATION, TYPE_SET


class SetsMixin:
    """
    Mixin class providing Redis-compatible set operations.
    """

    def sadd(self, key, *members):
        """
        Add one or more members to a set.
        If key does not exist, it is created as empty set before performing the add operations.

        Args:
            key: The key name
            members: One or more members to add

        Returns:
            The number of elements that were added (not including already existing elements)

        Raises:
            TypeError: If key exists but is not a set
        """
        self._check_type(key, TYPE_SET)

        data_type, current_set = self._is_expired(key)

        if current_set is None:
            # Key doesn't exist, create new set
            current_set = set()

        # Count new members
        initial_size = len(current_set)
        current_set.update(members)
        added_count = len(current_set) - initial_size

        expire = time.time() + NO_EXPIRATION
        with self.mutex:
            self._keys[key] = (expire, TYPE_SET, current_set)

        return added_count

    def srem(self, key, *members):
        """
        Remove one or more members from a set.

        Args:
            key: The key name
            members: One or more members to remove

        Returns:
            The number of members that were removed (not including non-existing members)

        Raises:
            TypeError: If key exists but is not a set
        """
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return 0

        # Count removed members
        initial_size = len(current_set)
        for member in members:
            current_set.discard(member)
        removed_count = initial_size - len(current_set)

        if len(current_set) == 0:
            # Delete the key if set becomes empty
            with self.mutex:
                del self._keys[key]
        else:
            # Update the set
            entry = self._keys[key]
            expire, data_type, _ = entry
            with self.mutex:
                self._keys[key] = (expire, data_type, current_set)

        return removed_count

    def smembers(self, key):
        """
        Get all members of a set.

        Args:
            key: The key name

        Returns:
            Set of all members, or empty set if key doesn't exist

        Raises:
            TypeError: If key exists but is not a set
        """
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return set()

        # Return a copy to prevent external modification
        return current_set.copy()

    def sismember(self, key, member):
        """
        Check if member is in the set.

        Args:
            key: The key name
            member: The member to check

        Returns:
            1 if member exists, 0 otherwise

        Raises:
            TypeError: If key exists but is not a set
        """
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return 0

        return 1 if member in current_set else 0

    def scard(self, key):
        """
        Get the number of members in a set.

        Args:
            key: The key name

        Returns:
            The cardinality (number of elements) of the set, or 0 if key doesn't exist

        Raises:
            TypeError: If key exists but is not a set
        """
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return 0

        return len(current_set)

    def spop(self, key, count=None):
        """
        Remove and return one or more random members from a set.

        Args:
            key: The key name
            count: Number of members to pop (None for single member)

        Returns:
            A random member (if count is None), or a set of random members

        Raises:
            TypeError: If key exists but is not a set
        """
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return None if count is None else set()

        if len(current_set) == 0:
            return None if count is None else set()

        if count is None:
            # Pop single element
            member = current_set.pop()

            # If set is now empty, delete the key
            if len(current_set) == 0:
                with self.mutex:
                    del self._keys[key]
            else:
                # Update the set
                entry = self._keys[key]
                expire, data_type, _ = entry
                with self.mutex:
                    self._keys[key] = (expire, data_type, current_set)

            return member
        else:
            # Pop multiple elements
            if count <= 0:
                return set()

            pop_count = min(count, len(current_set))
            members = set(random.sample(list(current_set), pop_count))

            # Remove the popped members
            current_set -= members

            # If set is now empty, delete the key
            if len(current_set) == 0:
                with self.mutex:
                    del self._keys[key]
            else:
                # Update the set
                entry = self._keys[key]
                expire, data_type, _ = entry
                with self.mutex:
                    self._keys[key] = (expire, data_type, current_set)

            return members

    def srandmember(self, key, count=None):
        """
        Return one or more random members from a set without removing them.

        Args:
            key: The key name
            count: Number of members to return (None for single member)

        Returns:
            A random member (if count is None), or a list of random members

        Raises:
            TypeError: If key exists but is not a set
        """
        current_set = self._get_typed_data(key, TYPE_SET)

        if current_set is None:
            return None if count is None else []

        if len(current_set) == 0:
            return None if count is None else []

        if count is None:
            # Return single element
            return random.choice(list(current_set))
        else:
            # Return multiple elements
            if count <= 0:
                return []

            sample_count = min(abs(count), len(current_set))
            return random.sample(list(current_set), sample_count)

    def sinter(self, *keys):
        """
        Return the intersection of multiple sets.

        Args:
            keys: One or more set keys

        Returns:
            Set containing the intersection of all sets

        Raises:
            TypeError: If any key exists but is not a set
        """
        if not keys:
            return set()

        # Get the first set
        result_set = self._get_typed_data(keys[0], TYPE_SET)
        if result_set is None:
            return set()

        result_set = result_set.copy()

        # Intersect with remaining sets
        for key in keys[1:]:
            other_set = self._get_typed_data(key, TYPE_SET)
            if other_set is None:
                return set()
            result_set &= other_set

        return result_set

    def sunion(self, *keys):
        """
        Return the union of multiple sets.

        Args:
            keys: One or more set keys

        Returns:
            Set containing the union of all sets

        Raises:
            TypeError: If any key exists but is not a set
        """
        result_set = set()

        for key in keys:
            current_set = self._get_typed_data(key, TYPE_SET)
            if current_set is not None:
                result_set |= current_set

        return result_set

    def sdiff(self, *keys):
        """
        Return the difference of multiple sets (elements in first set but not in others).

        Args:
            keys: One or more set keys

        Returns:
            Set containing the difference

        Raises:
            TypeError: If any key exists but is not a set
        """
        if not keys:
            return set()

        # Get the first set
        result_set = self._get_typed_data(keys[0], TYPE_SET)
        if result_set is None:
            return set()

        result_set = result_set.copy()

        # Subtract remaining sets
        for key in keys[1:]:
            other_set = self._get_typed_data(key, TYPE_SET)
            if other_set is not None:
                result_set -= other_set

        return result_set

    def smove(self, source, destination, member):
        """
        Move a member from one set to another.

        Args:
            source: Source set key
            destination: Destination set key
            member: Member to move

        Returns:
            1 if member was moved, 0 if not found in source

        Raises:
            TypeError: If source or destination exists but is not a set
        """
        # Check types
        self._check_type(source, TYPE_SET)
        self._check_type(destination, TYPE_SET)

        source_set = self._get_typed_data(source, TYPE_SET)

        if source_set is None or member not in source_set:
            return 0

        # Remove from source
        source_set.discard(member)

        # Update or delete source
        if len(source_set) == 0:
            with self.mutex:
                del self._keys[source]
        else:
            entry = self._keys[source]
            expire, data_type, _ = entry
            with self.mutex:
                self._keys[source] = (expire, data_type, source_set)

        # Add to destination
        data_type, dest_set = self._is_expired(destination)
        if dest_set is None:
            dest_set = set()

        dest_set.add(member)

        expire = time.time() + NO_EXPIRATION
        with self.mutex:
            self._keys[destination] = (expire, TYPE_SET, dest_set)

        return 1
