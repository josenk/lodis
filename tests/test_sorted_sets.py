import unittest
import time
from lodis import Redis


class TestSortedSets(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.redis = Redis()

    def test_zadd_and_zrange(self):
        """Test basic zadd and zrange operations."""
        added = self.redis.zadd("myzset", {"one": 1, "two": 2, "three": 3})
        self.assertEqual(added, 3)

        members = self.redis.zrange("myzset", 0, -1)
        self.assertEqual(members, ["one", "two", "three"])

    def test_zadd_with_scores(self):
        """Test zrange with scores."""
        self.redis.zadd("myzset", {"one": 1, "two": 2, "three": 3})

        result = self.redis.zrange("myzset", 0, -1, withscores=True)
        self.assertEqual(result, [("one", 1.0), ("two", 2.0), ("three", 3.0)])

    def test_zadd_updates(self):
        """Test that zadd updates existing members."""
        self.redis.zadd("myzset", {"member": 1})
        added = self.redis.zadd("myzset", {"member": 2})
        self.assertEqual(added, 0)  # 0 new members added

        score = self.redis.zscore("myzset", "member")
        self.assertEqual(score, 2.0)

    def test_zadd_nx(self):
        """Test zadd with NX flag (only add new)."""
        self.redis.zadd("myzset", {"member": 1})
        added = self.redis.zadd("myzset", {"member": 2}, nx=True)
        self.assertEqual(added, 0)

        score = self.redis.zscore("myzset", "member")
        self.assertEqual(score, 1.0)  # Should not be updated

    def test_zadd_xx(self):
        """Test zadd with XX flag (only update existing)."""
        added = self.redis.zadd("myzset", {"member": 1}, xx=True)
        self.assertEqual(added, 0)  # Should not add

        self.redis.zadd("myzset", {"member": 1})
        added = self.redis.zadd("myzset", {"member": 2}, xx=True)
        self.assertEqual(added, 0)

        score = self.redis.zscore("myzset", "member")
        self.assertEqual(score, 2.0)  # Should be updated

    def test_zadd_gt(self):
        """Test zadd with GT flag (only if new score greater)."""
        self.redis.zadd("myzset", {"member": 5})

        added = self.redis.zadd("myzset", {"member": 3}, gt=True)
        self.assertEqual(self.redis.zscore("myzset", "member"), 5.0)

        added = self.redis.zadd("myzset", {"member": 7}, gt=True)
        self.assertEqual(self.redis.zscore("myzset", "member"), 7.0)

    def test_zadd_lt(self):
        """Test zadd with LT flag (only if new score less)."""
        self.redis.zadd("myzset", {"member": 5})

        added = self.redis.zadd("myzset", {"member": 7}, lt=True)
        self.assertEqual(self.redis.zscore("myzset", "member"), 5.0)

        added = self.redis.zadd("myzset", {"member": 3}, lt=True)
        self.assertEqual(self.redis.zscore("myzset", "member"), 3.0)

    def test_zadd_ch(self):
        """Test zadd with CH flag (return changed count)."""
        changed = self.redis.zadd("myzset", {"one": 1, "two": 2}, ch=True)
        self.assertEqual(changed, 2)

        changed = self.redis.zadd("myzset", {"one": 10, "three": 3}, ch=True)
        self.assertEqual(changed, 2)  # one updated, three added

    def test_zrem(self):
        """Test zrem operation."""
        self.redis.zadd("myzset", {"one": 1, "two": 2, "three": 3})

        removed = self.redis.zrem("myzset", "two")
        self.assertEqual(removed, 1)

        members = self.redis.zrange("myzset", 0, -1)
        self.assertEqual(members, ["one", "three"])

    def test_zrem_multiple(self):
        """Test zrem with multiple members."""
        self.redis.zadd("myzset", {"one": 1, "two": 2, "three": 3, "four": 4})

        removed = self.redis.zrem("myzset", "two", "four", "nonexistent")
        self.assertEqual(removed, 2)

        members = self.redis.zrange("myzset", 0, -1)
        self.assertEqual(members, ["one", "three"])

    def test_zscore(self):
        """Test zscore operation."""
        self.redis.zadd("myzset", {"one": 1.5, "two": 2.7})

        self.assertEqual(self.redis.zscore("myzset", "one"), 1.5)
        self.assertEqual(self.redis.zscore("myzset", "two"), 2.7)
        self.assertIsNone(self.redis.zscore("myzset", "nonexistent"))

    def test_zscore_nonexistent_key(self):
        """Test zscore on nonexistent key."""
        result = self.redis.zscore("nonexistent", "member")
        self.assertIsNone(result)

    def test_zcard(self):
        """Test zcard operation."""
        self.assertEqual(self.redis.zcard("myzset"), 0)

        self.redis.zadd("myzset", {"one": 1, "two": 2, "three": 3})
        self.assertEqual(self.redis.zcard("myzset"), 3)

        self.redis.zrem("myzset", "one")
        self.assertEqual(self.redis.zcard("myzset"), 2)

    def test_zincrby(self):
        """Test zincrby operation."""
        score = self.redis.zincrby("myzset", 5, "member")
        self.assertEqual(score, 5.0)

        score = self.redis.zincrby("myzset", 2.5, "member")
        self.assertEqual(score, 7.5)

        score = self.redis.zincrby("myzset", -3, "member")
        self.assertEqual(score, 4.5)

    def test_zrank(self):
        """Test zrank operation."""
        self.redis.zadd("myzset", {"one": 1, "two": 2, "three": 3, "four": 4})

        self.assertEqual(self.redis.zrank("myzset", "one"), 0)
        self.assertEqual(self.redis.zrank("myzset", "two"), 1)
        self.assertEqual(self.redis.zrank("myzset", "four"), 3)
        self.assertIsNone(self.redis.zrank("myzset", "nonexistent"))

    def test_zrank_with_ties(self):
        """Test zrank with tied scores."""
        self.redis.zadd("myzset", {"a": 1, "b": 1, "c": 2})

        # Tied scores are ordered lexicographically
        self.assertEqual(self.redis.zrank("myzset", "a"), 0)
        self.assertEqual(self.redis.zrank("myzset", "b"), 1)
        self.assertEqual(self.redis.zrank("myzset", "c"), 2)

    def test_zrevrank(self):
        """Test zrevrank operation."""
        self.redis.zadd("myzset", {"one": 1, "two": 2, "three": 3, "four": 4})

        self.assertEqual(self.redis.zrevrank("myzset", "four"), 0)
        self.assertEqual(self.redis.zrevrank("myzset", "three"), 1)
        self.assertEqual(self.redis.zrevrank("myzset", "one"), 3)
        self.assertIsNone(self.redis.zrevrank("myzset", "nonexistent"))

    def test_zrange_various_ranges(self):
        """Test zrange with various range parameters."""
        self.redis.zadd("myzset", {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})

        # Normal range
        self.assertEqual(self.redis.zrange("myzset", 0, 2), ["a", "b", "c"])

        # Start from middle
        self.assertEqual(self.redis.zrange("myzset", 2, 4), ["c", "d", "e"])

        # Negative indices
        self.assertEqual(self.redis.zrange("myzset", -3, -1), ["c", "d", "e"])

        # All elements
        self.assertEqual(self.redis.zrange("myzset", 0, -1), ["a", "b", "c", "d", "e"])

    def test_zrevrange(self):
        """Test zrevrange operation."""
        self.redis.zadd("myzset", {"a": 1, "b": 2, "c": 3, "d": 4})

        result = self.redis.zrevrange("myzset", 0, -1)
        self.assertEqual(result, ["d", "c", "b", "a"])

        result = self.redis.zrevrange("myzset", 0, 1)
        self.assertEqual(result, ["d", "c"])

    def test_zrevrange_with_scores(self):
        """Test zrevrange with scores."""
        self.redis.zadd("myzset", {"a": 1, "b": 2, "c": 3})

        result = self.redis.zrevrange("myzset", 0, -1, withscores=True)
        self.assertEqual(result, [("c", 3.0), ("b", 2.0), ("a", 1.0)])

    def test_zrangebyscore(self):
        """Test zrangebyscore operation."""
        self.redis.zadd("myzset", {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})

        result = self.redis.zrangebyscore("myzset", 2, 4)
        self.assertEqual(result, ["b", "c", "d"])

        result = self.redis.zrangebyscore("myzset", "-inf", 3)
        self.assertEqual(result, ["a", "b", "c"])

        result = self.redis.zrangebyscore("myzset", 3, "+inf")
        self.assertEqual(result, ["c", "d", "e"])

    def test_zrangebyscore_with_scores(self):
        """Test zrangebyscore with scores."""
        self.redis.zadd("myzset", {"a": 1, "b": 2, "c": 3})

        result = self.redis.zrangebyscore("myzset", 1, 2, withscores=True)
        self.assertEqual(result, [("a", 1.0), ("b", 2.0)])

    def test_zcount(self):
        """Test zcount operation."""
        self.redis.zadd("myzset", {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})

        self.assertEqual(self.redis.zcount("myzset", 2, 4), 3)
        self.assertEqual(self.redis.zcount("myzset", "-inf", 3), 3)
        self.assertEqual(self.redis.zcount("myzset", 3, "+inf"), 3)

    def test_zremrangebyrank(self):
        """Test zremrangebyrank operation."""
        self.redis.zadd("myzset", {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})

        removed = self.redis.zremrangebyrank("myzset", 1, 3)
        self.assertEqual(removed, 3)

        remaining = self.redis.zrange("myzset", 0, -1)
        self.assertEqual(remaining, ["a", "e"])

    def test_zremrangebyscore(self):
        """Test zremrangebyscore operation."""
        self.redis.zadd("myzset", {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})

        removed = self.redis.zremrangebyscore("myzset", 2, 4)
        self.assertEqual(removed, 3)

        remaining = self.redis.zrange("myzset", 0, -1)
        self.assertEqual(remaining, ["a", "e"])

    def test_type_checking_string_to_zset(self):
        """Test that sorted set operations fail on string keys."""
        self.redis.set("mykey", "string_value")

        with self.assertRaises(TypeError):
            self.redis.zadd("mykey", {"member": 1})

        with self.assertRaises(TypeError):
            self.redis.zrange("mykey", 0, -1)

    def test_type_checking_list_to_zset(self):
        """Test that sorted set operations fail on list keys."""
        self.redis.rpush("mylist", "one", "two")

        with self.assertRaises(TypeError):
            self.redis.zadd("mylist", {"member": 1})

    def test_type_checking_set_to_zset(self):
        """Test that sorted set operations fail on set keys."""
        self.redis.sadd("myset", "one", "two")

        with self.assertRaises(TypeError):
            self.redis.zadd("myset", {"member": 1})

    def test_type_checking_zset_to_string(self):
        """Test that string operations fail on sorted set keys."""
        self.redis.zadd("myzset", {"member": 1})

        with self.assertRaises(TypeError):
            self.redis.get("myzset")

    def test_zset_expiration(self):
        """Test that sorted sets expire correctly."""
        self.redis.zadd("myzset", {"one": 1, "two": 2})
        self.redis.expire("myzset", 1)

        # Should exist immediately
        self.assertEqual(self.redis.zcard("myzset"), 2)

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        self.assertEqual(self.redis.zcard("myzset"), 0)

    def test_zset_ttl(self):
        """Test TTL on sorted set keys."""
        self.redis.zadd("myzset", {"member": 1})

        # No expiration
        self.assertEqual(self.redis.ttl("myzset"), -1)

        # Set expiration
        self.redis.expire("myzset", 10)
        ttl = self.redis.ttl("myzset")
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 10)

    def test_zset_exists(self):
        """Test exists() works with sorted set keys."""
        self.assertEqual(self.redis.exists("myzset"), 0)

        self.redis.zadd("myzset", {"member": 1})
        self.assertEqual(self.redis.exists("myzset"), 1)

    def test_zset_delete(self):
        """Test delete() works with sorted set keys."""
        self.redis.zadd("myzset", {"one": 1, "two": 2})

        deleted = self.redis.delete("myzset")
        self.assertEqual(deleted, 1)

        self.assertEqual(self.redis.zcard("myzset"), 0)

    def test_zset_keys(self):
        """Test keys() includes sorted set keys."""
        self.redis.set("stringkey", "value")
        self.redis.rpush("listkey", "value")
        self.redis.sadd("setkey", "value")
        self.redis.zadd("zsetkey", {"member": 1})

        keys = self.redis.keys()
        self.assertIn("stringkey", keys)
        self.assertIn("listkey", keys)
        self.assertIn("setkey", keys)
        self.assertIn("zsetkey", keys)

    def test_zset_database_isolation(self):
        """Test that sorted sets are isolated between databases."""
        self.redis.zadd("myzset", {"db0": 1})

        self.redis.select(1)
        self.redis.zadd("myzset", {"db1": 2})

        # Verify each database has its own sorted set
        self.assertEqual(self.redis.zrange("myzset", 0, -1), ["db1"])

        self.redis.select(0)
        self.assertEqual(self.redis.zrange("myzset", 0, -1), ["db0"])

    def test_zset_flushdb(self):
        """Test that flushdb clears sorted set keys."""
        self.redis.zadd("myzset", {"member": 1})
        self.redis.flushdb()

        self.assertEqual(self.redis.zcard("myzset"), 0)

    def test_empty_zset_auto_delete(self):
        """Test that empty sorted sets are automatically deleted."""
        self.redis.zadd("myzset", {"member": 1})
        self.redis.zrem("myzset", "member")

        # Key should not exist after sorted set becomes empty
        self.assertEqual(self.redis.exists("myzset"), 0)

    def test_leaderboard_use_case(self):
        """Test leaderboard use case with sorted sets."""
        # Add players with scores
        self.redis.zadd("leaderboard", {
            "alice": 100,
            "bob": 85,
            "charlie": 95,
            "diana": 110
        })

        # Get top 3 players
        top3 = self.redis.zrevrange("leaderboard", 0, 2, withscores=True)
        self.assertEqual(top3, [("diana", 110.0), ("alice", 100.0), ("charlie", 95.0)])

        # Get alice's rank
        rank = self.redis.zrevrank("leaderboard", "alice")
        self.assertEqual(rank, 1)  # 0-indexed, so 2nd place

        # Increment alice's score
        new_score = self.redis.zincrby("leaderboard", 15, "alice")
        self.assertEqual(new_score, 115.0)

        # Alice should now be first
        rank = self.redis.zrevrank("leaderboard", "alice")
        self.assertEqual(rank, 0)


if __name__ == "__main__":
    unittest.main()
