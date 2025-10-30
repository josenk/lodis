import unittest
import time
from lodis import Redis


class TestLodis(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.redis = Redis()  # Redis-compatible interface

    def test_set_and_get(self):
        """Test basic set and get operations."""
        self.redis.set("test_key", "test_value")
        result = self.redis.get("test_key")
        self.assertEqual(result, "test_value")

    def test_item_expiration(self):
        """Test that items expire after TTL."""
        self.redis.set("expire_key", "expire_value", ex=1)  # 1 second TTL
        time.sleep(1.1)  # Wait for expiration
        result = self.redis.get("expire_key")
        self.assertIsNone(result)

    def test_custom_ttl(self):
        """Test custom TTL for items."""
        self.redis.set("custom_key", "custom_value", ex=2)  # 2 seconds TTL
        time.sleep(1.1)  # Should still be valid
        result = self.redis.get("custom_key")
        self.assertEqual(result, "custom_value")

    def test_setex(self):
        """Test SETEX command (set with expiration)."""
        # Test basic setex
        result = self.redis.setex("setex_key", 2, "setex_value")
        self.assertTrue(result)
        self.assertEqual(self.redis.get("setex_key"), "setex_value")

        # Verify expiration works
        time.sleep(2.1)
        self.assertIsNone(self.redis.get("setex_key"))

    def test_incr_operations(self):
        """Test increment operations."""
        result = self.redis.incr("test_counter", 5)
        self.assertEqual(result, 5)

        # Increment again
        result = self.redis.incr("test_counter", 3)
        self.assertEqual(result, 8)

        # Get current value
        current = self.redis.get("test_counter")
        self.assertEqual(current, 8)

    def test_incr_with_expiration(self):
        """Test increment with expiration using expire method."""
        self.redis.incr("expire_counter", 3)
        self.redis.expire("expire_counter", 1)  # 1 second TTL
        time.sleep(1.1)  # Wait for expiration
        result = self.redis.get("expire_counter")
        self.assertIsNone(result)

    def test_delete_operations(self):
        """Test delete operations."""
        self.redis.set("delete_key", "delete_value")
        deleted_count = self.redis.delete("delete_key")
        self.assertEqual(deleted_count, 1)
        result = self.redis.get("delete_key")
        self.assertIsNone(result)

        # Test deleting multiple keys
        self.redis.set("key1", "value1")
        self.redis.set("key2", "value2")
        deleted_count = self.redis.delete("key1", "key2", "nonexistent")
        self.assertEqual(deleted_count, 2)

    def test_keys_method(self):
        """Test retrieving keys with patterns."""
        self.redis.set("key1", "value1")
        self.redis.set("key2", "value2")
        self.redis.set("test_key", "test_value")

        # Get all keys
        all_keys = self.redis.keys()
        self.assertEqual(len(all_keys), 3)
        self.assertIn("key1", all_keys)
        self.assertIn("key2", all_keys)
        self.assertIn("test_key", all_keys)

        # Pattern matching
        key_pattern = self.redis.keys("key*")
        self.assertEqual(len(key_pattern), 2)
        self.assertIn("key1", key_pattern)
        self.assertIn("key2", key_pattern)

    def test_new_redis_methods(self):
        """Test new Redis-specific methods."""
        # Test exists
        self.redis.set("exists_key", "value")
        self.assertEqual(self.redis.exists("exists_key"), 1)
        self.assertEqual(self.redis.exists("nonexistent"), 0)
        self.assertEqual(self.redis.exists("exists_key", "nonexistent"), 1)

        # Test ttl
        self.redis.set("ttl_key", "value", ex=10)
        ttl = self.redis.ttl("ttl_key")
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 10)

        # Test ttl on non-expiring key
        self.redis.set("no_expire", "value")
        self.assertEqual(self.redis.ttl("no_expire"), -1)

        # Test ttl on non-existent key
        self.assertEqual(self.redis.ttl("nonexistent"), -2)

        # Test decr
        self.redis.set("decr_key", "10")
        result = self.redis.decr("decr_key", 3)
        self.assertEqual(result, 7)

        # Test flushall
        self.redis.set("flush_key", "value")
        self.redis.flushall()
        self.assertIsNone(self.redis.get("flush_key"))

    def test_database_isolation(self):
        """Test that databases are isolated from each other."""
        # Start in database 0
        self.redis.set("key1", "value_db0")

        # Switch to database 1 and set a different value
        self.redis.select(1)
        self.redis.set("key1", "value_db1")

        # Switch to database 2
        self.redis.select(2)
        self.redis.set("key1", "value_db2")

        # Verify isolation: each database has its own value
        self.assertEqual(self.redis.get("key1"), "value_db2")

        self.redis.select(1)
        self.assertEqual(self.redis.get("key1"), "value_db1")

        self.redis.select(0)
        self.assertEqual(self.redis.get("key1"), "value_db0")

    def test_database_initialization(self):
        """Test that we can initialize with a specific database."""
        # Create a Redis instance starting at database 5
        r = Redis(db=5)
        r.set("test_key", "test_value_db5")

        # Verify we're in database 5 by switching to 0 and back
        self.assertEqual(r.get("test_key"), "test_value_db5")

        # Switch to database 0 and verify the key doesn't exist there
        r.select(0)
        self.assertIsNone(r.get("test_key"))

        # Set a different value in database 0
        r.set("test_key", "test_value_db0")

        # Switch back to database 5 and verify original value is still there
        r.select(5)
        self.assertEqual(r.get("test_key"), "test_value_db5")

    def test_select_invalid_database(self):
        """Test that selecting invalid database raises error."""
        with self.assertRaises(ValueError):
            self.redis.select(-1)

        with self.assertRaises(ValueError):
            self.redis.select(16)  # Only 0-15 are valid

        with self.assertRaises(ValueError):
            self.redis.select("invalid")

    def test_init_invalid_database(self):
        """Test that initializing with invalid database raises error."""
        with self.assertRaises(ValueError):
            Redis(db=-1)

        with self.assertRaises(ValueError):
            Redis(db=16)

        with self.assertRaises(ValueError):
            Redis(db="invalid")

    def test_flushdb_only_current(self):
        """Test that flushdb only clears current database."""
        # Set keys in database 0
        self.redis.set("key0", "value0")

        # Set keys in database 1
        self.redis.select(1)
        self.redis.set("key1", "value1")

        # Set keys in database 2
        self.redis.select(2)
        self.redis.set("key2", "value2")

        # Flush database 1
        self.redis.select(1)
        self.redis.flushdb()

        # Verify database 1 is empty
        self.assertIsNone(self.redis.get("key1"))

        # Verify database 0 and 2 still have their keys
        self.redis.select(0)
        self.assertEqual(self.redis.get("key0"), "value0")

        self.redis.select(2)
        self.assertEqual(self.redis.get("key2"), "value2")

    def test_flushall_clears_all_databases(self):
        """Test that flushall clears all databases."""
        # Set keys in multiple databases
        self.redis.set("key0", "value0")

        self.redis.select(1)
        self.redis.set("key1", "value1")

        self.redis.select(5)
        self.redis.set("key5", "value5")

        # Flush all databases
        self.redis.flushall()

        # Verify all databases are empty
        self.assertIsNone(self.redis.get("key5"))

        self.redis.select(1)
        self.assertIsNone(self.redis.get("key1"))

        self.redis.select(0)
        self.assertIsNone(self.redis.get("key0"))

    def test_keys_across_databases(self):
        """Test that keys() only shows keys from current database."""
        # Add keys to database 0
        self.redis.set("key0_1", "value1")
        self.redis.set("key0_2", "value2")

        # Add keys to database 1
        self.redis.select(1)
        self.redis.set("key1_1", "value1")
        self.redis.set("key1_2", "value2")

        # Verify database 1 only shows its own keys
        keys = self.redis.keys()
        self.assertEqual(len(keys), 2)
        self.assertIn("key1_1", keys)
        self.assertIn("key1_2", keys)

        # Verify database 0 only shows its own keys
        self.redis.select(0)
        keys = self.redis.keys()
        self.assertEqual(len(keys), 2)
        self.assertIn("key0_1", keys)
        self.assertIn("key0_2", keys)

    def test_exists_across_databases(self):
        """Test that exists() only checks current database."""
        self.redis.set("test_key", "value0")

        self.redis.select(1)
        # Key doesn't exist in database 1
        self.assertEqual(self.redis.exists("test_key"), 0)

        # Back to database 0
        self.redis.select(0)
        self.assertEqual(self.redis.exists("test_key"), 1)

    def test_all_16_databases(self):
        """Test that all 16 databases (0-15) work correctly."""
        # Set a unique value in each database
        for db_num in range(16):
            self.redis.select(db_num)
            self.redis.set(f"db_key", f"value_from_db_{db_num}")

        # Verify each database has its unique value
        for db_num in range(16):
            self.redis.select(db_num)
            self.assertEqual(self.redis.get("db_key"), f"value_from_db_{db_num}")

    # New String Operations Tests
    def test_setnx(self):
        """Test SETNX command (set if not exists)."""
        # Key doesn't exist, should set
        result = self.redis.setnx("new_key", "value")
        self.assertTrue(result)
        self.assertEqual(self.redis.get("new_key"), "value")

        # Key exists, should not set
        result = self.redis.setnx("new_key", "new_value")
        self.assertFalse(result)
        self.assertEqual(self.redis.get("new_key"), "value")

    def test_psetex(self):
        """Test PSETEX command (set with millisecond expiration)."""
        result = self.redis.psetex("psetex_key", 1500, "value")
        self.assertTrue(result)
        self.assertEqual(self.redis.get("psetex_key"), "value")

        time.sleep(1.6)
        self.assertIsNone(self.redis.get("psetex_key"))

    def test_mget_mset(self):
        """Test MGET and MSET commands (batch operations)."""
        # Test mset
        result = self.redis.mset({"key1": "val1", "key2": "val2", "key3": "val3"})
        self.assertTrue(result)

        # Test mget
        values = self.redis.mget("key1", "key2", "key3", "nonexistent")
        self.assertEqual(values, ["val1", "val2", "val3", None])

    def test_getset(self):
        """Test GETSET command (atomic get and set)."""
        # Key doesn't exist
        old_value = self.redis.getset("getset_key", "new_value")
        self.assertIsNone(old_value)
        self.assertEqual(self.redis.get("getset_key"), "new_value")

        # Key exists
        old_value = self.redis.getset("getset_key", "newer_value")
        self.assertEqual(old_value, "new_value")
        self.assertEqual(self.redis.get("getset_key"), "newer_value")

    def test_append(self):
        """Test APPEND command."""
        # Key doesn't exist
        length = self.redis.append("append_key", "Hello")
        self.assertEqual(length, 5)
        self.assertEqual(self.redis.get("append_key"), "Hello")

        # Key exists
        length = self.redis.append("append_key", " World")
        self.assertEqual(length, 11)
        self.assertEqual(self.redis.get("append_key"), "Hello World")

    def test_strlen(self):
        """Test STRLEN command."""
        self.redis.set("strlen_key", "Hello")
        self.assertEqual(self.redis.strlen("strlen_key"), 5)

        # Nonexistent key
        self.assertEqual(self.redis.strlen("nonexistent"), 0)

    def test_getdel(self):
        """Test GETDEL command (get and delete)."""
        self.redis.set("getdel_key", "value")
        value = self.redis.getdel("getdel_key")
        self.assertEqual(value, "value")
        self.assertIsNone(self.redis.get("getdel_key"))

        # Nonexistent key
        self.assertIsNone(self.redis.getdel("nonexistent"))

    def test_getex(self):
        """Test GETEX command (get and update expiration)."""
        self.redis.set("getex_key", "value")

        # Get and set expiration
        value = self.redis.getex("getex_key", ex=2)
        self.assertEqual(value, "value")
        ttl = self.redis.ttl("getex_key")
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 2)

    def test_incrby_decrby(self):
        """Test INCRBY and DECRBY commands."""
        result = self.redis.incrby("counter", 5)
        self.assertEqual(result, 5)

        result = self.redis.incrby("counter", 3)
        self.assertEqual(result, 8)

        result = self.redis.decrby("counter", 2)
        self.assertEqual(result, 6)

    def test_incrbyfloat(self):
        """Test INCRBYFLOAT command."""
        result = self.redis.incrbyfloat("float_counter", 2.5)
        self.assertEqual(result, 2.5)

        result = self.redis.incrbyfloat("float_counter", 1.5)
        self.assertEqual(result, 4.0)

    # Key Management Tests
    def test_type(self):
        """Test TYPE command."""
        self.redis.set("string_key", "value")
        self.assertEqual(self.redis.type("string_key"), "string")

        self.redis.lpush("list_key", "value")
        self.assertEqual(self.redis.type("list_key"), "list")

        self.redis.sadd("set_key", "value")
        self.assertEqual(self.redis.type("set_key"), "set")

        self.assertEqual(self.redis.type("nonexistent"), "none")

    def test_rename(self):
        """Test RENAME command."""
        self.redis.set("old_key", "value")
        result = self.redis.rename("old_key", "new_key")
        self.assertTrue(result)
        self.assertIsNone(self.redis.get("old_key"))
        self.assertEqual(self.redis.get("new_key"), "value")

        # Renaming nonexistent key should raise error
        with self.assertRaises(KeyError):
            self.redis.rename("nonexistent", "new")

    def test_renamenx(self):
        """Test RENAMENX command."""
        self.redis.set("key1", "value1")
        self.redis.set("key2", "value2")

        # Target exists, should not rename
        result = self.redis.renamenx("key1", "key2")
        self.assertEqual(result, 0)
        self.assertEqual(self.redis.get("key1"), "value1")

        # Target doesn't exist, should rename
        result = self.redis.renamenx("key1", "key3")
        self.assertEqual(result, 1)
        self.assertIsNone(self.redis.get("key1"))
        self.assertEqual(self.redis.get("key3"), "value1")

    def test_persist(self):
        """Test PERSIST command."""
        self.redis.set("persist_key", "value", ex=10)

        # Remove expiration
        result = self.redis.persist("persist_key")
        self.assertEqual(result, 1)
        self.assertEqual(self.redis.ttl("persist_key"), -1)

        # Key already persistent
        result = self.redis.persist("persist_key")
        self.assertEqual(result, 0)

    def test_randomkey(self):
        """Test RANDOMKEY command."""
        # Empty database
        self.redis.flushdb()
        self.assertIsNone(self.redis.randomkey())

        # With keys
        self.redis.set("key1", "val1")
        self.redis.set("key2", "val2")
        key = self.redis.randomkey()
        self.assertIn(key, ["key1", "key2"])

    def test_scan(self):
        """Test SCAN command."""
        self.redis.flushdb()

        # Add multiple keys
        for i in range(25):
            self.redis.set(f"key{i}", f"value{i}")

        # Scan with default count
        cursor, keys = self.redis.scan(0)
        self.assertIsInstance(keys, list)
        self.assertGreater(len(keys), 0)

        # Scan with pattern
        cursor, keys = self.redis.scan(0, match="key1*", count=100)
        for key in keys:
            self.assertTrue(key.startswith("key1"))

    # Expiration Tests
    def test_pttl(self):
        """Test PTTL command (TTL in milliseconds)."""
        self.redis.set("pttl_key", "value", ex=2)
        pttl = self.redis.pttl("pttl_key")
        self.assertGreater(pttl, 0)
        self.assertLessEqual(pttl, 2000)

        # Nonexistent key
        self.assertEqual(self.redis.pttl("nonexistent"), -2)

    def test_expireat(self):
        """Test EXPIREAT command."""
        self.redis.set("expireat_key", "value")
        future_timestamp = int(time.time()) + 2
        result = self.redis.expireat("expireat_key", future_timestamp)
        self.assertEqual(result, 1)

        ttl = self.redis.ttl("expireat_key")
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 2)

    def test_pexpire(self):
        """Test PEXPIRE command (expire in milliseconds)."""
        self.redis.set("pexpire_key", "value")
        result = self.redis.pexpire("pexpire_key", 1500)
        self.assertEqual(result, 1)

        time.sleep(1.6)
        self.assertIsNone(self.redis.get("pexpire_key"))

    def test_pexpireat(self):
        """Test PEXPIREAT command."""
        self.redis.set("pexpireat_key", "value")
        future_timestamp_ms = int(time.time() * 1000) + 2000
        result = self.redis.pexpireat("pexpireat_key", future_timestamp_ms)
        self.assertEqual(result, 1)

    # List Operations Tests
    def test_rpoplpush(self):
        """Test RPOPLPUSH command."""
        self.redis.rpush("source", "a", "b", "c")

        element = self.redis.rpoplpush("source", "dest")
        self.assertEqual(element, "c")
        self.assertEqual(self.redis.lrange("source", 0, -1), ["a", "b"])
        self.assertEqual(self.redis.lrange("dest", 0, -1), ["c"])

    def test_blpop(self):
        """Test BLPOP command."""
        self.redis.rpush("list1", "a", "b")
        self.redis.rpush("list2", "c", "d")

        # Pop from first non-empty list
        result = self.redis.blpop("empty", "list1", "list2", timeout=1)
        self.assertEqual(result, ("list1", "a"))

        # All lists empty
        result = self.redis.blpop("empty1", "empty2", timeout=0)
        self.assertIsNone(result)

    def test_brpop(self):
        """Test BRPOP command."""
        self.redis.rpush("list1", "a", "b")

        result = self.redis.brpop("list1", timeout=1)
        self.assertEqual(result, ("list1", "b"))

    def test_brpoplpush(self):
        """Test BRPOPLPUSH command."""
        self.redis.rpush("source", "a", "b", "c")

        element = self.redis.brpoplpush("source", "dest", timeout=1)
        self.assertEqual(element, "c")

    # Server/Utility Tests
    def test_ping(self):
        """Test PING command."""
        # No message
        result = self.redis.ping()
        self.assertTrue(result)

        # With message
        result = self.redis.ping("hello")
        self.assertEqual(result, "hello")

    def test_dbsize(self):
        """Test DBSIZE command."""
        self.redis.flushdb()
        self.assertEqual(self.redis.dbsize(), 0)

        self.redis.set("key1", "val1")
        self.redis.set("key2", "val2")
        self.assertEqual(self.redis.dbsize(), 2)


if __name__ == "__main__":
    unittest.main()