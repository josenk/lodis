import unittest
import time
from lodis import Redis


class TestLists(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.redis = Redis()

    def test_lpush_and_lrange(self):
        """Test basic lpush and lrange operations."""
        # Push elements to the left
        length = self.redis.lpush("mylist", "world")
        self.assertEqual(length, 1)

        length = self.redis.lpush("mylist", "hello")
        self.assertEqual(length, 2)

        # Get all elements
        result = self.redis.lrange("mylist", 0, -1)
        self.assertEqual(result, ["hello", "world"])

    def test_rpush_and_lrange(self):
        """Test basic rpush and lrange operations."""
        # Push elements to the right
        length = self.redis.rpush("mylist", "hello")
        self.assertEqual(length, 1)

        length = self.redis.rpush("mylist", "world")
        self.assertEqual(length, 2)

        # Get all elements
        result = self.redis.lrange("mylist", 0, -1)
        self.assertEqual(result, ["hello", "world"])

    def test_lpush_multiple_values(self):
        """Test lpush with multiple values at once."""
        # Redis lpush with multiple values inserts in reverse order
        length = self.redis.lpush("mylist", "a", "b", "c")
        self.assertEqual(length, 3)

        result = self.redis.lrange("mylist", 0, -1)
        self.assertEqual(result, ["c", "b", "a"])

    def test_rpush_multiple_values(self):
        """Test rpush with multiple values at once."""
        length = self.redis.rpush("mylist", "a", "b", "c")
        self.assertEqual(length, 3)

        result = self.redis.lrange("mylist", 0, -1)
        self.assertEqual(result, ["a", "b", "c"])

    def test_lpop_single(self):
        """Test lpop for single element."""
        self.redis.rpush("mylist", "one", "two", "three")

        value = self.redis.lpop("mylist")
        self.assertEqual(value, "one")

        result = self.redis.lrange("mylist", 0, -1)
        self.assertEqual(result, ["two", "three"])

    def test_rpop_single(self):
        """Test rpop for single element."""
        self.redis.rpush("mylist", "one", "two", "three")

        value = self.redis.rpop("mylist")
        self.assertEqual(value, "three")

        result = self.redis.lrange("mylist", 0, -1)
        self.assertEqual(result, ["one", "two"])

    def test_lpop_multiple(self):
        """Test lpop with count parameter."""
        self.redis.rpush("mylist", "one", "two", "three", "four", "five")

        values = self.redis.lpop("mylist", 3)
        self.assertEqual(values, ["one", "two", "three"])

        result = self.redis.lrange("mylist", 0, -1)
        self.assertEqual(result, ["four", "five"])

    def test_rpop_multiple(self):
        """Test rpop with count parameter."""
        self.redis.rpush("mylist", "one", "two", "three", "four", "five")

        values = self.redis.rpop("mylist", 3)
        self.assertEqual(values, ["five", "four", "three"])

        result = self.redis.lrange("mylist", 0, -1)
        self.assertEqual(result, ["one", "two"])

    def test_lpop_nonexistent_key(self):
        """Test lpop on nonexistent key."""
        result = self.redis.lpop("nonexistent")
        self.assertIsNone(result)

    def test_rpop_nonexistent_key(self):
        """Test rpop on nonexistent key."""
        result = self.redis.rpop("nonexistent")
        self.assertIsNone(result)

    def test_lpop_empty_list(self):
        """Test lpop on empty list after all elements are removed."""
        self.redis.rpush("mylist", "one")
        self.redis.lpop("mylist")

        # Key should be deleted when list becomes empty
        result = self.redis.lpop("mylist")
        self.assertIsNone(result)

    def test_llen(self):
        """Test llen operation."""
        self.assertEqual(self.redis.llen("mylist"), 0)

        self.redis.rpush("mylist", "one", "two", "three")
        self.assertEqual(self.redis.llen("mylist"), 3)

        self.redis.lpop("mylist")
        self.assertEqual(self.redis.llen("mylist"), 2)

    def test_lindex(self):
        """Test lindex operation."""
        self.redis.rpush("mylist", "zero", "one", "two", "three")

        self.assertEqual(self.redis.lindex("mylist", 0), "zero")
        self.assertEqual(self.redis.lindex("mylist", 2), "two")
        self.assertEqual(self.redis.lindex("mylist", -1), "three")
        self.assertEqual(self.redis.lindex("mylist", -2), "two")

        # Out of range
        self.assertIsNone(self.redis.lindex("mylist", 10))
        self.assertIsNone(self.redis.lindex("mylist", -10))

    def test_lindex_nonexistent_key(self):
        """Test lindex on nonexistent key."""
        result = self.redis.lindex("nonexistent", 0)
        self.assertIsNone(result)

    def test_lset(self):
        """Test lset operation."""
        self.redis.rpush("mylist", "zero", "one", "two")

        result = self.redis.lset("mylist", 1, "ONE")
        self.assertTrue(result)

        self.assertEqual(self.redis.lindex("mylist", 1), "ONE")

        # Test with negative index
        result = self.redis.lset("mylist", -1, "TWO")
        self.assertTrue(result)
        self.assertEqual(self.redis.lindex("mylist", -1), "TWO")

    def test_lset_errors(self):
        """Test lset error conditions."""
        # Nonexistent key
        with self.assertRaises(ValueError):
            self.redis.lset("nonexistent", 0, "value")

        # Out of range
        self.redis.rpush("mylist", "one")
        with self.assertRaises(ValueError):
            self.redis.lset("mylist", 10, "value")

    def test_lrange_various_ranges(self):
        """Test lrange with various range parameters."""
        self.redis.rpush("mylist", "0", "1", "2", "3", "4", "5")

        # Normal range
        self.assertEqual(self.redis.lrange("mylist", 0, 2), ["0", "1", "2"])

        # Start from middle
        self.assertEqual(self.redis.lrange("mylist", 2, 4), ["2", "3", "4"])

        # Negative indices
        self.assertEqual(self.redis.lrange("mylist", -3, -1), ["3", "4", "5"])

        # Mix positive and negative
        self.assertEqual(self.redis.lrange("mylist", 1, -2), ["1", "2", "3", "4"])

        # All elements
        self.assertEqual(self.redis.lrange("mylist", 0, -1), ["0", "1", "2", "3", "4", "5"])

    def test_lrange_nonexistent_key(self):
        """Test lrange on nonexistent key."""
        result = self.redis.lrange("nonexistent", 0, -1)
        self.assertEqual(result, [])

    def test_ltrim(self):
        """Test ltrim operation."""
        self.redis.rpush("mylist", "0", "1", "2", "3", "4", "5")

        result = self.redis.ltrim("mylist", 1, 4)
        self.assertTrue(result)

        self.assertEqual(self.redis.lrange("mylist", 0, -1), ["1", "2", "3", "4"])

    def test_ltrim_with_negative_indices(self):
        """Test ltrim with negative indices."""
        self.redis.rpush("mylist", "0", "1", "2", "3", "4", "5")

        result = self.redis.ltrim("mylist", 1, -2)
        self.assertTrue(result)

        self.assertEqual(self.redis.lrange("mylist", 0, -1), ["1", "2", "3", "4"])

    def test_ltrim_empty_result(self):
        """Test ltrim that results in empty list."""
        self.redis.rpush("mylist", "one", "two", "three")

        result = self.redis.ltrim("mylist", 5, 10)
        self.assertTrue(result)

        # Key should be deleted when list becomes empty
        self.assertEqual(self.redis.llen("mylist"), 0)

    def test_lrem_positive_count(self):
        """Test lrem with positive count (remove from head)."""
        self.redis.rpush("mylist", "a", "b", "a", "c", "a", "d")

        removed = self.redis.lrem("mylist", 2, "a")
        self.assertEqual(removed, 2)

        self.assertEqual(self.redis.lrange("mylist", 0, -1), ["b", "c", "a", "d"])

    def test_lrem_negative_count(self):
        """Test lrem with negative count (remove from tail)."""
        self.redis.rpush("mylist", "a", "b", "a", "c", "a", "d")

        removed = self.redis.lrem("mylist", -2, "a")
        self.assertEqual(removed, 2)

        self.assertEqual(self.redis.lrange("mylist", 0, -1), ["a", "b", "c", "d"])

    def test_lrem_zero_count(self):
        """Test lrem with zero count (remove all)."""
        self.redis.rpush("mylist", "a", "b", "a", "c", "a", "d")

        removed = self.redis.lrem("mylist", 0, "a")
        self.assertEqual(removed, 3)

        self.assertEqual(self.redis.lrange("mylist", 0, -1), ["b", "c", "d"])

    def test_lrem_nonexistent_key(self):
        """Test lrem on nonexistent key."""
        removed = self.redis.lrem("nonexistent", 1, "value")
        self.assertEqual(removed, 0)

    def test_lrem_value_not_found(self):
        """Test lrem when value doesn't exist."""
        self.redis.rpush("mylist", "a", "b", "c")

        removed = self.redis.lrem("mylist", 1, "d")
        self.assertEqual(removed, 0)

    def test_type_checking_string_to_list(self):
        """Test that list operations fail on string keys."""
        self.redis.set("mykey", "string_value")

        with self.assertRaises(TypeError):
            self.redis.lpush("mykey", "value")

        with self.assertRaises(TypeError):
            self.redis.rpush("mykey", "value")

        with self.assertRaises(TypeError):
            self.redis.lpop("mykey")

        with self.assertRaises(TypeError):
            self.redis.lrange("mykey", 0, -1)

    def test_type_checking_list_to_string(self):
        """Test that string operations fail on list keys."""
        self.redis.rpush("mylist", "one", "two")

        with self.assertRaises(TypeError):
            self.redis.get("mylist")

        with self.assertRaises(TypeError):
            self.redis.incr("mylist")

    def test_list_expiration(self):
        """Test that lists expire correctly."""
        self.redis.rpush("mylist", "one", "two", "three")
        self.redis.expire("mylist", 1)

        # Should exist immediately
        self.assertEqual(self.redis.llen("mylist"), 3)

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        self.assertEqual(self.redis.llen("mylist"), 0)
        self.assertIsNone(self.redis.lpop("mylist"))

    def test_list_ttl(self):
        """Test TTL on list keys."""
        self.redis.rpush("mylist", "one", "two")

        # No expiration
        self.assertEqual(self.redis.ttl("mylist"), -1)

        # Set expiration
        self.redis.expire("mylist", 10)
        ttl = self.redis.ttl("mylist")
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 10)

    def test_list_exists(self):
        """Test exists() works with list keys."""
        self.assertEqual(self.redis.exists("mylist"), 0)

        self.redis.rpush("mylist", "value")
        self.assertEqual(self.redis.exists("mylist"), 1)

    def test_list_delete(self):
        """Test delete() works with list keys."""
        self.redis.rpush("mylist", "one", "two")

        deleted = self.redis.delete("mylist")
        self.assertEqual(deleted, 1)

        self.assertEqual(self.redis.llen("mylist"), 0)

    def test_list_keys(self):
        """Test keys() includes list keys."""
        self.redis.set("stringkey", "value")
        self.redis.rpush("listkey", "value")

        keys = self.redis.keys()
        self.assertIn("stringkey", keys)
        self.assertIn("listkey", keys)

    def test_list_database_isolation(self):
        """Test that lists are isolated between databases."""
        self.redis.rpush("mylist", "db0_value")

        self.redis.select(1)
        self.redis.rpush("mylist", "db1_value")

        # Verify each database has its own list
        self.assertEqual(self.redis.lrange("mylist", 0, -1), ["db1_value"])

        self.redis.select(0)
        self.assertEqual(self.redis.lrange("mylist", 0, -1), ["db0_value"])

    def test_list_flushdb(self):
        """Test that flushdb clears list keys."""
        self.redis.rpush("mylist", "one", "two")
        self.redis.flushdb()

        self.assertEqual(self.redis.llen("mylist"), 0)

    def test_mixed_lpush_rpush(self):
        """Test mixing lpush and rpush operations."""
        self.redis.lpush("mylist", "middle")
        self.redis.lpush("mylist", "left")
        self.redis.rpush("mylist", "right")

        result = self.redis.lrange("mylist", 0, -1)
        self.assertEqual(result, ["left", "middle", "right"])

    def test_empty_list_auto_delete(self):
        """Test that empty lists are automatically deleted."""
        self.redis.rpush("mylist", "one")
        self.redis.lpop("mylist")

        # Key should not exist after list becomes empty
        self.assertEqual(self.redis.exists("mylist"), 0)


if __name__ == "__main__":
    unittest.main()
