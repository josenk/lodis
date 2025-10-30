#!/usr/bin/env python3
"""
Performance benchmark script comparing Redis vs Lodis.

This script runs comprehensive performance tests on both Redis and Lodis
to compare their speed and throughput across various operations.

Usage:
    python benchmark.py                          # Test Lodis only
    python benchmark.py --redis localhost:6379   # Compare with Redis server
"""

import argparse
import time
import statistics
import sys
import getpass
from typing import List, Tuple, Dict, Any

try:
    import redis as redis_module
except ImportError:
    redis_module = None

from lodis import Lodis


class BenchmarkResult:
    """Store results of a benchmark test."""

    def __init__(self, name: str, operations: int):
        self.name = name
        self.operations = operations
        self.lodis_time = None
        self.redis_time = None
        self.lodis_ops_per_sec = None
        self.redis_ops_per_sec = None

    def set_lodis_time(self, time_taken: float):
        self.lodis_time = time_taken
        self.lodis_ops_per_sec = self.operations / time_taken if time_taken > 0 else 0

    def set_redis_time(self, time_taken: float):
        self.redis_time = time_taken
        self.redis_ops_per_sec = self.operations / time_taken if time_taken > 0 else 0

    def get_speedup(self) -> str:
        """Calculate speedup factor (positive means Lodis is faster)."""
        if self.redis_time and self.lodis_time:
            speedup = self.redis_time / self.lodis_time
            if speedup > 1:
                return f"{speedup:.2f}x faster"
            else:
                return f"{1/speedup:.2f}x slower"
        return "N/A"


