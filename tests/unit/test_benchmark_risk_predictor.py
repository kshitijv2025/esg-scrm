"""
Unit tests for benchmark_risk_predictor module.
"""
import argparse
import io
import sys
from unittest.mock import patch

import pytest


class FakeConnection:
    """Minimal fake connection for testing without a real DB."""
    def cursor(self):
        return FakeCursor()

    def commit(self):
        pass

    def close(self):
        pass


class FakeCursor:
    """Minimal fake cursor that returns empty results."""
    def execute(self, query, params=None):
        pass

    def fetchall(self):
        return []

    def fetchone(self):
        return None

    def close(self):
        pass


class TestBenchmarkCompleteness:
    """Test that benchmark runs without error and produces expected fields."""

    def test_benchmark_latency_completes(self):
        """Latency benchmark runs to completion without raising."""
        from src.ml.benchmark_risk_predictor import benchmark_latency

        # Patch DB access and the predict function to avoid real DB calls
        with patch("src.ml.benchmark_risk_predictor.get_connection") as mock_conn:
            mock_conn.return_value = FakeConnection()
            with patch("src.ml.benchmark_risk_predictor.release_connection"):
                with patch("src.ml.benchmark_risk_predictor.predict_supplier_risk") as mock_pred:
                    mock_pred.return_value = {
                        "supplier_id": "sup_001",
                        "risk_score": 42.0,
                        "risk_level": "medium",
                        "factors": {},
                        "recommendation": "test",
                    }
                    supplier_ids = ["sup_001", "sup_002"]
                    result = benchmark_latency(supplier_ids, iterations=5, warmup=2)

        assert isinstance(result, dict)
        assert "iterations" in result
        assert result["iterations"] == 5

    def test_benchmark_latency_output_fields(self):
        """Latency benchmark output contains all required fields."""
        from src.ml.benchmark_risk_predictor import _compute_percentiles

        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        result = _compute_percentiles(values)

        assert "p50" in result
        assert "p90" in result
        assert "p95" in result
        assert "p99" in result
        assert result["p50"] == 5.0  # sorted_vals[4]
        assert result["p90"] == 9.0  # sorted_vals[8]

    def test_benchmark_throughput_completes(self):
        """Throughput benchmark runs to completion without raising."""
        from src.ml.benchmark_risk_predictor import benchmark_throughput

        with patch("src.ml.benchmark_risk_predictor.get_connection") as mock_conn:
            mock_conn.return_value = FakeConnection()

            with patch("src.ml.benchmark_risk_predictor.release_connection"):
                with patch("src.ml.benchmark_risk_predictor.batch_predict") as mock_batch:
                    mock_batch.return_value = [{"supplier_id": f"sup_{i:03d}"} for i in range(10)]
                    result = benchmark_throughput(supplier_count=10, iterations=2)

        assert isinstance(result, dict)
        assert "iterations" in result
        assert "predictions_per_second" in result
        assert "suppliers" in result
        assert "mean_s" in result

    def test_benchmark_throughput_fields_present(self):
        """Throughput benchmark output contains all expected fields."""
        from src.ml.benchmark_risk_predictor import benchmark_throughput

        with patch("src.ml.benchmark_risk_predictor.get_connection") as mock_conn:
            mock_conn.return_value = FakeConnection()

            with patch("src.ml.benchmark_risk_predictor.release_connection"):
                with patch("src.ml.benchmark_risk_predictor.batch_predict") as mock_batch:
                    mock_batch.return_value = [{"supplier_id": f"sup_{i:03d}"} for i in range(50)]
                    result = benchmark_throughput(supplier_count=50, iterations=3)

        required_fields = ["iterations", "errors", "suppliers", "predictions_per_second", "mean_s"]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_percentiles_with_single_value(self):
        """Percentiles computation handles edge case of single value."""
        from src.ml.benchmark_risk_predictor import _compute_percentiles

        result = _compute_percentiles([42.0])
        assert result["p50"] == 42.0
        assert result["p90"] == 42.0
        assert result["p95"] == 42.0
        assert result["p99"] == 42.0

    def test_percentiles_with_empty_list(self):
        """Percentiles computation handles empty list."""
        from src.ml.benchmark_risk_predictor import _compute_percentiles

        result = _compute_percentiles([])
        assert result["p50"] == 0.0
        assert result["p90"] == 0.0
        assert result["p95"] == 0.0
        assert result["p99"] == 0.0


class TestCLIArgumentParsing:
    """Test CLI argument parsing for the benchmark module."""

    def test_default_arguments(self):
        """Module accepts default arguments without error."""
        from src.ml.benchmark_risk_predictor import main

        with patch("src.ml.benchmark_risk_predictor.run_benchmarks") as mock_run:
            with patch("sys.argv", ["benchmark_risk_predictor"]):
                main()
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("iterations") == 100
            assert call_kwargs.get("supplier_count") == 50

    def test_custom_iterations(self):
        """Module accepts --iterations argument."""
        from src.ml.benchmark_risk_predictor import main

        with patch("src.ml.benchmark_risk_predictor.run_benchmarks") as mock_run:
            with patch("sys.argv", ["benchmark_risk_predictor", "--iterations", "25"]):
                main()
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("iterations") == 25

    def test_custom_supplier_count(self):
        """Module accepts --supplier-count argument."""
        from src.ml.benchmark_risk_predictor import main

        with patch("src.ml.benchmark_risk_predictor.run_benchmarks") as mock_run:
            with patch("sys.argv", ["benchmark_risk_predictor", "--supplier-count", "200"]):
                main()
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("supplier_count") == 200

    def test_both_arguments(self):
        """Module accepts both --iterations and --supplier-count."""
        from src.ml.benchmark_risk_predictor import main

        with patch("src.ml.benchmark_risk_predictor.run_benchmarks") as mock_run:
            with patch(
                "sys.argv",
                ["benchmark_risk_predictor", "--iterations", "50", "--supplier-count", "100"],
            ):
                main()
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("iterations") == 50
            assert call_kwargs.get("supplier_count") == 100
