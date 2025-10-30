# Lodis

A lightweight, in-memory key-value store with Redis-compatible API. Perfect drop-in replacement for Redis when you don't have a Redis server or need simple embedded caching.

## Features

- **Redis-compatible API** - use `from lodis import Redis` as a drop-in replacement
- **Multiple data types** - Strings, Lists, and Sets (Sorted Sets and Hashes coming soon)
- **16 isolated databases** - just like Redis (db 0-15)
- **In-memory storage** with automatic expiration
- **Thread-safe operations** using mutex locks
- **Key-value storage** with TTL support
- **Redis-style counters** with INCR/DECR operations
- **List operations** - LPUSH, RPUSH, LPOP, RPOP, LRANGE, and more
- **Set operations** - SADD, SREM, SMEMBERS, SINTER, SUNION, and more
- **Zero external dependencies** - uses only Python standard library
- **No network required** - all data stored locally in memory

## Installation

```bash
pip install lodis
```

## Quick Start - Redis Compatible

```python
# Drop-in replacement for Redis
from lodis import Redis

# Create Redis-compatible client (connection params ignored)
r = Redis(host='localhost', port=6379, db=0)

# Use exactly like Redis
r.set("user:123", '{"name": "John", "email": "john@example.com"}')
r.set("session:abc", "active", ex=300)  # TTL in seconds

# Retrieve values
user = r.get("user:123")
print(user)  # '{"name": "John", "email": "john@example.com"}'

# Redis-style counters
r.incr("api_calls:user:123", 1)
r.expire("api_calls:user:123", 3600)  # Set TTL
calls = r.get("api_calls:user:123")
print(f"API calls: {calls}")

# Database isolation (just like Redis)
r.select(1)  # Switch to database 1
r.set("isolated_key", "value in db 1")
r.select(0)  # Back to database 0
print(r.get("isolated_key"))  # None - not in db 0

# List operations
r.rpush("queue", "job1", "job2", "job3")  # Add items to queue
length = r.llen("queue")                   # Get queue length
job = r.lpop("queue")                      # Pop first job
print(f"Processing: {job}")                # Processing: job1

# Set operations
r.sadd("tags", "python", "redis", "cache")  # Add tags
r.sismember("tags", "python")                # Check membership: 1
tags = r.smembers("tags")                    # Get all tags
print(f"Tags: {tags}")                       # Tags: {'python', 'redis', 'cache'}
```

## Alternative Import (same class)

```python
# You can also import as Lodis
from lodis import Lodis

# Same Redis-compatible API
cache = Lodis()
cache.set("key", "value")
cache.get("key")
```

## API Reference

### String Operations (Redis Compatible)

- `set(key, value, ex=None, px=None, nx=False, xx=False)` - Store a key-value pair
  - `ex`: TTL in seconds
  - `px`: TTL in milliseconds
  - `nx`: Only set if key doesn't exist
  - `xx`: Only set if key already exists
- `get(key)` - Retrieve a value (returns None if expired/not found)
- `delete(*keys)` - Delete one or more keys, returns count deleted

### List Operations (Redis Compatible)

```python
# Push operations
r.lpush("queue", "item1", "item2")  # Push to left (head)
r.rpush("queue", "item3", "item4")  # Push to right (tail)

# Pop operations
item = r.lpop("queue")              # Pop from left
items = r.lpop("queue", count=3)    # Pop multiple from left
item = r.rpop("queue")              # Pop from right
items = r.rpop("queue", count=3)    # Pop multiple from right

# Range and length
items = r.lrange("queue", 0, -1)    # Get all items (inclusive)
items = r.lrange("queue", 0, 4)     # Get first 5 items
length = r.llen("queue")            # Get list length

# Index operations
item = r.lindex("queue", 0)         # Get item at index (supports negative)
r.lset("queue", 0, "new_value")     # Set item at index

# Trim and remove
r.ltrim("queue", 0, 99)             # Keep only first 100 items
count = r.lrem("queue", 2, "value") # Remove 2 occurrences of "value"
```

