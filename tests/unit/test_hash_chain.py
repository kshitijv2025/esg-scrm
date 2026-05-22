"""
Unit tests for hash_chain module.
Tests compute_cryptographic_hash, verify_chain_record_v2, and build_chain_proof_v2.
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4


from src.evidence.evidence_record import ChainProof, EvidenceRecord, EvidenceType
from src.evidence.hash_chain import (
    build_chain_proof_v2,
    compute_cryptographic_hash,
    verify_chain_record_v2,
)


class TestComputeCryptographicHash:
    """Tests for compute_cryptographic_hash() function."""

    def test_returns_sha256_hash_string(self):
        """compute_cryptographic_hash() returns a SHA-256 hex string."""
        data_point_id = uuid4()
        value = Decimal("100.5")
        methodology = "direct"
        timestamp = datetime(2024, 6, 15, 12, 30, 0)

        result = compute_cryptographic_hash(
            data_point_id=data_point_id,
            value=value,
            methodology=methodology,
            timestamp=timestamp,
        )

        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 produces 64 character hex string
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_inputs_produce_same_hash(self):
        """Same inputs always produce the same hash."""
        data_point_id = uuid4()
        value = Decimal("500.25")
        methodology = "aggregated"
        timestamp = datetime(2024, 3, 10, 8, 0, 0)

        result1 = compute_cryptographic_hash(
            data_point_id=data_point_id,
            value=value,
            methodology=methodology,
            timestamp=timestamp,
        )

        result2 = compute_cryptographic_hash(
            data_point_id=data_point_id,
            value=value,
            methodology=methodology,
            timestamp=timestamp,
        )

        assert result1 == result2

    def test_different_inputs_produce_different_hash(self):
        """Different inputs produce different hashes."""
        data_point_id1 = uuid4()
        data_point_id2 = uuid4()
        value = Decimal("100")
        methodology = "direct"
        timestamp = datetime(2024, 1, 1, 0, 0, 0)

        result1 = compute_cryptographic_hash(
            data_point_id=data_point_id1,
            value=value,
            methodology=methodology,
            timestamp=timestamp,
        )

        result2 = compute_cryptographic_hash(
            data_point_id=data_point_id2,
            value=value,
            methodology=methodology,
            timestamp=timestamp,
        )

        assert result1 != result2


class TestVerifyChainRecordV2:
    """Tests for verify_chain_record_v2() function."""

    def test_verify_valid_record_returns_true(self):
        """verify_chain_record_v2() returns True for non-genesis record with matching hash."""
        data_point_id = uuid4()
        org_id = uuid4()
        now = datetime.utcnow()
        value = Decimal("250")

        # Create a record manually with properly computed hash
        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=data_point_id,
            organization_id=org_id,
            value=value,
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.SENSOR_READING,
            raw_source_reference="sensor-1",
            raw_source_hash="hash123",
            calculation_formula="direct_measurement",
            previous_hash="GENESIS",
            reported_at=now,
        )

        # Compute the hash using the same method as verify_chain_record_v2
        from src.evidence.hash_chain import compute_cryptographic_hash

        record.cryptographic_hash = compute_cryptographic_hash(
            data_point_id=record.data_point_id,
            value=record.value,
            methodology=record.calculation_formula or "",
            timestamp=record.reported_at or datetime.utcnow(),
        )

        result = verify_chain_record_v2(record, record.previous_hash)

        assert result is True

    def test_verify_tampered_record_returns_false(self):
        """verify_chain_record_v2() returns False for tampered record."""
        data_point_id = uuid4()
        org_id = uuid4()
        now = datetime.utcnow()

        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=data_point_id,
            organization_id=org_id,
            value=Decimal("100"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="api",
            raw_source_hash="hash",
            calculation_formula="direct",
            previous_hash="GENESIS",
            reported_at=now,
        )

        # Compute hash for original value
        from src.evidence.hash_chain import compute_cryptographic_hash

        record.cryptographic_hash = compute_cryptographic_hash(
            data_point_id=record.data_point_id,
            value=record.value,
            methodology=record.calculation_formula or "",
            timestamp=record.reported_at or datetime.utcnow(),
        )

        # Tamper with the record by modifying the value
        record.value = Decimal("999999")

        result = verify_chain_record_v2(record, record.previous_hash)

        assert result is False

    def test_verify_tampered_hash_returns_false(self):
        """verify_chain_record_v2() returns False when hash is modified."""
        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("100"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="api",
            raw_source_hash="hash",
            cryptographic_hash="tampered_hash_value_that_is_not_correct",
            previous_hash="GENESIS",
        )

        result = verify_chain_record_v2(record, record.previous_hash)

        assert result is False


class TestBuildChainProofV2:
    """Tests for build_chain_proof_v2() function."""

    def test_build_chain_proof_returns_chain_proof(self):
        """build_chain_proof_v2() returns a ChainProof object."""
        data_point_id = uuid4()
        org_id = uuid4()
        now = datetime.utcnow()

        # Create a properly configured genesis-like record
        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=data_point_id,
            organization_id=org_id,
            value=Decimal("100"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="api",
            raw_source_hash="hash",
            previous_hash="GENESIS",
            reported_at=now,
            calculation_formula="",
        )

        # Compute hash matching what verify_chain_record_v2 expects
        record.cryptographic_hash = compute_cryptographic_hash(
            data_point_id=record.data_point_id,
            value=record.value,
            methodology=record.calculation_formula or "",
            timestamp=record.reported_at or datetime.utcnow(),
        )

        result = build_chain_proof_v2([record])

        assert isinstance(result, ChainProof)
        assert result.chain_valid is True
        assert result.records == [record]

    def test_build_chain_proof_empty_list_returns_valid_proof(self):
        """build_chain_proof_v2([]) returns valid ChainProof with empty records."""
        result = build_chain_proof_v2([])

        assert isinstance(result, ChainProof)
        assert result.chain_valid is True
        assert result.records == []

    def test_build_chain_proof_valid_chain_returns_valid_proof(self):
        """build_chain_proof_v2() with valid chain returns chain_valid=True."""
        data_point_id = uuid4()
        org_id = uuid4()
        now = datetime.utcnow()

        # Create first record (genesis)
        record1 = EvidenceRecord(
            id=uuid4(),
            data_point_id=data_point_id,
            organization_id=org_id,
            value=Decimal("100"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="api",
            raw_source_hash="hash1",
            previous_hash="GENESIS",
            reported_at=now,
            calculation_formula="",
        )

        record1.cryptographic_hash = compute_cryptographic_hash(
            data_point_id=record1.data_point_id,
            value=record1.value,
            methodology=record1.calculation_formula or "",
            timestamp=record1.reported_at or datetime.utcnow(),
        )

        # Create second record linked to first
        record2 = EvidenceRecord(
            id=uuid4(),
            data_point_id=data_point_id,
            organization_id=org_id,
            value=Decimal("150"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.CALCULATION,
            raw_source_reference="calc",
            raw_source_hash="hash2",
            previous_hash=record1.cryptographic_hash,
            calculation_formula="sum",
            reported_at=now,
            calculation_result=Decimal("150"),
        )

        record2.cryptographic_hash = compute_cryptographic_hash(
            data_point_id=record2.data_point_id,
            value=record2.value,
            methodology=record2.calculation_formula,
            timestamp=record2.reported_at or datetime.utcnow(),
        )

        result = build_chain_proof_v2([record1, record2])

        assert result.chain_valid is True
        assert len(result.records) == 2

    def test_build_chain_proof_invalid_genesis_returns_invalid_proof(self):
        """build_chain_proof_v2() with non-GENESIS first record returns invalid."""
        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("100"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="api",
            raw_source_hash="hash",
            previous_hash="not_genesis",  # Should be GENESIS
        )

        result = build_chain_proof_v2([record])

        assert result.chain_valid is False

    def test_build_chain_proof_broken_link_returns_invalid_proof(self):
        """build_chain_proof_v2() with broken chain link returns invalid."""
        data_point_id = uuid4()
        org_id = uuid4()
        now = datetime.utcnow()

        # First record
        record1 = EvidenceRecord(
            id=uuid4(),
            data_point_id=data_point_id,
            organization_id=org_id,
            value=Decimal("100"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="api",
            raw_source_hash="hash1",
            previous_hash="GENESIS",
            reported_at=now,
            calculation_formula="",
        )

        record1.cryptographic_hash = compute_cryptographic_hash(
            data_point_id=record1.data_point_id,
            value=record1.value,
            methodology=record1.calculation_formula or "",
            timestamp=record1.reported_at or datetime.utcnow(),
        )

        # Second record with WRONG previous_hash (not matching record1's hash)
        record2 = EvidenceRecord(
            id=uuid4(),
            data_point_id=data_point_id,
            organization_id=org_id,
            value=Decimal("150"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.CALCULATION,
            raw_source_reference="calc",
            raw_source_hash="hash2",
            previous_hash="wrong_previous_hash",  # Should be record1.cryptographic_hash
            calculation_formula="sum",
            reported_at=now,
            calculation_result=Decimal("150"),
        )

        record2.cryptographic_hash = compute_cryptographic_hash(
            data_point_id=record2.data_point_id,
            value=record2.value,
            methodology=record2.calculation_formula,
            timestamp=record2.reported_at or datetime.utcnow(),
        )

        result = build_chain_proof_v2([record1, record2])

        assert result.chain_valid is False


class TestHashChainIntegration:
    """Integration tests for hash chain functions."""

    def test_full_chain_workflow(self):
        """Test complete workflow: create records, compute hash, verify chain."""
        data_point_id = uuid4()
        org_id = uuid4()
        now = datetime.utcnow()

        # Create genesis record manually with proper hash computation
        record1 = EvidenceRecord(
            id=uuid4(),
            data_point_id=data_point_id,
            organization_id=org_id,
            value=Decimal("1000"),
            unit="tonnes",
            metric_type="scope1_emissions",
            evidence_type=EvidenceType.SENSOR_READING,
            raw_source_reference="ems_sensor_1",
            raw_source_hash="raw_hash_1",
            previous_hash="GENESIS",
            reported_at=now,
            calculation_formula="continuous_monitoring",
        )

        record1.cryptographic_hash = compute_cryptographic_hash(
            data_point_id=record1.data_point_id,
            value=record1.value,
            methodology=record1.calculation_formula,
            timestamp=record1.reported_at or datetime.utcnow(),
        )

        # Create second record linked to genesis
        record2 = EvidenceRecord(
            id=uuid4(),
            data_point_id=data_point_id,
            organization_id=org_id,
            value=Decimal("1050"),
            unit="tonnes",
            metric_type="scope1_emissions",
            evidence_type=EvidenceType.CALCULATION,
            raw_source_reference="monthly_aggregate",
            raw_source_hash="raw_hash_2",
            previous_hash=record1.cryptographic_hash,
            calculation_formula="sum(daily_readings)",
            calculation_result=Decimal("1050"),
            reported_at=now,
        )

        record2.cryptographic_hash = compute_cryptographic_hash(
            data_point_id=record2.data_point_id,
            value=record2.value,
            methodology=record2.calculation_formula,
            timestamp=record2.reported_at or datetime.utcnow(),
        )

        # Verify individual records
        assert verify_chain_record_v2(record1, record1.previous_hash) is True
        assert verify_chain_record_v2(record2, record2.previous_hash) is True

        # Build chain proof
        proof = build_chain_proof_v2([record1, record2])

        assert proof.chain_valid is True
        assert len(proof.records) == 2
