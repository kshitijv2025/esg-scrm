"""
Unit tests for evidence_record module.
Tests EvidenceRecord, LineageNode, ChainProof, and all enum types.
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4


from src.evidence.evidence_record import (
    ChainProof,
    ConfidenceLevel,
    DisclosureFramework,
    EvidenceRecord,
    EvidenceType,
    LineageNode,
    RetentionPolicy,
)


class TestEvidenceType:
    """Tests for EvidenceType enum values."""

    def test_all_evidence_types_exist(self):
        """All expected EvidenceType values are present."""
        assert EvidenceType.API_EXTRACTION.value == "api_extraction"
        assert EvidenceType.MANUAL_ENTRY.value == "manual_entry"
        assert EvidenceType.SUPPLIER_RESPONSE.value == "supplier_response"
        assert EvidenceType.SENSOR_READING.value == "sensor_reading"
        assert EvidenceType.CALCULATION.value == "calculation"

    def test_evidence_type_count(self):
        """Exactly 5 evidence types exist."""
        assert len(EvidenceType) == 5


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum values."""

    def test_all_confidence_levels_exist(self):
        """All expected ConfidenceLevel values are present."""
        assert ConfidenceLevel.HIGH.value == "HIGH"
        assert ConfidenceLevel.MEDIUM.value == "MEDIUM"
        assert ConfidenceLevel.LOW.value == "LOW"

    def test_confidence_level_count(self):
        """Exactly 3 confidence levels exist."""
        assert len(ConfidenceLevel) == 3


class TestRetentionPolicy:
    """Tests for RetentionPolicy enum values."""

    def test_all_retention_policies_exist(self):
        """All expected RetentionPolicy values are present."""
        assert RetentionPolicy.CSRD_7YR.value == "csrd_7yr"
        assert RetentionPolicy.UNLIMITED.value == "unlimited"

    def test_retention_policy_count(self):
        """Exactly 2 retention policies exist."""
        assert len(RetentionPolicy) == 2


class TestDisclosureFramework:
    """Tests for DisclosureFramework enum values."""

    def test_all_disclosure_frameworks_exist(self):
        """All expected DisclosureFramework values are present."""
        assert DisclosureFramework.CSRD.value == "CSRD"
        assert DisclosureFramework.ISSB.value == "ISSB"
        assert DisclosureFramework.GRI.value == "GRI"
        assert DisclosureFramework.TCFD.value == "TCFD"

    def test_disclosure_framework_count(self):
        """Exactly 4 disclosure frameworks exist."""
        assert len(DisclosureFramework) == 4


class TestEvidenceRecordMinimalFields:
    """Tests for EvidenceRecord with minimal required fields."""

    def test_evidence_record_with_required_fields_only(self):
        """EvidenceRecord can be created with only required fields."""
        record_id = uuid4()
        data_point_id = uuid4()
        org_id = uuid4()

        record = EvidenceRecord(
            id=record_id,
            data_point_id=data_point_id,
            organization_id=org_id,
            value=Decimal("100.5"),
            unit="kg CO2e",
            metric_type="emissions",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="https://api.example.com/data",
            raw_source_hash="abc123",
        )

        assert record.id == record_id
        assert record.data_point_id == data_point_id
        assert record.organization_id == org_id
        assert record.value == Decimal("100.5")
        assert record.unit == "kg CO2e"
        assert record.metric_type == "emissions"
        assert record.evidence_type == EvidenceType.API_EXTRACTION
        assert record.raw_source_reference == "https://api.example.com/data"
        assert record.raw_source_hash == "abc123"

    def test_evidence_record_defaults(self):
        """EvidenceRecord has correct default values."""
        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("0"),
            unit="",
            metric_type="",
            evidence_type=EvidenceType.MANUAL_ENTRY,
            raw_source_reference="",
            raw_source_hash="",
        )

        assert record.confidence == ConfidenceLevel.MEDIUM
        assert record.confidence_rationale == ""
        assert record.cryptographic_hash == ""
        assert record.previous_hash == ""
        assert record.chain_valid is True
        assert record.included_in_report is None
        assert record.reported_at is None
        assert record.reported_by is None
        assert record.retained_until is not None  # Set by __post_init__ for CSRD_7YR
        assert record.retention_policy == RetentionPolicy.CSRD_7YR


