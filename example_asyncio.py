"""
Example script demonstrating asyncio support in lodis.
"""

import asyncio
import lodis.asyncio as lodis


async def main():
    print("=== Lodis Asyncio Example ===\n")

    # Create async Redis-compatible client
    r = lodis.Redis()

    # String operations
    print("1. String Operations:")
    await r.set("user:123", '{"name": "Alice"}', ex=300)
    user = await r.get("user:123")
    print(f"   User: {user}")

    # Counter operations
    print("\n2. Counter Operations:")
    await r.incr("api_calls")
    await r.incr("api_calls")
    await r.incr("api_calls")
    calls = await r.get("api_calls")
    print(f"   API calls: {calls}")

    # List operations
    print("\n3. List Operations:")
    await r.rpush("queue", "task1", "task2", "task3")
    print(f"   Queue length: {await r.llen('queue')}")
    task = await r.lpop("queue")
    print(f"   Processing: {task}")
    remaining = await r.lrange("queue", 0, -1)
    print(f"   Remaining tasks: {remaining}")

    # Set operations
    print("\n4. Set Operations:")
    await r.sadd("tags", "python", "async", "redis", "cache")
    tags = await r.smembers("tags")
    print(f"   Tags: {tags}")
    is_member = await r.sismember("tags", "python")
    print(f"   Is 'python' a tag? {bool(is_member)}")

    # Sorted set operations
    print("\n5. Sorted Set Operations:")
    await r.zadd("leaderboard", {"Alice": 100, "Bob": 85, "Charlie": 95})
    top_players = await r.zrevrange("leaderboard", 0, 2, withscores=True)
    print(f"   Top 3 players: {top_players}")

    # Concurrent operations
    print("\n6. Concurrent Operations:")
    print("   Setting 5 keys concurrently...")
    start = asyncio.get_event_loop().time()
    await asyncio.gather(
        r.set("key1", "value1"),
        r.set("key2", "value2"),
        r.set("key3", "value3"),
        r.set("key4", "value4"),
        r.set("key5", "value5"),
    )

    print("   Getting 5 keys concurrently...")
    values = await asyncio.gather(
        r.get("key1"),
        r.get("key2"),
        r.get("key3"),
        r.get("key4"),
        r.get("key5"),
    )
    end = asyncio.get_event_loop().time()
    print(f"   Values: {values}")
    print(f"   Time taken: {(end - start) * 1000:.2f}ms")

    # Database operations
    print("\n7. Database Operations:")
    await r.set("db0_key", "value in db 0")
    await r.select(1)
    await r.set("db1_key", "value in db 1")
    print(f"   Key in db 1: {await r.get('db1_key')}")
    print(f"   Key from db 0: {await r.get('db0_key')} (should be None)")
    await r.select(0)
    print(f"   Back to db 0: {await r.get('db0_key')}")

    # Expiration
    print("\n8. Expiration:")
    await r.set("temp_key", "temporary", ex=2)
    print(f"   TTL: {await r.ttl('temp_key')} seconds")
    print("   Waiting 2.5 seconds...")
    await asyncio.sleep(2.5)
    expired = await r.get("temp_key")
    print(f"   After expiration: {expired} (should be None)")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