**List API Methods:**
- `lpush(key, *values)` - Push values to the left (head) of list
- `rpush(key, *values)` - Push values to the right (tail) of list
- `lpop(key, count=None)` - Pop from left (returns single or list)
- `rpop(key, count=None)` - Pop from right (returns single or list)
- `lrange(key, start, stop)` - Get slice of list (inclusive end, supports negative indices)
- `llen(key)` - Get length of list
- `lindex(key, index)` - Get element at index
- `lset(key, index, value)` - Set element at index
- `ltrim(key, start, stop)` - Trim list to specified range
- `lrem(key, count, value)` - Remove elements equal to value

### Set Operations (Redis Compatible)

```python
# Add and remove members
r.sadd("myset", "member1", "member2")   # Add members
r.srem("myset", "member1")              # Remove members

# Query operations
members = r.smembers("myset")           # Get all members
exists = r.sismember("myset", "member2") # Check membership (returns 1 or 0)
count = r.scard("myset")                # Get cardinality (count)

# Random operations
member = r.spop("myset")                # Pop random member
member = r.srandmember("myset")         # Get random member (no removal)

# Set algebra
intersection = r.sinter("set1", "set2", "set3")  # Intersection
union = r.sunion("set1", "set2")                 # Union
difference = r.sdiff("set1", "set2")             # Difference

# Move between sets
r.smove("source", "dest", "member")     # Move member between sets
```

**Set API Methods:**
- `sadd(key, *members)` - Add one or more members to set
- `srem(key, *members)` - Remove one or more members from set
- `smembers(key)` - Get all members of set
- `sismember(key, member)` - Check if member exists in set
- `scard(key)` - Get cardinality (number of members)
- `spop(key, count=None)` - Remove and return random member(s)
- `srandmember(key, count=None)` - Get random member(s) without removing
- `sinter(*keys)` - Return intersection of multiple sets
- `sunion(*keys)` - Return union of multiple sets
- `sdiff(*keys)` - Return difference of multiple sets
- `smove(source, destination, member)` - Move member between sets

### Expiration Operations

- `expire(key, seconds)` - Set TTL on existing key (works for all data types)
- `ttl(key)` - Get remaining TTL (-1 if no expiry, -2 if not exists)

### Counter Operations

- `incr(key, amount=1)` - Increment integer value, returns new value
- `decr(key, amount=1)` - Decrement integer value, returns new value

### Key Operations

- `exists(*keys)` - Check if keys exist, returns count (works for all data types)
- `keys(pattern='*')` - List keys matching glob pattern (works for all data types)
- `flushall()` - Delete all keys from all databases
- `flushdb()` - Delete all keys from current database only

### Database Operations

- `select(db)` - Switch to a different database (0-15)
- Redis-style database isolation - each database has separate keyspace

## Use Cases

- **Redis fallback** - Drop-in replacement when Redis server unavailable
- **Testing** - Use in tests without needing Redis infrastructure
- **Session storage** - Store temporary session data with automatic cleanup
- **Rate limiting** - Track API calls, requests per user, etc.
- **Caching** - Store computed results with expiration
- **Embedded applications** - Simple caching without external dependencies

## Easy Migration from Redis

```python
# Your existing Redis code:
# import redis
# r = redis.Redis(host='localhost', port=6379, db=0)

# Simply change the import:
from lodis import Redis
r = Redis(host='localhost', port=6379, db=0)  # Connection params ignored

# Everything else works the same!
r.set('key', 'value')
r.get('key')
r.incr('counter')
r.expire('key', 60)
```

## Performance Benchmarking

Lodis includes a comprehensive benchmark suite to compare performance against Redis:

```bash
# Benchmark Lodis only
python3 benchmark.py

# Compare Lodis vs Redis server
python3 benchmark.py --redis localhost:6379
```

The benchmark tests:
- SET/GET/DELETE operations
- INCR/DECR counters
- EXPIRE/TTL operations
- EXISTS/KEYS queries
- Database switching (SELECT)
- Mixed read/write workloads

Sample output:
```
Operation            Lodis (ops/s)        Redis (ops/s)        Result
---------------------------------------------------------------------------
SET                  1,004,037            450,000              2.23x faster
GET                  1,119,103            500,000              2.24x faster
INCR                 1,614,527            380,000              4.25x faster
...
```

**Note:** Lodis is typically faster than Redis for local operations because:
- No network overhead (in-memory only)
- No serialization/deserialization
- No protocol parsing
- However, Redis excels at networked, multi-client scenarios

## Requirements

- Python 3.7+
- No external dependencies
- Optional: `redis` package for benchmarking against Redis

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.