class TestEvidenceRecordAllFields:
    """Tests for EvidenceRecord with all 19 fields populated."""

    def test_evidence_record_with_all_fields(self):
        """EvidenceRecord can be created with all fields specified."""
        record_id = uuid4()
        data_point_id = uuid4()
        org_id = uuid4()
        report_id = uuid4()
        reported_by = uuid4()
        now = datetime.utcnow()
        retained = datetime(2033, 5, 22)

        calc_inputs = [uuid4(), uuid4()]

        record = EvidenceRecord(
            id=record_id,
            data_point_id=data_point_id,
            organization_id=org_id,
            value=Decimal("1234.567"),
            unit="tonnes",
            metric_type="scope1_emissions",
            evidence_type=EvidenceType.CALCULATION,
            raw_source_reference="aggregation_formula",
            raw_source_hash="hash456",
            calculation_inputs=calc_inputs,
            calculation_formula="sum(sources) * emission_factor",
            calculation_result=Decimal("1234.567"),
            confidence=ConfidenceLevel.HIGH,
            confidence_rationale="Derived from verified sensor data",
            cryptographic_hash="cryptohash789",
            previous_hash="previous123",
            chain_valid=True,
            included_in_report=report_id,
            reported_at=now,
            reported_by=reported_by,
            retained_until=retained,
            retention_policy=RetentionPolicy.UNLIMITED,
        )

        assert record.id == record_id
        assert record.data_point_id == data_point_id
        assert record.organization_id == org_id
        assert record.value == Decimal("1234.567")
        assert record.unit == "tonnes"
        assert record.metric_type == "scope1_emissions"
        assert record.evidence_type == EvidenceType.CALCULATION
        assert record.raw_source_reference == "aggregation_formula"
        assert record.raw_source_hash == "hash456"
        assert record.calculation_inputs == calc_inputs
        assert record.calculation_formula == "sum(sources) * emission_factor"
        assert record.calculation_result == Decimal("1234.567")
        assert record.confidence == ConfidenceLevel.HIGH
        assert record.confidence_rationale == "Derived from verified sensor data"
        assert record.cryptographic_hash == "cryptohash789"
        assert record.previous_hash == "previous123"
        assert record.chain_valid is True
        assert record.included_in_report == report_id
        assert record.reported_at == now
        assert record.reported_by == reported_by
        assert record.retained_until == retained
        assert record.retention_policy == RetentionPolicy.UNLIMITED


class TestEvidenceRecordToDict:
    """Tests for EvidenceRecord.to_dict() method."""

    def test_to_dict_produces_expected_keys(self):
        """to_dict() returns all expected dictionary keys."""
        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("100"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.SENSOR_READING,
            raw_source_reference="sensor-1",
            raw_source_hash="hash123",
        )

        d = record.to_dict()

        expected_keys = {
            "id",
            "data_point_id",
            "organization_id",
            "value",
            "unit",
            "metric_type",
            "evidence_type",
            "raw_source_reference",
            "raw_source_hash",
            "calculation_inputs",
            "calculation_formula",
            "calculation_result",
            "confidence",
            "confidence_rationale",
            "cryptographic_hash",
            "previous_hash",
            "chain_valid",
            "included_in_report",
            "reported_at",
            "reported_by",
            "retained_until",
            "retention_policy",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_values_are_strings_or_proper_types(self):
        """to_dict() serializes values correctly."""
        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("42.5"),
            unit="MWH",
            metric_type="energy",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="api",
            raw_source_hash="hash",
        )

        d = record.to_dict()

        # UUIDs should be stringified
        assert isinstance(d["id"], str)
        assert isinstance(d["data_point_id"], str)
        assert isinstance(d["organization_id"], str)
        # Decimal should be stringified
        assert isinstance(d["value"], str)
        assert d["value"] == "42.5"
        # Enums should have .value accessed
        assert d["evidence_type"] == "api_extraction"
        assert d["confidence"] == "MEDIUM"
        assert d["retention_policy"] == "csrd_7yr"


