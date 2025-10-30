import unittest
import time
from lodis import Redis


class TestSets(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.redis = Redis()

    def test_sadd_and_smembers(self):
        """Test basic sadd and smembers operations."""
        added = self.redis.sadd("myset", "one")
        self.assertEqual(added, 1)

        added = self.redis.sadd("myset", "two", "three")
        self.assertEqual(added, 2)

        members = self.redis.smembers("myset")
        self.assertEqual(members, {"one", "two", "three"})

    def test_sadd_duplicates(self):
        """Test that sadd doesn't add duplicates."""
        added = self.redis.sadd("myset", "one", "two")
        self.assertEqual(added, 2)

        # Try to add existing members
        added = self.redis.sadd("myset", "one", "three")
        self.assertEqual(added, 1)  # Only "three" is new

        members = self.redis.smembers("myset")
        self.assertEqual(members, {"one", "two", "three"})

    def test_srem(self):
        """Test srem operation."""
        self.redis.sadd("myset", "one", "two", "three")

        removed = self.redis.srem("myset", "two")
        self.assertEqual(removed, 1)

        members = self.redis.smembers("myset")
        self.assertEqual(members, {"one", "three"})

    def test_srem_multiple(self):
        """Test srem with multiple members."""
        self.redis.sadd("myset", "one", "two", "three", "four")

        removed = self.redis.srem("myset", "two", "four", "nonexistent")
        self.assertEqual(removed, 2)

        members = self.redis.smembers("myset")
        self.assertEqual(members, {"one", "three"})

    def test_srem_nonexistent_key(self):
        """Test srem on nonexistent key."""
        removed = self.redis.srem("nonexistent", "value")
        self.assertEqual(removed, 0)

    def test_sismember(self):
        """Test sismember operation."""
        self.redis.sadd("myset", "one", "two", "three")

        self.assertEqual(self.redis.sismember("myset", "one"), 1)
        self.assertEqual(self.redis.sismember("myset", "four"), 0)

    def test_sismember_nonexistent_key(self):
        """Test sismember on nonexistent key."""
        result = self.redis.sismember("nonexistent", "value")
        self.assertEqual(result, 0)

    def test_scard(self):
        """Test scard operation."""
        self.assertEqual(self.redis.scard("myset"), 0)

        self.redis.sadd("myset", "one", "two", "three")
        self.assertEqual(self.redis.scard("myset"), 3)

        self.redis.srem("myset", "one")
        self.assertEqual(self.redis.scard("myset"), 2)

    def test_spop_single(self):
        """Test spop for single member."""
        self.redis.sadd("myset", "one", "two", "three")

        member = self.redis.spop("myset")
        self.assertIn(member, {"one", "two", "three"})

        remaining = self.redis.smembers("myset")
        self.assertEqual(len(remaining), 2)
        self.assertNotIn(member, remaining)

    def test_spop_multiple(self):
        """Test spop with count parameter."""
        self.redis.sadd("myset", "one", "two", "three", "four", "five")

        members = self.redis.spop("myset", 3)
        self.assertIsInstance(members, set)
        self.assertEqual(len(members), 3)

        remaining = self.redis.smembers("myset")
        self.assertEqual(len(remaining), 2)

        # Ensure no overlap
        self.assertEqual(len(members & remaining), 0)

    def test_spop_nonexistent_key(self):
        """Test spop on nonexistent key."""
        result = self.redis.spop("nonexistent")
        self.assertIsNone(result)

        result = self.redis.spop("nonexistent", 5)
        self.assertEqual(result, set())

    def test_spop_empty_set(self):
        """Test spop on empty set after all members are removed."""
        self.redis.sadd("myset", "one")
        self.redis.spop("myset")

        # Key should be deleted when set becomes empty
        result = self.redis.spop("myset")
        self.assertIsNone(result)

    def test_srandmember_single(self):
        """Test srandmember for single member."""
        self.redis.sadd("myset", "one", "two", "three")

        member = self.redis.srandmember("myset")
        self.assertIn(member, {"one", "two", "three"})

        # Set should remain unchanged
        self.assertEqual(self.redis.scard("myset"), 3)

    def test_srandmember_multiple(self):
        """Test srandmember with count parameter."""
        self.redis.sadd("myset", "one", "two", "three", "four", "five")

        members = self.redis.srandmember("myset", 3)
        self.assertIsInstance(members, list)
        self.assertEqual(len(members), 3)

        # Set should remain unchanged
        self.assertEqual(self.redis.scard("myset"), 5)

    def test_srandmember_nonexistent_key(self):
        """Test srandmember on nonexistent key."""
        result = self.redis.srandmember("nonexistent")
        self.assertIsNone(result)

        result = self.redis.srandmember("nonexistent", 5)
        self.assertEqual(result, [])

    def test_sinter(self):
        """Test sinter operation."""
        self.redis.sadd("set1", "a", "b", "c", "d")
        self.redis.sadd("set2", "c", "d", "e", "f")
        self.redis.sadd("set3", "c", "d", "g", "h")

        result = self.redis.sinter("set1", "set2", "set3")
        self.assertEqual(result, {"c", "d"})

    def test_sinter_single_set(self):
        """Test sinter with single set."""
        self.redis.sadd("set1", "a", "b", "c")

        result = self.redis.sinter("set1")
        self.assertEqual(result, {"a", "b", "c"})

    def test_sinter_nonexistent_key(self):
        """Test sinter with nonexistent key."""
        self.redis.sadd("set1", "a", "b", "c")

        result = self.redis.sinter("set1", "nonexistent")
        self.assertEqual(result, set())

    def test_sunion(self):
        """Test sunion operation."""
        self.redis.sadd("set1", "a", "b", "c")
        self.redis.sadd("set2", "c", "d", "e")

        result = self.redis.sunion("set1", "set2")
        self.assertEqual(result, {"a", "b", "c", "d", "e"})

    def test_sunion_single_set(self):
        """Test sunion with single set."""
        self.redis.sadd("set1", "a", "b", "c")

        result = self.redis.sunion("set1")
        self.assertEqual(result, {"a", "b", "c"})

    def test_sunion_nonexistent_key(self):
        """Test sunion with nonexistent key."""
        self.redis.sadd("set1", "a", "b", "c")

        result = self.redis.sunion("set1", "nonexistent")
        self.assertEqual(result, {"a", "b", "c"})

    def test_sdiff(self):
        """Test sdiff operation."""
        self.redis.sadd("set1", "a", "b", "c", "d")
        self.redis.sadd("set2", "c", "d")
        self.redis.sadd("set3", "e", "f")

        result = self.redis.sdiff("set1", "set2", "set3")
        self.assertEqual(result, {"a", "b"})

    def test_sdiff_single_set(self):
        """Test sdiff with single set."""
        self.redis.sadd("set1", "a", "b", "c")

        result = self.redis.sdiff("set1")
        self.assertEqual(result, {"a", "b", "c"})

    def test_sdiff_nonexistent_key(self):
        """Test sdiff with nonexistent key."""
        self.redis.sadd("set1", "a", "b", "c")

        result = self.redis.sdiff("set1", "nonexistent")
        self.assertEqual(result, {"a", "b", "c"})

    def test_smove(self):
        """Test smove operation."""
        self.redis.sadd("source", "one", "two", "three")
        self.redis.sadd("dest", "four")

        result = self.redis.smove("source", "dest", "two")
        self.assertEqual(result, 1)

        self.assertEqual(self.redis.smembers("source"), {"one", "three"})
        self.assertEqual(self.redis.smembers("dest"), {"two", "four"})

    def test_smove_nonexistent_member(self):
        """Test smove with nonexistent member."""
        self.redis.sadd("source", "one", "two")

        result = self.redis.smove("source", "dest", "three")
        self.assertEqual(result, 0)

    def test_smove_nonexistent_source(self):
        """Test smove with nonexistent source."""
        result = self.redis.smove("nonexistent", "dest", "member")
        self.assertEqual(result, 0)

    def test_smove_to_new_set(self):
        """Test smove to a new (nonexistent) set."""
        self.redis.sadd("source", "one", "two")

        result = self.redis.smove("source", "newdest", "one")
        self.assertEqual(result, 1)

        self.assertEqual(self.redis.smembers("newdest"), {"one"})

    def test_type_checking_string_to_set(self):
        """Test that set operations fail on string keys."""
        self.redis.set("mykey", "string_value")

        with self.assertRaises(TypeError):
            self.redis.sadd("mykey", "value")

        with self.assertRaises(TypeError):
            self.redis.smembers("mykey")

        with self.assertRaises(TypeError):
            self.redis.scard("mykey")

    def test_type_checking_list_to_set(self):
        """Test that set operations fail on list keys."""
        self.redis.rpush("mylist", "one", "two")

        with self.assertRaises(TypeError):
            self.redis.sadd("mylist", "value")

        with self.assertRaises(TypeError):
            self.redis.smembers("mylist")

    def test_type_checking_set_to_string(self):
        """Test that string operations fail on set keys."""
        self.redis.sadd("myset", "one", "two")

        with self.assertRaises(TypeError):
            self.redis.get("myset")

        with self.assertRaises(TypeError):
            self.redis.incr("myset")

    def test_type_checking_set_to_list(self):
        """Test that list operations fail on set keys."""
        self.redis.sadd("myset", "one", "two")

        with self.assertRaises(TypeError):
            self.redis.lpush("myset", "value")

        with self.assertRaises(TypeError):
            self.redis.lrange("myset", 0, -1)

    def test_set_expiration(self):
        """Test that sets expire correctly."""
        self.redis.sadd("myset", "one", "two", "three")
        self.redis.expire("myset", 1)

        # Should exist immediately
        self.assertEqual(self.redis.scard("myset"), 3)

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        self.assertEqual(self.redis.scard("myset"), 0)
        self.assertIsNone(self.redis.spop("myset"))

    def test_set_ttl(self):
        """Test TTL on set keys."""
        self.redis.sadd("myset", "one", "two")

        # No expiration
        self.assertEqual(self.redis.ttl("myset"), -1)

        # Set expiration
        self.redis.expire("myset", 10)
        ttl = self.redis.ttl("myset")
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 10)

    def test_set_exists(self):
        """Test exists() works with set keys."""
        self.assertEqual(self.redis.exists("myset"), 0)

        self.redis.sadd("myset", "value")
        self.assertEqual(self.redis.exists("myset"), 1)

    def test_set_delete(self):
        """Test delete() works with set keys."""
        self.redis.sadd("myset", "one", "two")

        deleted = self.redis.delete("myset")
        self.assertEqual(deleted, 1)

        self.assertEqual(self.redis.scard("myset"), 0)

    def test_set_keys(self):
        """Test keys() includes set keys."""
        self.redis.set("stringkey", "value")
        self.redis.rpush("listkey", "value")
        self.redis.sadd("setkey", "value")

        keys = self.redis.keys()
        self.assertIn("stringkey", keys)
        self.assertIn("listkey", keys)
        self.assertIn("setkey", keys)

    def test_set_database_isolation(self):
        """Test that sets are isolated between databases."""
        self.redis.sadd("myset", "db0_value")

        self.redis.select(1)
        self.redis.sadd("myset", "db1_value")

        # Verify each database has its own set
        self.assertEqual(self.redis.smembers("myset"), {"db1_value"})

        self.redis.select(0)
        self.assertEqual(self.redis.smembers("myset"), {"db0_value"})

    def test_set_flushdb(self):
        """Test that flushdb clears set keys."""
        self.redis.sadd("myset", "one", "two")
        self.redis.flushdb()

        self.assertEqual(self.redis.scard("myset"), 0)

    def test_empty_set_auto_delete(self):
        """Test that empty sets are automatically deleted."""
        self.redis.sadd("myset", "one")
        self.redis.srem("myset", "one")

        # Key should not exist after set becomes empty
        self.assertEqual(self.redis.exists("myset"), 0)

    def test_smembers_returns_copy(self):
        """Test that smembers returns a copy, not the internal set."""
        self.redis.sadd("myset", "one", "two", "three")

        members = self.redis.smembers("myset")
        members.add("four")

        # Original set should not be modified
        actual_members = self.redis.smembers("myset")
        self.assertEqual(actual_members, {"one", "two", "three"})


if __name__ == "__main__":
    unittest.main()
