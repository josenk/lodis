"""
Unit tests for lodis async implementation (asyncio module).
"""

import unittest
import asyncio
import time
import lodis.asyncio as lodis


class TestAsyncLodis(unittest.IsolatedAsyncioTestCase):
    """Test async Lodis implementation using unittest.IsolatedAsyncioTestCase."""

    async def asyncSetUp(self):
        """Set up test fixtures before each test method."""
        self.redis = lodis.Redis()  # Async Redis-compatible interface

    async def test_set_and_get(self):
        """Test basic async set and get operations."""
        await self.redis.set("test_key", "test_value")
        result = await self.redis.get("test_key")
        self.assertEqual(result, "test_value")

    async def test_item_expiration(self):
        """Test that items expire after TTL."""
        await self.redis.set("expire_key", "expire_value", ex=1)  # 1 second TTL
        await asyncio.sleep(1.1)  # Wait for expiration
        result = await self.redis.get("expire_key")
        self.assertIsNone(result)

    async def test_custom_ttl(self):
        """Test custom TTL for items."""
        await self.redis.set("custom_key", "custom_value", ex=2)  # 2 seconds TTL
        await asyncio.sleep(1.1)  # Should still be valid
        result = await self.redis.get("custom_key")
        self.assertEqual(result, "custom_value")

    async def test_setex(self):
        """Test SETEX command (set with expiration)."""
        result = await self.redis.setex("setex_key", 2, "setex_value")
        self.assertTrue(result)
        self.assertEqual(await self.redis.get("setex_key"), "setex_value")

        await asyncio.sleep(2.1)
        self.assertIsNone(await self.redis.get("setex_key"))

    async def test_psetex(self):
        """Test PSETEX command (set with expiration in milliseconds)."""
        result = await self.redis.psetex("psetex_key", 1500, "psetex_value")
        self.assertTrue(result)
        self.assertEqual(await self.redis.get("psetex_key"), "psetex_value")

        await asyncio.sleep(1.6)
        self.assertIsNone(await self.redis.get("psetex_key"))

    async def test_setnx(self):
        """Test SETNX command (set if not exists)."""
        result = await self.redis.setnx("setnx_key", "value1")
        self.assertTrue(result)

        result = await self.redis.setnx("setnx_key", "value2")
        self.assertFalse(result)
        self.assertEqual(await self.redis.get("setnx_key"), "value1")

    async def test_incr_operations(self):
        """Test increment operations."""
        result = await self.redis.incr("test_counter", 5)
        self.assertEqual(result, 5)

        result = await self.redis.incr("test_counter", 3)
        self.assertEqual(result, 8)

        current = await self.redis.get("test_counter")
        self.assertEqual(current, 8)

    async def test_decr_operations(self):
        """Test decrement operations."""
        await self.redis.set("counter", "10")
        result = await self.redis.decr("counter", 3)
        self.assertEqual(result, 7)

        result = await self.redis.decr("counter", 2)
        self.assertEqual(result, 5)

    async def test_incrbyfloat(self):
        """Test INCRBYFLOAT command."""
        result = await self.redis.incrbyfloat("float_counter", 2.5)
        self.assertEqual(result, 2.5)

        result = await self.redis.incrbyfloat("float_counter", 1.3)
        self.assertAlmostEqual(result, 3.8, places=5)

    async def test_delete_operations(self):
        """Test delete operations."""
        await self.redis.set("delete_key", "delete_value")
        deleted_count = await self.redis.delete("delete_key")
        self.assertEqual(deleted_count, 1)
        result = await self.redis.get("delete_key")
        self.assertIsNone(result)

        await self.redis.set("key1", "value1")
        await self.redis.set("key2", "value2")
        deleted_count = await self.redis.delete("key1", "key2", "nonexistent")
        self.assertEqual(deleted_count, 2)

    async def test_keys_method(self):
        """Test retrieving keys with patterns."""
        await self.redis.set("key1", "value1")
        await self.redis.set("key2", "value2")
        await self.redis.set("test_key", "test_value")

        all_keys = await self.redis.keys()
        self.assertEqual(len(all_keys), 3)
        self.assertIn("key1", all_keys)
        self.assertIn("key2", all_keys)
        self.assertIn("test_key", all_keys)

        key_pattern = await self.redis.keys("key*")
        self.assertEqual(len(key_pattern), 2)
        self.assertIn("key1", key_pattern)
        self.assertIn("key2", key_pattern)

    async def test_exists(self):
        """Test EXISTS command."""
        await self.redis.set("exists_key", "value")
        self.assertEqual(await self.redis.exists("exists_key"), 1)
        self.assertEqual(await self.redis.exists("nonexistent"), 0)
        self.assertEqual(await self.redis.exists("exists_key", "nonexistent"), 1)

    async def test_expire_and_ttl(self):
        """Test EXPIRE and TTL commands."""
        await self.redis.set("expire_key", "value")
        result = await self.redis.expire("expire_key", 5)
        self.assertTrue(result)

        ttl = await self.redis.ttl("expire_key")
        self.assertGreaterEqual(ttl, 4)
        self.assertLessEqual(ttl, 5)

    async def test_type_command(self):
        """Test TYPE command."""
        await self.redis.set("string_key", "value")
        self.assertEqual(await self.redis.type("string_key"), "string")

        await self.redis.lpush("list_key", "item")
        self.assertEqual(await self.redis.type("list_key"), "list")

        await self.redis.sadd("set_key", "member")
        self.assertEqual(await self.redis.type("set_key"), "set")

        self.assertEqual(await self.redis.type("nonexistent"), "none")

    async def test_mget_mset(self):
        """Test MGET and MSET commands."""
        await self.redis.mset({"key1": "value1", "key2": "value2", "key3": "value3"})

        values = await self.redis.mget("key1", "key2", "key3", "nonexistent")
        self.assertEqual(values, ["value1", "value2", "value3", None])

    async def test_getset(self):
        """Test GETSET command."""
        await self.redis.set("getset_key", "old_value")
        old_value = await self.redis.getset("getset_key", "new_value")
        self.assertEqual(old_value, "old_value")
        self.assertEqual(await self.redis.get("getset_key"), "new_value")

    async def test_list_operations(self):
        """Test list operations (LPUSH, RPUSH, LPOP, RPOP, LRANGE)."""
        await self.redis.rpush("list_key", "item1", "item2", "item3")
        self.assertEqual(await self.redis.llen("list_key"), 3)

        items = await self.redis.lrange("list_key", 0, -1)
        self.assertEqual(items, ["item1", "item2", "item3"])

        popped = await self.redis.lpop("list_key")
        self.assertEqual(popped, "item1")
        self.assertEqual(await self.redis.llen("list_key"), 2)

        popped = await self.redis.rpop("list_key")
        self.assertEqual(popped, "item3")

    async def test_lpush_rpush(self):
        """Test LPUSH and RPUSH commands."""
        length = await self.redis.lpush("list_key", "item1", "item2")
        self.assertEqual(length, 2)

        items = await self.redis.lrange("list_key", 0, -1)
        self.assertEqual(items, ["item2", "item1"])

        length = await self.redis.rpush("list_key", "item3", "item4")
        self.assertEqual(length, 4)

        items = await self.redis.lrange("list_key", 0, -1)
        self.assertEqual(items, ["item2", "item1", "item3", "item4"])

    async def test_lindex_lset(self):
        """Test LINDEX and LSET commands."""
        await self.redis.rpush("list_key", "item1", "item2", "item3")

        item = await self.redis.lindex("list_key", 1)
        self.assertEqual(item, "item2")

        await self.redis.lset("list_key", 1, "new_item")
        item = await self.redis.lindex("list_key", 1)
        self.assertEqual(item, "new_item")

    async def test_ltrim(self):
        """Test LTRIM command."""
        await self.redis.rpush("list_key", "item1", "item2", "item3", "item4", "item5")
        await self.redis.ltrim("list_key", 1, 3)

        items = await self.redis.lrange("list_key", 0, -1)
        self.assertEqual(items, ["item2", "item3", "item4"])

    async def test_lrem(self):
        """Test LREM command."""
        await self.redis.rpush("list_key", "a", "b", "a", "c", "a")

        removed = await self.redis.lrem("list_key", 2, "a")
        self.assertEqual(removed, 2)

        items = await self.redis.lrange("list_key", 0, -1)
        self.assertEqual(items, ["b", "c", "a"])

    async def test_set_operations(self):
        """Test set operations (SADD, SREM, SMEMBERS, SISMEMBER)."""
        await self.redis.sadd("set_key", "member1", "member2", "member3")
        self.assertEqual(await self.redis.scard("set_key"), 3)

        members = await self.redis.smembers("set_key")
        self.assertEqual(members, {"member1", "member2", "member3"})

        self.assertEqual(await self.redis.sismember("set_key", "member1"), 1)
        self.assertEqual(await self.redis.sismember("set_key", "nonexistent"), 0)

        removed = await self.redis.srem("set_key", "member1")
        self.assertEqual(removed, 1)
        self.assertEqual(await self.redis.scard("set_key"), 2)

    async def test_sadd_srem(self):
        """Test SADD and SREM commands."""
        added = await self.redis.sadd("set_key", "member1", "member2", "member1")
        self.assertEqual(added, 2)

        removed = await self.redis.srem("set_key", "member1", "nonexistent")
        self.assertEqual(removed, 1)

    async def test_spop_srandmember(self):
        """Test SPOP and SRANDMEMBER commands."""
        await self.redis.sadd("set_key", "member1", "member2", "member3")

        member = await self.redis.spop("set_key")
        self.assertIn(member, ["member1", "member2", "member3"])
        self.assertEqual(await self.redis.scard("set_key"), 2)

        await self.redis.sadd("set_key", "member4")
        random_member = await self.redis.srandmember("set_key")
        self.assertIsNotNone(random_member)

    async def test_sinter_sunion_sdiff(self):
        """Test SINTER, SUNION, and SDIFF commands."""
        await self.redis.sadd("set1", "a", "b", "c")
        await self.redis.sadd("set2", "b", "c", "d")

        intersection = await self.redis.sinter("set1", "set2")
        self.assertEqual(intersection, {"b", "c"})

        union = await self.redis.sunion("set1", "set2")
        self.assertEqual(union, {"a", "b", "c", "d"})

        diff = await self.redis.sdiff("set1", "set2")
        self.assertEqual(diff, {"a"})

    async def test_smove(self):
        """Test SMOVE command."""
        await self.redis.sadd("set1", "member1", "member2")
        await self.redis.sadd("set2", "member3")

        result = await self.redis.smove("set1", "set2", "member1")
        self.assertEqual(result, 1)

        self.assertEqual(await self.redis.sismember("set1", "member1"), 0)
        self.assertEqual(await self.redis.sismember("set2", "member1"), 1)

    async def test_sorted_set_operations(self):
        """Test sorted set operations (ZADD, ZRANGE, ZSCORE)."""
        await self.redis.zadd("zset_key", {"member1": 1.0, "member2": 2.0, "member3": 3.0})
        self.assertEqual(await self.redis.zcard("zset_key"), 3)

        members = await self.redis.zrange("zset_key", 0, -1)
        self.assertEqual(members, ["member1", "member2", "member3"])

        members_with_scores = await self.redis.zrange("zset_key", 0, -1, withscores=True)
        self.assertEqual(members_with_scores, [("member1", 1.0), ("member2", 2.0), ("member3", 3.0)])

        score = await self.redis.zscore("zset_key", "member2")
        self.assertEqual(score, 2.0)

    async def test_zadd_options(self):
        """Test ZADD command with various options."""
        added = await self.redis.zadd("zset_key", {"member1": 1.0})
        self.assertEqual(added, 1)

        added = await self.redis.zadd("zset_key", {"member1": 2.0}, nx=True)
        self.assertEqual(added, 0)

        added = await self.redis.zadd("zset_key", {"member1": 3.0}, xx=True)
        self.assertEqual(added, 0)
        self.assertEqual(await self.redis.zscore("zset_key", "member1"), 3.0)

    async def test_zincrby(self):
        """Test ZINCRBY command."""
        await self.redis.zadd("zset_key", {"member1": 1.0})

        new_score = await self.redis.zincrby("zset_key", 2.5, "member1")
        self.assertEqual(new_score, 3.5)

        new_score = await self.redis.zincrby("zset_key", 1.0, "new_member")
        self.assertEqual(new_score, 1.0)

    async def test_zrank_zrevrank(self):
        """Test ZRANK and ZREVRANK commands."""
        await self.redis.zadd("zset_key", {"member1": 1.0, "member2": 2.0, "member3": 3.0})

        rank = await self.redis.zrank("zset_key", "member2")
        self.assertEqual(rank, 1)

        rev_rank = await self.redis.zrevrank("zset_key", "member2")
        self.assertEqual(rev_rank, 1)

    async def test_zrangebyscore(self):
        """Test ZRANGEBYSCORE command."""
        await self.redis.zadd("zset_key", {"member1": 1.0, "member2": 2.0, "member3": 3.0, "member4": 4.0})

        members = await self.redis.zrangebyscore("zset_key", 2.0, 3.0)
        self.assertEqual(members, ["member2", "member3"])

        count = await self.redis.zcount("zset_key", 2.0, 3.0)
        self.assertEqual(count, 2)

    async def test_zrem_zremrangebyrank(self):
        """Test ZREM and ZREMRANGEBYRANK commands."""
        await self.redis.zadd("zset_key", {"member1": 1.0, "member2": 2.0, "member3": 3.0})

        removed = await self.redis.zrem("zset_key", "member2")
        self.assertEqual(removed, 1)
        self.assertEqual(await self.redis.zcard("zset_key"), 2)

        await self.redis.zadd("zset_key", {"member4": 4.0, "member5": 5.0})
        removed = await self.redis.zremrangebyrank("zset_key", 0, 1)
        self.assertEqual(removed, 2)

    async def test_database_operations(self):
        """Test database operations (SELECT, FLUSHDB, FLUSHALL)."""
        await self.redis.set("key1", "value1")

        await self.redis.select(1)
        await self.redis.set("key2", "value2")
        self.assertIsNone(await self.redis.get("key1"))

        await self.redis.select(0)
        self.assertEqual(await self.redis.get("key1"), "value1")

        await self.redis.flushdb()
        self.assertIsNone(await self.redis.get("key1"))

        await self.redis.select(1)
        self.assertEqual(await self.redis.get("key2"), "value2")

        await self.redis.flushall()
        self.assertIsNone(await self.redis.get("key2"))

    async def test_ping(self):
        """Test PING command."""
        self.assertTrue(await self.redis.ping())
        self.assertEqual(await self.redis.ping("hello"), "hello")

    async def test_rename(self):
        """Test RENAME command."""
        await self.redis.set("old_key", "value")
        await self.redis.rename("old_key", "new_key")
        self.assertIsNone(await self.redis.get("old_key"))
        self.assertEqual(await self.redis.get("new_key"), "value")

    async def test_renamenx(self):
        """Test RENAMENX command."""
        await self.redis.set("key1", "value1")
        await self.redis.set("key2", "value2")

        result = await self.redis.renamenx("key1", "key2")
        self.assertEqual(result, 0)

        result = await self.redis.renamenx("key1", "key3")
        self.assertEqual(result, 1)
        self.assertEqual(await self.redis.get("key3"), "value1")

    async def test_persist(self):
        """Test PERSIST command."""
        await self.redis.set("key", "value", ex=10)
        result = await self.redis.persist("key")
        self.assertEqual(result, 1)
        self.assertEqual(await self.redis.ttl("key"), -1)

    async def test_scan(self):
        """Test SCAN command."""
        for i in range(20):
            await self.redis.set(f"key{i}", f"value{i}")

        cursor, keys = await self.redis.scan(0, count=5)
        self.assertGreaterEqual(len(keys), 1)

    async def test_dbsize(self):
        """Test DBSIZE command."""
        await self.redis.set("key1", "value1")
        await self.redis.set("key2", "value2")
        size = await self.redis.dbsize()
        self.assertEqual(size, 2)

    async def test_append_strlen(self):
        """Test APPEND and STRLEN commands."""
        await self.redis.set("key", "hello")
        length = await self.redis.append("key", " world")
        self.assertEqual(length, 11)
        self.assertEqual(await self.redis.get("key"), "hello world")

        length = await self.redis.strlen("key")
        self.assertEqual(length, 11)

    async def test_getdel(self):
        """Test GETDEL command."""
        await self.redis.set("key", "value")
        value = await self.redis.getdel("key")
        self.assertEqual(value, "value")
        self.assertIsNone(await self.redis.get("key"))

    async def test_getex(self):
        """Test GETEX command."""
        await self.redis.set("key", "value")
        value = await self.redis.getex("key", ex=5)
        self.assertEqual(value, "value")

        ttl = await self.redis.ttl("key")
        self.assertGreaterEqual(ttl, 4)
        self.assertLessEqual(ttl, 5)

    async def test_concurrent_operations(self):
        """Test that concurrent async operations work correctly."""
        async def set_and_get(key, value):
            await self.redis.set(key, value)
            return await self.redis.get(key)

        results = await asyncio.gather(
            set_and_get("key1", "value1"),
            set_and_get("key2", "value2"),
            set_and_get("key3", "value3"),
        )

        self.assertEqual(results, ["value1", "value2", "value3"])


if __name__ == "__main__":
    unittest.main()