class TestLineageNode:
    """Tests for LineageNode dataclass."""

    def test_lineage_node_creation(self):
        """LineageNode can be created with required fields."""
        node_id = uuid4()
        now = datetime.utcnow()

        node = LineageNode(
            id=node_id,
            metric_type="emissions",
            value=Decimal("500"),
            unit="tonnes",
            source="manual_entry",
            extraction_timestamp=now,
            confidence=ConfidenceLevel.MEDIUM,
        )

        assert node.id == node_id
        assert node.metric_type == "emissions"
        assert node.value == Decimal("500")
        assert node.unit == "tonnes"
        assert node.source == "manual_entry"
        assert node.extraction_timestamp == now
        assert node.confidence == ConfidenceLevel.MEDIUM
        assert node.children == []

    def test_lineage_node_add_child(self):
        """LineageNode.add_child() adds a child node."""
        parent = LineageNode(
            id=uuid4(),
            metric_type="parent_metric",
            value=Decimal("100"),
            unit="kg",
            source="parent_source",
            extraction_timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel.HIGH,
        )

        child = LineageNode(
            id=uuid4(),
            metric_type="child_metric",
            value=Decimal("50"),
            unit="kg",
            source="child_source",
            extraction_timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel.LOW,
        )

        parent.add_child(child)

        assert len(parent.children) == 1
        assert parent.children[0] == child

    def test_lineage_node_parent_reference(self):
        """Child node has correct parent reference after add_child."""
        parent = LineageNode(
            id=uuid4(),
            metric_type="parent",
            value=Decimal("100"),
            unit="kg",
            source="p",
            extraction_timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel.HIGH,
        )

        child = LineageNode(
            id=uuid4(),
            metric_type="child",
            value=Decimal("50"),
            unit="kg",
            source="c",
            extraction_timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel.LOW,
        )

        parent.add_child(child)

        # Verify the child is correctly linked
        assert parent.children[0].metric_type == "child"
        assert parent.children[0].confidence == ConfidenceLevel.LOW

    def test_lineage_node_get_ancestors(self):
        """LineageNode.get_ancestors() returns depth-first ancestors."""
        leaf = LineageNode(
            id=uuid4(),
            metric_type="leaf",
            value=Decimal("10"),
            unit="kg",
            source="leaf",
            extraction_timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel.LOW,
        )

        middle = LineageNode(
            id=uuid4(),
            metric_type="middle",
            value=Decimal("100"),
            unit="kg",
            source="middle",
            extraction_timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel.MEDIUM,
            children=[leaf],
        )

        root = LineageNode(
            id=uuid4(),
            metric_type="root",
            value=Decimal("1000"),
            unit="kg",
            source="root",
            extraction_timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel.HIGH,
            children=[middle],
        )

        ancestors = root.get_ancestors()
        assert middle in ancestors
        assert leaf in ancestors
        assert root not in ancestors

    def test_lineage_node_get_root_returns_deepest_leaf(self):
        """LineageNode.get_root() returns the deepest leaf in the subtree.

        Note: The get_root() implementation returns the first leaf node,
        not the actual tree root. This is the existing behavior.
        """
        leaf = LineageNode(
            id=uuid4(),
            metric_type="leaf",
            value=Decimal("10"),
            unit="kg",
            source="leaf",
            extraction_timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel.LOW,
        )

        middle = LineageNode(
            id=uuid4(),
            metric_type="middle",
            value=Decimal("100"),
            unit="kg",
            source="middle",
            extraction_timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel.MEDIUM,
            children=[leaf],
        )

        root = LineageNode(
            id=uuid4(),
            metric_type="root",
            value=Decimal("1000"),
            unit="kg",
            source="root",
            extraction_timestamp=datetime.utcnow(),
            confidence=ConfidenceLevel.HIGH,
            children=[middle],
        )

        # get_root() returns the deepest leaf, not the tree root
        assert leaf.get_root() == leaf  # leaf has no children, returns itself
        assert middle.get_root() == leaf  # middle goes to its first child (leaf)
        assert root.get_root() == leaf  # root goes to middle, then to leaf