class PerformanceBenchmark:
    """Performance benchmark suite for Redis vs Lodis."""

    def __init__(self, redis_endpoint: str = None, redis_password: str = None):
        """
        Initialize benchmark suite.

        Args:
            redis_endpoint: Redis server endpoint in format "host:port" or None for Lodis-only
            redis_password: Redis server password or None for no authentication
        """
        self.redis_endpoint = redis_endpoint
        self.redis_client = None
        self.lodis_client = Lodis()
        self.results: List[BenchmarkResult] = []

        # Connect to Redis if endpoint provided
        if redis_endpoint and redis_module:
            try:
                host, port = redis_endpoint.split(":")
                self.redis_client = redis_module.Redis(
                    host=host, port=int(port), password=redis_password, decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                auth_msg = " (authenticated)" if redis_password else ""
                print(f"✓ Connected to Redis at {redis_endpoint}{auth_msg}")
            except Exception as e:
                print(f"✗ Failed to connect to Redis: {e}")
                self.redis_client = None
        elif redis_endpoint and not redis_module:
            print("✗ redis module not installed. Install with: pip install redis")

    def run_benchmark(self, name: str, operations: int, lodis_func, redis_func=None):
        """
        Run a benchmark test.

        Args:
            name: Name of the benchmark
            operations: Number of operations to perform
            lodis_func: Function to test Lodis
            redis_func: Function to test Redis (optional)
        """
        result = BenchmarkResult(name, operations)

        # Benchmark Lodis
        self.lodis_client.flushall()
        start_time = time.perf_counter()
        lodis_func(self.lodis_client)
        lodis_time = time.perf_counter() - start_time
        result.set_lodis_time(lodis_time)

        # Benchmark Redis if available
        if self.redis_client and redis_func:
            try:
                self.redis_client.flushall()
                start_time = time.perf_counter()
                redis_func(self.redis_client)
                redis_time = time.perf_counter() - start_time
                result.set_redis_time(redis_time)
            except Exception as e:
                print(f"  ✗ Redis test failed: {e}")

        self.results.append(result)

        # Print immediate result
        print(f"  Lodis: {result.lodis_ops_per_sec:,.0f} ops/sec ({result.lodis_time:.4f}s)")
        if result.redis_time:
            print(f"  Redis: {result.redis_ops_per_sec:,.0f} ops/sec ({result.redis_time:.4f}s)")
            print(f"  Result: Lodis is {result.get_speedup()}")

    def test_set_operations(self, num_ops: int = 10000):
        """Test SET operations."""
        print(f"\n[1/14] SET Operations ({num_ops:,} operations)")

        def lodis_test(client):
            for i in range(num_ops):
                client.set(f"key_{i}", f"value_{i}")

        def redis_test(client):
            for i in range(num_ops):
                client.set(f"key_{i}", f"value_{i}")

        self.run_benchmark("SET", num_ops, lodis_test, redis_test)

    def test_get_operations(self, num_ops: int = 10000):
        """Test GET operations."""
        print(f"\n[2/14] GET Operations ({num_ops:,} operations)")

        def lodis_test(client):
            # Prepare data
            for i in range(num_ops):
                client.set(f"key_{i}", f"value_{i}")
            # Test GET
            for i in range(num_ops):
                client.get(f"key_{i}")

        def redis_test(client):
            # Prepare data
            for i in range(num_ops):
                client.set(f"key_{i}", f"value_{i}")
            # Test GET
            for i in range(num_ops):
                client.get(f"key_{i}")

        self.run_benchmark("GET", num_ops, lodis_test, redis_test)

    def test_delete_operations(self, num_ops: int = 5000):
        """Test DELETE operations."""
        print(f"\n[3/14] DELETE Operations ({num_ops:,} operations)")

        def lodis_test(client):
            # Prepare data
            for i in range(num_ops):
                client.set(f"key_{i}", f"value_{i}")
            # Test DELETE
            for i in range(num_ops):
                client.delete(f"key_{i}")

        def redis_test(client):
            # Prepare data
            for i in range(num_ops):
                client.set(f"key_{i}", f"value_{i}")
            # Test DELETE
            for i in range(num_ops):
                client.delete(f"key_{i}")

        self.run_benchmark("DELETE", num_ops, lodis_test, redis_test)

    def test_incr_operations(self, num_ops: int = 10000):
        """Test INCR operations."""
        print(f"\n[4/14] INCR Operations ({num_ops:,} operations)")

        def lodis_test(client):
            for i in range(num_ops):
                client.incr("counter")

        def redis_test(client):
            for i in range(num_ops):
                client.incr("counter")

        self.run_benchmark("INCR", num_ops, lodis_test, redis_test)

    def test_lpush_operations(self, num_ops: int = 10000):
        """Test LPUSH operations."""
        print(f"\n[5/14] LPUSH Operations ({num_ops:,} operations)")

        def lodis_test(client):
            for i in range(num_ops):
                client.lpush("mylist", f"value_{i}")

        def redis_test(client):
            for i in range(num_ops):
                client.lpush("mylist", f"value_{i}")

        self.run_benchmark("LPUSH", num_ops, lodis_test, redis_test)

    def test_rpush_operations(self, num_ops: int = 10000):
        """Test RPUSH operations."""
        print(f"\n[6/14] RPUSH Operations ({num_ops:,} operations)")

        def lodis_test(client):
            for i in range(num_ops):
                client.rpush("mylist", f"value_{i}")

        def redis_test(client):
            for i in range(num_ops):
                client.rpush("mylist", f"value_{i}")

        self.run_benchmark("RPUSH", num_ops, lodis_test, redis_test)

    def test_lpop_operations(self, num_ops: int = 5000):
        """Test LPOP operations."""
        print(f"\n[7/14] LPOP Operations ({num_ops:,} operations)")

        def lodis_test(client):
            # Prepare data
            for i in range(num_ops):
                client.rpush("mylist", f"value_{i}")
            # Test LPOP
            for i in range(num_ops):
                client.lpop("mylist")

        def redis_test(client):
            # Prepare data
            for i in range(num_ops):
                client.rpush("mylist", f"value_{i}")
            # Test LPOP
            for i in range(num_ops):
                client.lpop("mylist")

        self.run_benchmark("LPOP", num_ops, lodis_test, redis_test)

    def test_lrange_operations(self, num_ops: int = 1000):
        """Test LRANGE operations."""
        print(f"\n[8/14] LRANGE Operations ({num_ops:,} operations, 1000 items)")

        def lodis_test(client):
            # Prepare data
            for i in range(1000):
                client.rpush("mylist", f"value_{i}")
            # Test LRANGE
            for i in range(num_ops):
                client.lrange("mylist", 0, 99)

        def redis_test(client):
            # Prepare data
            for i in range(1000):
                client.rpush("mylist", f"value_{i}")
            # Test LRANGE
            for i in range(num_ops):
                client.lrange("mylist", 0, 99)

        self.run_benchmark("LRANGE", num_ops, lodis_test, redis_test)

    def test_sadd_operations(self, num_ops: int = 10000):
        """Test SADD operations."""
        print(f"\n[9/14] SADD Operations ({num_ops:,} operations)")

        def lodis_test(client):
            for i in range(num_ops):
                client.sadd("myset", f"member_{i}")

        def redis_test(client):
            for i in range(num_ops):
                client.sadd("myset", f"member_{i}")

        self.run_benchmark("SADD", num_ops, lodis_test, redis_test)

    def test_smembers_operations(self, num_ops: int = 1000):
        """Test SMEMBERS operations."""
        print(f"\n[10/14] SMEMBERS Operations ({num_ops:,} operations, 1000 members)")

        def lodis_test(client):
            # Prepare data
            for i in range(1000):
                client.sadd("myset", f"member_{i}")
            # Test SMEMBERS
            for i in range(num_ops):
                client.smembers("myset")

        def redis_test(client):
            # Prepare data
            for i in range(1000):
                client.sadd("myset", f"member_{i}")
            # Test SMEMBERS
            for i in range(num_ops):
                client.smembers("myset")

        self.run_benchmark("SMEMBERS", num_ops, lodis_test, redis_test)

    def test_sismember_operations(self, num_ops: int = 10000):
        """Test SISMEMBER operations."""
        print(f"\n[11/17] SISMEMBER Operations ({num_ops:,} operations)")

        def lodis_test(client):
            # Prepare data
            for i in range(1000):
                client.sadd("myset", f"member_{i}")
            # Test SISMEMBER
            for i in range(num_ops):
                client.sismember("myset", f"member_{i % 1000}")

        def redis_test(client):
            # Prepare data
            for i in range(1000):
                client.sadd("myset", f"member_{i}")
            # Test SISMEMBER
            for i in range(num_ops):
                client.sismember("myset", f"member_{i % 1000}")

        self.run_benchmark("SISMEMBER", num_ops, lodis_test, redis_test)

    def test_zadd_operations(self, num_ops: int = 10000):
        """Test ZADD operations."""
        print(f"\n[12/17] ZADD Operations ({num_ops:,} operations)")

        def lodis_test(client):
            for i in range(num_ops):
                client.zadd("myzset", {f"member_{i}": i})

        def redis_test(client):
            for i in range(num_ops):
                client.zadd("myzset", {f"member_{i}": i})

        self.run_benchmark("ZADD", num_ops, lodis_test, redis_test)

    def test_zrange_operations(self, num_ops: int = 1000):
        """Test ZRANGE operations."""
        print(f"\n[13/17] ZRANGE Operations ({num_ops:,} operations, 1000 members)")

        def lodis_test(client):
            # Prepare data
            for i in range(1000):
                client.zadd("myzset", {f"member_{i}": i})
            # Test ZRANGE
            for i in range(num_ops):
                client.zrange("myzset", 0, 99)

        def redis_test(client):
            # Prepare data
            for i in range(1000):
                client.zadd("myzset", {f"member_{i}": i})
            # Test ZRANGE
            for i in range(num_ops):
                client.zrange("myzset", 0, 99)

        self.run_benchmark("ZRANGE", num_ops, lodis_test, redis_test)

    def test_zscore_operations(self, num_ops: int = 10000):
        """Test ZSCORE operations."""
        print(f"\n[14/17] ZSCORE Operations ({num_ops:,} operations)")

        def lodis_test(client):
            # Prepare data
            for i in range(1000):
                client.zadd("myzset", {f"member_{i}": i})
            # Test ZSCORE
            for i in range(num_ops):
                client.zscore("myzset", f"member_{i % 1000}")

        def redis_test(client):
            # Prepare data
            for i in range(1000):
                client.zadd("myzset", {f"member_{i}": i})
            # Test ZSCORE
            for i in range(num_ops):
                client.zscore("myzset", f"member_{i % 1000}")

        self.run_benchmark("ZSCORE", num_ops, lodis_test, redis_test)

    def test_expire_operations(self, num_ops: int = 5000):
        """Test EXPIRE operations."""
        print(f"\n[15/17] EXPIRE Operations ({num_ops:,} operations)")

        def lodis_test(client):
            # Prepare data
            for i in range(num_ops):
                client.set(f"key_{i}", f"value_{i}")
            # Test EXPIRE
            for i in range(num_ops):
                client.expire(f"key_{i}", 300)

        def redis_test(client):
            # Prepare data
            for i in range(num_ops):
                client.set(f"key_{i}", f"value_{i}")
            # Test EXPIRE
            for i in range(num_ops):
                client.expire(f"key_{i}", 300)

        self.run_benchmark("EXPIRE", num_ops, lodis_test, redis_test)

    def test_exists_operations(self, num_ops: int = 10000):
        """Test EXISTS operations."""
        print(f"\n[16/17] EXISTS Operations ({num_ops:,} operations)")

        def lodis_test(client):
            # Prepare data
            for i in range(num_ops // 2):
                client.set(f"key_{i}", f"value_{i}")
            # Test EXISTS
            for i in range(num_ops):
                client.exists(f"key_{i}")

        def redis_test(client):
            # Prepare data
            for i in range(num_ops // 2):
                client.set(f"key_{i}", f"value_{i}")
            # Test EXISTS
            for i in range(num_ops):
                client.exists(f"key_{i}")

        self.run_benchmark("EXISTS", num_ops, lodis_test, redis_test)

    def test_keys_operations(self, num_ops: int = 100):
        """Test KEYS operations."""
        print(f"\n[17/17] KEYS Operations ({num_ops:,} operations, 1000 keys)")

        def lodis_test(client):
            # Prepare data
            for i in range(1000):
                client.set(f"key_{i}", f"value_{i}")
            # Test KEYS
            for i in range(num_ops):
                client.keys("key_*")

        def redis_test(client):
            # Prepare data
            for i in range(1000):
                client.set(f"key_{i}", f"value_{i}")
            # Test KEYS
            for i in range(num_ops):
                client.keys("key_*")

        self.run_benchmark("KEYS", num_ops, lodis_test, redis_test)

    def run_all_tests(self):
        """Run all benchmark tests."""
        print("\n" + "=" * 70)
        print("PERFORMANCE BENCHMARK: Redis vs Lodis")
        print("=" * 70)

        start_time = time.perf_counter()

        # Run all tests - Strings, Lists, Sets, Sorted Sets
        self.test_set_operations(10000)
        self.test_get_operations(10000)
        self.test_delete_operations(5000)
        self.test_incr_operations(10000)
        self.test_lpush_operations(10000)
        self.test_rpush_operations(10000)
        self.test_lpop_operations(5000)
        self.test_lrange_operations(1000)
        self.test_sadd_operations(10000)
        self.test_smembers_operations(1000)
        self.test_sismember_operations(10000)
        self.test_zadd_operations(10000)
        self.test_zrange_operations(1000)
        self.test_zscore_operations(10000)
        self.test_expire_operations(5000)
        self.test_exists_operations(10000)
        self.test_keys_operations(100)

        total_time = time.perf_counter() - start_time

        # Print summary
        self.print_summary(total_time)

    def print_summary(self, total_time: float):
        """Print benchmark summary."""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        # Table header
        print(f"\n{'Operation':<20} {'Lodis (ops/s)':<20} {'Redis (ops/s)':<20} {'Result':<15}")
        print("-" * 75)

        # Table rows
        for result in self.results:
            lodis_ops = f"{result.lodis_ops_per_sec:,.0f}" if result.lodis_ops_per_sec else "N/A"
            redis_ops = f"{result.redis_ops_per_sec:,.0f}" if result.redis_ops_per_sec else "N/A"
            speedup = result.get_speedup() if result.redis_time else "N/A"

            print(f"{result.name:<20} {lodis_ops:<20} {redis_ops:<20} {speedup:<15}")

        # Overall statistics
        print("\n" + "=" * 70)
        print("STATISTICS")
        print("=" * 70)

        total_lodis_ops = sum(r.operations for r in self.results)
        lodis_total_time = sum(r.lodis_time for r in self.results if r.lodis_time)
        lodis_avg_ops = total_lodis_ops / lodis_total_time if lodis_total_time > 0 else 0

        print(f"\nLodis:")
        print(f"  Total operations: {total_lodis_ops:,}")
        print(f"  Total time: {lodis_total_time:.4f}s")
        print(f"  Average throughput: {lodis_avg_ops:,.0f} ops/sec")

        if any(r.redis_time for r in self.results):
            total_redis_ops = sum(r.operations for r in self.results if r.redis_time)
            redis_total_time = sum(r.redis_time for r in self.results if r.redis_time)
            redis_avg_ops = total_redis_ops / redis_total_time if redis_total_time > 0 else 0

            print(f"\nRedis:")
            print(f"  Total operations: {total_redis_ops:,}")
            print(f"  Total time: {redis_total_time:.4f}s")
            print(f"  Average throughput: {redis_avg_ops:,.0f} ops/sec")

            # Overall comparison
            if redis_avg_ops > 0:
                overall_ratio = lodis_avg_ops / redis_avg_ops
                if overall_ratio > 1:
                    print(f"\nOverall: Lodis is {overall_ratio:.2f}x faster than Redis")
                else:
                    print(f"\nOverall: Lodis is {1/overall_ratio:.2f}x slower than Redis")

        print(f"\nTotal benchmark time: {total_time:.2f}s")
        print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Performance benchmark comparing Redis vs Lodis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python benchmark.py                                    # Test Lodis only
  python benchmark.py --redis localhost:6379             # Compare with Redis server
  python benchmark.py --redis localhost:6379 --redis-password mypassword  # With authentication
  python benchmark.py --redis localhost:6379 --redis-password  # Prompt for password
        """
    )

    parser.add_argument(
        "--redis",
        type=str,
        default=None,
        help="Redis server endpoint in format 'host:port' (e.g., localhost:6379)"
    )

    parser.add_argument(
        "--redis-password",
        type=str,
        nargs="?",
        const="__prompt__",
        default=None,
        help="Redis server password. If flag is provided without value, will prompt for password."
    )

    args = parser.parse_args()

    # Handle password prompting
    redis_password = None
    if args.redis_password == "__prompt__":
        # User specified --redis-password without a value, prompt for it
        redis_password = getpass.getpass("Redis password: ")
    elif args.redis_password:
        # User provided a password value
        redis_password = args.redis_password

    # Run benchmark
    benchmark = PerformanceBenchmark(redis_endpoint=args.redis, redis_password=redis_password)
    benchmark.run_all_tests()


if __name__ == "__main__":
    main()
