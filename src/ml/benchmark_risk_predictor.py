"""
Benchmarking module for supplier risk score calculation.

Measures latency and throughput of predict_supplier_risk() and batch_predict()
functions from src.ml.risk_predictor.
"""
import argparse
import logging
import statistics
import sys
import time
from pathlib import Path

from src.db.database import get_connection, release_connection
from src.ml.risk_predictor import batch_predict, predict_supplier_risk

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _seed_test_suppliers(count: int = 10) -> list[str]:
    """Create test suppliers in the database if none exist.

    Returns a list of supplier IDs created or found.
    """
    conn = get_connection()
    try:
        # Check existing suppliers
        rows = []
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM suppliers LIMIT ?", (count,))
            rows = cur.fetchall()
            cur.close()
        except Exception:
            pass

        if len(rows) >= count:
            supplier_ids = [str(r["id"]) if hasattr(r, "__getitem__") else str(r[0]) for r in rows[:count]]
            return supplier_ids

        # Create test suppliers
        supplier_ids = []
        for i in range(count):
            supplier_id = f"bench_supplier_{i:04d}"
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR IGNORE INTO suppliers
                    (id, name, org_id, risk_tier, certifications, questionnaire_status, country, annual_spend_usd)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    supplier_id,
                    f"Benchmark Supplier {i}",
                    "bench_org",
                    "B" if i % 3 == 0 else "A",
                    "ISO14001" if i % 2 == 0 else "",
                    "pending",
                    "CN" if i % 2 == 0 else "US",
                    100000 + i * 1000,
                ))
                cur.close()
                supplier_ids.append(supplier_id)
            except Exception as e:
                logger.warning("seed_supplier failed id=%s error=%s", supplier_id, e)

        conn.commit()
        return supplier_ids
    finally:
        release_connection(conn)


def _compute_percentiles(values: list[float]) -> dict[str, float]:
    """Compute percentiles from a list of values without numpy."""
    if not values:
        return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def percentile(p: float) -> float:
        idx = int((n - 1) * p)
        if idx < 0:
            idx = 0
        elif idx >= n:
            idx = n - 1
        return sorted_vals[idx]

    return {
        "p50": percentile(0.50),
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
    }


def benchmark_latency(
    supplier_ids: list[str],
    iterations: int = 100,
    warmup: int = 10,
) -> dict:
    """Run latency benchmark for predict_supplier_risk().

    Args:
        supplier_ids: List of supplier IDs to benchmark (轮流使用).
        iterations: Number of measurement iterations.
        warmup: Number of warm-up runs before measurement.

    Returns:
        Dict with benchmark statistics.
    """
    # Warm-up runs
    logger.info("Latency benchmark: warming up with %d runs", warmup)
    for i in range(warmup):
        sid = supplier_ids[i % len(supplier_ids)]
        predict_supplier_risk(sid)

    # Measurement runs
    logger.info("Latency benchmark: running %d measurements", iterations)
    timings: list[float] = []
    errors = 0

    for i in range(iterations):
        sid = supplier_ids[i % len(supplier_ids)]
        start = time.perf_counter()
        try:
            predict_supplier_risk(sid)
        except Exception as e:
            errors += 1
            logger.warning("predict_supplier_risk error supplier_id=%s error=%s", sid, e)
        elapsed = time.perf_counter() - start
        timings.append(elapsed * 1000)  # Convert to ms

    if not timings:
        return {
            "iterations": iterations,
            "errors": errors,
            "mean_ms": 0.0,
            "median_ms": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }

    percentiles = _compute_percentiles(timings)
    mean_ms = statistics.mean(timings)
    median_ms = statistics.median(timings)

    result = {
        "iterations": iterations,
        "errors": errors,
        "mean_ms": round(mean_ms, 3),
        "median_ms": round(median_ms, 3),
    }
    result.update({k: round(v, 3) for k, v in percentiles.items()})
    return result


def benchmark_throughput(
    supplier_count: int = 50,
    iterations: int = 5,
) -> dict:
    """Run throughput benchmark for batch_predict().

    Args:
        supplier_count: Number of suppliers to create/use for the batch test.
        iterations: Number of measurement iterations.

    Returns:
        Dict with throughput statistics.
    """
    # Ensure we have enough suppliers
    supplier_ids = _seed_test_suppliers(supplier_count)
    actual_count = len(supplier_ids)
    logger.info("Throughput benchmark: testing with %d suppliers", actual_count)

    timings: list[float] = []
    errors = 0

    for i in range(iterations):
        start = time.perf_counter()
        try:
            results = batch_predict()
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
            logger.debug(
                "batch_predict iteration=%d suppliers=%d elapsed_s=%.3f",
                i + 1, len(results), elapsed,
            )
        except Exception as e:
            errors += 1
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
            logger.warning("batch_predict error iteration=%d error=%s", i + 1, e)

    if not timings:
        return {
            "iterations": iterations,
            "errors": errors,
            "suppliers": actual_count,
            "predictions_per_second": 0.0,
            "mean_s": 0.0,
        }

    mean_s = statistics.mean(timings)
    preds_per_sec = actual_count / mean_s if mean_s > 0 else 0.0

    return {
        "iterations": iterations,
        "errors": errors,
        "suppliers": actual_count,
        "predictions_per_second": round(preds_per_sec, 2),
        "mean_s": round(mean_s, 3),
    }


def run_benchmarks(
    iterations: int = 100,
    supplier_count: int = 50,
) -> None:
    """Run all benchmarks and print a report."""
    print("\n" + "=" * 60)
    print("SUPPLIER RISK SCORE CALCULATION — BENCHMARK REPORT")
    print("=" * 60)

    # Latency benchmark
    print("\n[1] LATENCY BENCHMARK — predict_supplier_risk()")
    print("-" * 60)

    supplier_ids = _seed_test_suppliers(min(supplier_count, 20))
    if not supplier_ids:
        print("ERROR: No suppliers available for benchmarking.")
        return

    lat = benchmark_latency(supplier_ids, iterations=iterations, warmup=10)
    print(f"  Iterations:   {lat['iterations']}")
    print(f"  Errors:       {lat['errors']}")
    print(f"  Mean (ms):    {lat['mean_ms']}")
    print(f"  Median (ms):  {lat['median_ms']}")
    print(f"  P50 (ms):     {lat['p50']}")
    print(f"  P90 (ms):     {lat['p90']}")
    print(f"  P95 (ms):     {lat['p95']}")
    print(f"  P99 (ms):     {lat['p99']}")

    # Throughput benchmark
    print("\n[2] THROUGHPUT BENCHMARK — batch_predict()")
    print("-" * 60)

    thr = benchmark_throughput(supplier_count=supplier_count, iterations=5)
    print(f"  Iterations:           {thr['iterations']}")
    print(f"  Suppliers:            {thr['suppliers']}")
    print(f"  Errors:              {thr['errors']}")
    print(f"  Predictions/sec:      {thr['predictions_per_second']}")
    print(f"  Mean time (s):       {thr['mean_s']}")

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark supplier risk score calculation.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of latency measurement iterations (default: 100)",
    )
    parser.add_argument(
        "--supplier-count",
        type=int,
        default=50,
        help="Number of suppliers for throughput test (default: 50)",
    )
    args = parser.parse_args()

    run_benchmarks(
        iterations=args.iterations,
        supplier_count=args.supplier_count,
    )


if __name__ == "__main__":
    main()