class TestChainProof:
    """Tests for ChainProof dataclass."""

    def test_chain_proof_creation(self):
        """ChainProof can be created with records."""
        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("100"),
            unit="kg",
            metric_type="test",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="test",
            raw_source_hash="hash",
        )

        proof = ChainProof(records=[record])

        assert proof.records == [record]
        assert proof.chain_valid is True
        assert proof.verification_date is not None

    def test_chain_proof_verify_empty(self):
        """ChainProof.verify() returns True for empty records."""
        proof = ChainProof(records=[])
        assert proof.verify() is True

    def test_chain_proof_verify_valid_genesis(self):
        """ChainProof.verify() returns True for valid genesis record."""
        record = EvidenceRecord.create_genesis(
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("100"),
            unit="kg",
            metric_type="test",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="test",
            raw_source_hash="hash",
            methodology="direct",
        )

        proof = ChainProof(records=[record])
        assert proof.verify() is True


class TestEvidenceRecordCreateGenesis:
    """Tests for EvidenceRecord.create_genesis() method."""

    def test_create_genesis_sets_previous_hash_to_genesis(self):
        """create_genesis() sets previous_hash to GENESIS."""
        record = EvidenceRecord.create_genesis(
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("100"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.SENSOR_READING,
            raw_source_reference="sensor-1",
            raw_source_hash="hash123",
        )

        assert record.previous_hash == "GENESIS"

    def test_create_genesis_computes_cryptographic_hash(self):
        """create_genesis() computes cryptographic hash."""
        record = EvidenceRecord.create_genesis(
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("100"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.SENSOR_READING,
            raw_source_reference="sensor-1",
            raw_source_hash="hash123",
            methodology="calibrated",
        )

        assert record.cryptographic_hash != ""
        # SHA-256 produces 64 character hex string
        assert len(record.cryptographic_hash) == 64


class TestEvidenceRecordComputeHash:
    """Tests for EvidenceRecord.compute_cryptographic_hash() method."""

    def test_compute_cryptographic_hash_returns_sha256(self):
        """compute_cryptographic_hash() returns a SHA-256 hex string."""
        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("100"),
            unit="kg",
            metric_type="emissions",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="test",
            raw_source_hash="hash",
        )

        data_point_id = uuid4()
        value = Decimal("50.5")
        methodology = "direct"
        timestamp = datetime(2024, 1, 15, 10, 30, 0)

        hash_result = record.compute_cryptographic_hash(
            data_point_id=data_point_id,
            value=value,
            methodology=methodology,
            timestamp=timestamp,
        )

        assert len(hash_result) == 64  # SHA-256 hex string length
        assert all(c in "0123456789abcdef" for c in hash_result)


class TestEvidenceRecordVerifyChainRecord:
    """Tests for EvidenceRecord.verify_chain_record() method."""

    def test_verify_chain_record_returns_true_for_valid_record(self):
        """verify_chain_record() returns True when hash matches."""
        record = EvidenceRecord(
            id=uuid4(),
            data_point_id=uuid4(),
            organization_id=uuid4(),
            value=Decimal("100"),
            unit="kg",
            metric_type="test",
            evidence_type=EvidenceType.API_EXTRACTION,
            raw_source_reference="test",
            raw_source_hash="hash",
        )

        data_point_id = uuid4()
        value = Decimal("100")
        methodology = "direct"
        timestamp = datetime.utcnow()

        # First compute the hash
        stored_hash = record.compute_cryptographic_hash(
            data_point_id=data_point_id,
            value=value,
            methodology=methodology,
            timestamp=timestamp,
        )

        # Then verify it
        is_valid = record.verify_chain_record(
            stored_hash=stored_hash,
            data_point_id=data_point_id,
            value=value,
            methodology=methodology,
            timestamp=timestamp,
        )

        assert is_valid is True
        assert record.chain_valid is True
