# Lodis Performance Benchmark

## Overview

The `benchmark.py` script provides comprehensive performance testing of Lodis, with optional comparison against a Redis server. The benchmark completes in under 2 minutes and tests all major Redis-compatible operations.

## Usage

```bash
# Test Lodis only (fastest, no Redis needed)
python3 benchmark.py

# Compare with local Redis server
python3 benchmark.py --redis localhost:6379

# Compare with remote Redis server
python3 benchmark.py --redis redis.example.com:6379
```

## What Gets Tested

The benchmark runs 10 comprehensive test suites:

1. **SET Operations** (10,000 ops)
   - Basic key-value storage performance
   - Tests write throughput

2. **GET Operations** (10,000 ops)
   - Read performance after data population
   - Tests retrieval speed

3. **DELETE Operations** (5,000 ops)
   - Key deletion performance
   - Tests cleanup speed

4. **INCR Operations** (10,000 ops)
   - Counter increment performance
   - Tests atomic operations

5. **EXPIRE Operations** (5,000 ops)
   - TTL setting performance
   - Tests expiration management

6. **EXISTS Operations** (10,000 ops)
   - Key existence checking
   - Tests lookup speed

7. **KEYS Operations** (100 ops with 1,000 keys)
   - Pattern matching performance
   - Tests filtering operations

8. **Mixed Operations** (10,000 ops)
   - 25% SET, 25% GET, 25% INCR, 25% EXISTS
   - Tests real-world mixed workload

9. **Database SELECT Operations** (5,000 ops)
   - Database switching with SET
   - Tests multi-database performance

10. **SET with TTL Check** (5,000 ops)
    - SET with expiration + TTL query
    - Tests combined operations

## Total Operations

- **70,100 total operations** across all tests
- Completes in well under 2 minutes
- Provides ops/sec metrics for each test
- Shows speedup/slowdown comparison when testing against Redis

## Output

The benchmark provides:

- **Real-time results** for each test
- **Summary table** comparing Lodis vs Redis (if Redis endpoint provided)
- **Overall statistics** including:
  - Total operations performed
  - Total time taken
  - Average throughput (ops/sec)
  - Overall speedup/slowdown factor

## Example Output

```
======================================================================
PERFORMANCE BENCHMARK: Redis vs Lodis
======================================================================

[1/10] SET Operations (10,000 operations)
  Lodis: 1,004,037 ops/sec (0.0100s)
  Redis: 450,000 ops/sec (0.0222s)
  Result: Lodis is 2.23x faster

[2/10] GET Operations (10,000 operations)
  Lodis: 1,119,103 ops/sec (0.0089s)
  Redis: 500,000 ops/sec (0.0200s)
  Result: Lodis is 2.24x faster

...

======================================================================
SUMMARY
======================================================================

Operation            Lodis (ops/s)        Redis (ops/s)        Result
---------------------------------------------------------------------------
SET                  1,004,037            450,000              2.23x faster
GET                  1,119,103            500,000              2.24x faster
DELETE               870,850              380,000              2.29x faster
INCR                 1,614,527            380,000              4.25x faster
...

Overall: Lodis is 2.5x faster than Redis

Total benchmark time: 45.23s
```

## Why Lodis is Faster (for local operations)

Lodis typically outperforms Redis for single-process, local operations because:

1. **No network overhead** - Direct function calls vs TCP/IP
2. **No serialization** - Native Python objects
3. **No protocol parsing** - No RESP protocol overhead
4. **No IPC** - Everything in same process

## When Redis is Better

Redis excels in scenarios where:

- Multiple clients need shared access
- Persistence is required
- Advanced data structures needed (lists, sets, sorted sets)
- Distributed systems with multiple servers
- Pub/sub messaging patterns
- Clustering and high availability

## Requirements

- Python 3.7+
- Optional: `redis` Python package (for comparing with Redis server)

Install redis package: `pip install redis`

## Notes

- The benchmark uses `time.perf_counter()` for high-resolution timing
- All tests flush data before starting to ensure clean state
- Redis comparison is optional - works standalone for Lodis-only testing
- Results may vary based on hardware and system load
