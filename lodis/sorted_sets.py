"""
Sorted Set operations for Lodis - Redis-compatible sorted set commands.
"""

import time

from .constants import NO_EXPIRATION, TYPE_ZSET


class SortedSetsMixin:
    """
    Mixin class providing Redis-compatible sorted set operations.
    """

    def zadd(self, key, mapping, nx=False, xx=False, gt=False, lt=False, ch=False):
        """
        Add one or more members to a sorted set, or update scores if they already exist.

        Args:
            key: The key name
            mapping: Dict of member:score pairs
            nx: Only add new elements (don't update existing)
            xx: Only update existing elements (don't add new)
            gt: Only update if new score is greater than current
            lt: Only update if new score is less than current
            ch: Return number of changed elements (added + updated)

        Returns:
            Number of elements added (or changed if ch=True)

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        self._check_type(key, TYPE_ZSET)

        data_type, current_zset = self._is_expired(key)

        if current_zset is None:
            # Key doesn't exist, create new sorted set
            # Store as dict: {member: score}
            current_zset = {}

        added = 0
        changed = 0

        for member, score in mapping.items():
            # Convert score to float
            try:
                score = float(score)
            except (ValueError, TypeError):
                raise ValueError("score value is not a valid float")

            exists = member in current_zset

            # Check nx/xx conditions
            if nx and exists:
                continue
            if xx and not exists:
                continue

            # Check gt/lt conditions
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
        with self.mutex:
            self._keys[key] = (expire, TYPE_ZSET, current_zset)

        return changed if ch else added

    def zrem(self, key, *members):
        """
        Remove one or more members from a sorted set.

        Args:
            key: The key name
            members: One or more members to remove

        Returns:
            The number of members removed

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return 0

        removed = 0
        for member in members:
            if member in current_zset:
                del current_zset[member]
                removed += 1

        if len(current_zset) == 0:
            # Delete the key if sorted set becomes empty
            with self.mutex:
                del self._keys[key]
        else:
            # Update the sorted set
            entry = self._keys[key]
            expire, data_type, _ = entry
            with self.mutex:
                self._keys[key] = (expire, data_type, current_zset)

        return removed

    def zscore(self, key, member):
        """
        Get the score of a member in a sorted set.

        Args:
            key: The key name
            member: The member to get score for

        Returns:
            The score as a float, or None if member doesn't exist

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return None

        return current_zset.get(member, None)

    def zcard(self, key):
        """
        Get the number of members in a sorted set.

        Args:
            key: The key name

        Returns:
            The cardinality (number of elements)

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return 0

        return len(current_zset)

    def zincrby(self, key, increment, member):
        """
        Increment the score of a member in a sorted set.

        Args:
            key: The key name
            increment: Amount to increment by
            member: The member to increment

        Returns:
            The new score

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        self._check_type(key, TYPE_ZSET)

        data_type, current_zset = self._is_expired(key)

        if current_zset is None:
            current_zset = {}

        # Convert increment to float
        try:
            increment = float(increment)
        except (ValueError, TypeError):
            raise ValueError("increment value is not a valid float")

        # Get current score or default to 0
        current_score = current_zset.get(member, 0.0)
        new_score = current_score + increment

        current_zset[member] = new_score

        expire = time.time() + NO_EXPIRATION
        with self.mutex:
            self._keys[key] = (expire, TYPE_ZSET, current_zset)

        return new_score

    def zrank(self, key, member):
        """
        Get the rank (index) of a member in a sorted set (ordered by score, low to high).

        Args:
            key: The key name
            member: The member to get rank for

        Returns:
            The rank (0-based index), or None if member doesn't exist

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None or member not in current_zset:
            return None

        # Sort by score (ascending), then by member lexicographically for ties
        sorted_members = sorted(current_zset.items(), key=lambda x: (x[1], x[0]))

        for rank, (m, _) in enumerate(sorted_members):
            if m == member:
                return rank

        return None

    def zrevrank(self, key, member):
        """
        Get the rank (index) of a member in a sorted set (ordered by score, high to low).

        Args:
            key: The key name
            member: The member to get rank for

        Returns:
            The rank (0-based index), or None if member doesn't exist

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None or member not in current_zset:
            return None

        # Sort by score (descending), then by member lexicographically for ties
        sorted_members = sorted(current_zset.items(), key=lambda x: (-x[1], x[0]))

        for rank, (m, _) in enumerate(sorted_members):
            if m == member:
                return rank

        return None

    def zrange(self, key, start, stop, withscores=False, desc=False):
        """
        Return a range of members in a sorted set by index.

        Args:
            key: The key name
            start: Start index (inclusive)
            stop: Stop index (inclusive, like Redis)
            withscores: Return scores along with members
            desc: Return in descending order

        Returns:
            List of members, or list of (member, score) tuples if withscores=True

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return []

        # Sort by score, then by member for ties
        if desc:
            sorted_members = sorted(current_zset.items(), key=lambda x: (-x[1], x[0]))
        else:
            sorted_members = sorted(current_zset.items(), key=lambda x: (x[1], x[0]))

        # Handle negative indices
        length = len(sorted_members)
        if start < 0:
            start = max(0, length + start)
        if stop < 0:
            stop = max(0, length + stop)

        # Redis ZRANGE uses inclusive end
        stop = min(stop + 1, length)

        result_slice = sorted_members[start:stop]

        if withscores:
            return result_slice
        else:
            return [member for member, score in result_slice]

    def zrevrange(self, key, start, stop, withscores=False):
        """
        Return a range of members in a sorted set by index (descending order).

        Args:
            key: The key name
            start: Start index (inclusive)
            stop: Stop index (inclusive)
            withscores: Return scores along with members

        Returns:
            List of members, or list of (member, score) tuples if withscores=True

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        return self.zrange(key, start, stop, withscores=withscores, desc=True)

    def zrangebyscore(self, key, min_score, max_score, withscores=False):
        """
        Return members in a sorted set within the given score range.

        Args:
            key: The key name
            min_score: Minimum score (inclusive, or "-inf" for negative infinity)
            max_score: Maximum score (inclusive, or "+inf" for positive infinity)
            withscores: Return scores along with members

        Returns:
            List of members, or list of (member, score) tuples if withscores=True

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return []

        # Parse min/max scores
        if min_score == "-inf":
            min_score = float("-inf")
        else:
            min_score = float(min_score)

        if max_score == "+inf":
            max_score = float("inf")
        else:
            max_score = float(max_score)

        # Filter by score range and sort
        filtered = [(m, s) for m, s in current_zset.items() if min_score <= s <= max_score]
        sorted_members = sorted(filtered, key=lambda x: (x[1], x[0]))

        if withscores:
            return sorted_members
        else:
            return [member for member, score in sorted_members]

    def zcount(self, key, min_score, max_score):
        """
        Count members in a sorted set within the given score range.

        Args:
            key: The key name
            min_score: Minimum score (inclusive, or "-inf")
            max_score: Maximum score (inclusive, or "+inf")

        Returns:
            Number of members in the range

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        result = self.zrangebyscore(key, min_score, max_score, withscores=False)
        return len(result)

    def zremrangebyrank(self, key, start, stop):
        """
        Remove all members in a sorted set within the given rank range.

        Args:
            key: The key name
            start: Start rank (inclusive)
            stop: Stop rank (inclusive)

        Returns:
            Number of members removed

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return 0

        # Get members in range
        members_to_remove = self.zrange(key, start, stop, withscores=False)

        # Remove them
        for member in members_to_remove:
            del current_zset[member]

        if len(current_zset) == 0:
            # Delete the key if sorted set becomes empty
            with self.mutex:
                del self._keys[key]
        else:
            # Update the sorted set
            entry = self._keys[key]
            expire, data_type, _ = entry
            with self.mutex:
                self._keys[key] = (expire, data_type, current_zset)

        return len(members_to_remove)

    def zremrangebyscore(self, key, min_score, max_score):
        """
        Remove all members in a sorted set within the given score range.

        Args:
            key: The key name
            min_score: Minimum score (inclusive, or "-inf")
            max_score: Maximum score (inclusive, or "+inf")

        Returns:
            Number of members removed

        Raises:
            TypeError: If key exists but is not a sorted set
        """
        current_zset = self._get_typed_data(key, TYPE_ZSET)

        if current_zset is None:
            return 0

        # Get members in range
        members_to_remove = self.zrangebyscore(key, min_score, max_score, withscores=False)

        # Remove them
        for member in members_to_remove:
            del current_zset[member]

        if len(current_zset) == 0:
            # Delete the key if sorted set becomes empty
            with self.mutex:
                del self._keys[key]
        else:
            # Update the sorted set
            entry = self._keys[key]
            expire, data_type, _ = entry
            with self.mutex:
                self._keys[key] = (expire, data_type, current_zset)

        return len(members_to_remove)
