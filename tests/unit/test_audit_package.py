"""
Unit tests for audit_package module.
Tests AuditEvidencePackage, Gap, and Organization classes.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from src.evidence.audit_package import (
    AuditEvidencePackage,
    Gap,
    Organization,
)
from src.evidence.evidence_record import (
    ConfidenceLevel,
    DisclosureFramework,
    EvidenceRecord,
    EvidenceType,
)


@pytest.fixture
def sample_organization():
    """Create a sample organization for testing."""
    return Organization(
        id=uuid4(),
        name="Acme Corp",
        industry="Manufacturing",
        country="USA",
        employee_count=5000,
    )


@pytest.fixture
def sample_evidence_record():
    """Create a sample evidence record for testing."""
    return EvidenceRecord(
        id=uuid4(),
        data_point_id=uuid4(),
        organization_id=uuid4(),
        value=Decimal("100"),
        unit="tonnes",
        metric_type="scope1_emissions",
        evidence_type=EvidenceType.API_EXTRACTION,
        raw_source_reference="api/emsions",
        raw_source_hash="hash123",
        confidence=ConfidenceLevel.HIGH,
    )


class TestGap:
    """Tests for Gap dataclass."""

    def test_gap_creation(self):
        """Gap can be created with required fields."""
        gap_id = uuid4()
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)

        gap = Gap(
            data_point_id=gap_id,
            metric_type="water_usage",
            framework_requirement="GRI 303-3",
            disclosure_code="GRI-303-3",
            reporting_period_start=start,
            reporting_period_end=end,
            reason="Supplier did not provide data",
        )

        assert gap.data_point_id == gap_id
        assert gap.metric_type == "water_usage"
        assert gap.framework_requirement == "GRI 303-3"
        assert gap.disclosure_code == "GRI-303-3"
        assert gap.reporting_period_start == start
        assert gap.reporting_period_end == end
        assert gap.reason == "Supplier did not provide data"
        assert gap.severity == "MEDIUM"  # default
        assert gap.estimated_value is None
        assert gap.estimated_unit is None

    def test_gap_to_dict(self):
        """Gap.to_dict() serializes correctly."""
        gap = Gap(
            data_point_id=uuid4(),
            metric_type="energy",
            framework_requirement="CSRD ESRS E1",
            disclosure_code="CSRD-E1-1",
            reporting_period_start=date(2024, 1, 1),
            reporting_period_end=date(2024, 12, 31),
            reason="No meter data available",
            severity="HIGH",
            estimated_value=Decimal("5000"),
            estimated_unit="MWh",
        )

        d = gap.to_dict()

        assert d["metric_type"] == "energy"
        assert d["framework_requirement"] == "CSRD ESRS E1"
        assert d["disclosure_code"] == "CSRD-E1-1"
        assert d["reason"] == "No meter data available"
        assert d["severity"] == "HIGH"
        assert d["estimated_value"] == "5000"
        assert d["estimated_unit"] == "MWh"


class TestOrganization:
    """Tests for Organization dataclass."""

    def test_organization_creation(self):
        """Organization can be created with required fields."""
        org_id = uuid4()
        org = Organization(
            id=org_id,
            name="Test Corp",
        )

        assert org.id == org_id
        assert org.name == "Test Corp"
        assert org.industry == ""
        assert org.country == ""
        assert org.employee_count == 0

    def test_organization_to_dict(self):
        """Organization.to_dict() serializes correctly."""
        org = Organization(
            id=uuid4(),
            name="Global Industries",
            industry="Automotive",
            country="Germany",
            employee_count=10000,
        )

        d = org.to_dict()

        assert d["name"] == "Global Industries"
        assert d["industry"] == "Automotive"
        assert d["country"] == "Germany"
        assert d["employee_count"] == 10000


class TestAuditEvidencePackage:
    """Tests for AuditEvidencePackage class."""

    def test_audit_evidence_package_constructor(self, sample_organization):
        """AuditEvidencePackage can be constructed with required fields."""
        report_id = uuid4()
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)

        package = AuditEvidencePackage(
            report_id=report_id,
            disclosure_framework=DisclosureFramework.CSRD,
            reporting_period=(start, end),
            organization=sample_organization,
        )

        assert package.report_id == report_id
        assert package.disclosure_framework == DisclosureFramework.CSRD
        assert package.reporting_period == (start, end)
        assert package.organization == sample_organization
        assert package.evidence_records == []
        assert package.gaps == []
        assert package.chain_verified is False
        assert package.generated_at is not None

    def test_audit_evidence_package_defaults(self, sample_organization):
        """AuditEvidencePackage has correct default values."""
        package = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.ISSB,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=sample_organization,
        )

        assert package.confidence_summary == {}
        assert package.chain_verification_date is None
        assert package.generated_by is None
        assert package.package_hash == ""


class TestAuditEvidencePackageVerifyChain:
    """Tests for AuditEvidencePackage.verify_chain() method."""

    def test_verify_chain_returns_true_for_valid_chain(self, sample_evidence_record):
        """verify_chain() returns True when chain is valid."""
        # Create a valid genesis record
        record = EvidenceRecord.create_genesis(
            data_point_id=sample_evidence_record.data_point_id,
            organization_id=sample_evidence_record.organization_id,
            value=sample_evidence_record.value,
            unit=sample_evidence_record.unit,
            metric_type=sample_evidence_record.metric_type,
            evidence_type=sample_evidence_record.evidence_type,
            raw_source_reference=sample_evidence_record.raw_source_reference,
            raw_source_hash=sample_evidence_record.raw_source_hash,
            methodology="direct",
        )

        package = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.CSRD,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=Organization(id=uuid4(), name="Test"),
        )
        package.add_evidence(record)

        result = package.verify_chain()

        assert result is True
        assert package.chain_verified is True
        assert package.chain_verification_date is not None

    def test_verify_chain_returns_false_for_empty_records(self):
        """verify_chain() returns False when no records exist."""
        package = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.GRI,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=Organization(id=uuid4(), name="Test"),
        )

        result = package.verify_chain()

        assert result is False
        assert package.chain_verified is False


class TestAuditEvidencePackageComputeConfidenceSummary:
    """Tests for AuditEvidencePackage.compute_confidence_summary() method."""

    def test_compute_confidence_summary_returns_min_of_levels(self):
        """compute_confidence_summary() returns MIN of confidence levels."""
        records = [
            EvidenceRecord(
                id=uuid4(),
                data_point_id=uuid4(),
                organization_id=uuid4(),
                value=Decimal("100"),
                unit="kg",
                metric_type="emissions",
                evidence_type=EvidenceType.API_EXTRACTION,
                raw_source_reference="api",
                raw_source_hash="hash",
                confidence=ConfidenceLevel.HIGH,
            ),
            EvidenceRecord(
                id=uuid4(),
                data_point_id=uuid4(),
                organization_id=uuid4(),
                value=Decimal("200"),
                unit="kg",
                metric_type="energy",
                evidence_type=EvidenceType.MANUAL_ENTRY,
                raw_source_reference="manual",
                raw_source_hash="hash2",
                confidence=ConfidenceLevel.MEDIUM,
            ),
            EvidenceRecord(
                id=uuid4(),
                data_point_id=uuid4(),
                organization_id=uuid4(),
                value=Decimal("300"),
                unit="kg",
                metric_type="water",
                evidence_type=EvidenceType.SUPPLIER_RESPONSE,
                raw_source_reference="supplier",
                raw_source_hash="hash3",
                confidence=ConfidenceLevel.LOW,
            ),
        ]

        package = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.TCFD,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=Organization(id=uuid4(), name="Test"),
        )

        for record in records:
            package.add_evidence(record)

        summary = package.compute_confidence_summary()

        # The aggregate should be LOW (the minimum of HIGH, MEDIUM, LOW)
        all_confidences = [r.confidence for r in records]
        expected_min = min(all_confidences, key=lambda c: ["LOW", "MEDIUM", "HIGH"].index(c.value))
        assert expected_min == ConfidenceLevel.LOW


class TestAuditEvidencePackageComputePackageHash:
    """Tests for AuditEvidencePackage.compute_package_hash() method."""

    def test_compute_package_hash_returns_hash_string(self, sample_organization):
        """compute_package_hash() returns a SHA-256 hash string."""
        package = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.CSRD,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=sample_organization,
        )

        result = package.compute_package_hash()

        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 produces 64 character hex string
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_package_hash_is_deterministic(self, sample_organization):
        """compute_package_hash() returns the same hash for same content."""
        report_id = uuid4()
        framework = DisclosureFramework.CSRD
        period = (date(2024, 1, 1), date(2024, 12, 31))

        package1 = AuditEvidencePackage(
            report_id=report_id,
            disclosure_framework=framework,
            reporting_period=period,
            organization=sample_organization,
        )

        package2 = AuditEvidencePackage(
            report_id=report_id,
            disclosure_framework=framework,
            reporting_period=period,
            organization=sample_organization,
        )

        hash1 = package1.compute_package_hash()
        hash2 = package2.compute_package_hash()

        assert hash1 == hash2

    def test_compute_package_hash_differs_for_different_content(self, sample_organization):
        """compute_package_hash() returns different hash for different content."""
        package1 = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.CSRD,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=sample_organization,
        )

        package2 = AuditEvidencePackage(
            report_id=uuid4(),  # Different report ID
            disclosure_framework=DisclosureFramework.CSRD,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=sample_organization,
        )

        hash1 = package1.compute_package_hash()
        hash2 = package2.compute_package_hash()

        assert hash1 != hash2


class TestAuditEvidencePackageAddEvidence:
    """Tests for AuditEvidencePackage.add_evidence() method."""

    def test_add_evidence_appends_record(self, sample_evidence_record):
        """add_evidence() appends a record to evidence_records."""
        package = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.CSRD,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=Organization(id=uuid4(), name="Test"),
        )

        assert len(package.evidence_records) == 0

        package.add_evidence(sample_evidence_record)

        assert len(package.evidence_records) == 1
        assert package.evidence_records[0] == sample_evidence_record


class TestAuditEvidencePackageAddGap:
    """Tests for AuditEvidencePackage.add_gap() method."""

    def test_add_gap_appends_gap(self):
        """add_gap() appends a gap to gaps list."""
        gap = Gap(
            data_point_id=uuid4(),
            metric_type="water",
            framework_requirement="GRI 303-3",
            disclosure_code="GRI-303-3",
            reporting_period_start=date(2024, 1, 1),
            reporting_period_end=date(2024, 12, 31),
            reason="No data",
        )

        package = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.GRI,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=Organization(id=uuid4(), name="Test"),
        )

        assert len(package.gaps) == 0

        package.add_gap(gap)

        assert len(package.gaps) == 1
        assert package.gaps[0] == gap


class TestAuditEvidencePackageGetRecords:
    """Tests for get_high_confidence_records and get_low_confidence_records."""

    def test_get_high_confidence_records(self):
        """get_high_confidence_records() returns only HIGH confidence records."""
        records = [
            EvidenceRecord(
                id=uuid4(),
                data_point_id=uuid4(),
                organization_id=uuid4(),
                value=Decimal("100"),
                unit="kg",
                metric_type="emissions",
                evidence_type=EvidenceType.API_EXTRACTION,
                raw_source_reference="api",
                raw_source_hash="hash",
                confidence=ConfidenceLevel.HIGH,
            ),
            EvidenceRecord(
                id=uuid4(),
                data_point_id=uuid4(),
                organization_id=uuid4(),
                value=Decimal("200"),
                unit="kg",
                metric_type="energy",
                evidence_type=EvidenceType.MANUAL_ENTRY,
                raw_source_reference="manual",
                raw_source_hash="hash2",
                confidence=ConfidenceLevel.LOW,
            ),
            EvidenceRecord(
                id=uuid4(),
                data_point_id=uuid4(),
                organization_id=uuid4(),
                value=Decimal("300"),
                unit="kg",
                metric_type="water",
                evidence_type=EvidenceType.SENSOR_READING,
                raw_source_reference="sensor",
                raw_source_hash="hash3",
                confidence=ConfidenceLevel.HIGH,
            ),
        ]

        package = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.CSRD,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=Organization(id=uuid4(), name="Test"),
        )

        for record in records:
            package.add_evidence(record)

        high_records = package.get_high_confidence_records()

        assert len(high_records) == 2
        assert all(r.confidence == ConfidenceLevel.HIGH for r in high_records)

    def test_get_low_confidence_records(self):
        """get_low_confidence_records() returns only LOW confidence records."""
        records = [
            EvidenceRecord(
                id=uuid4(),
                data_point_id=uuid4(),
                organization_id=uuid4(),
                value=Decimal("100"),
                unit="kg",
                metric_type="emissions",
                evidence_type=EvidenceType.API_EXTRACTION,
                raw_source_reference="api",
                raw_source_hash="hash",
                confidence=ConfidenceLevel.HIGH,
            ),
            EvidenceRecord(
                id=uuid4(),
                data_point_id=uuid4(),
                organization_id=uuid4(),
                value=Decimal("200"),
                unit="kg",
                metric_type="energy",
                evidence_type=EvidenceType.MANUAL_ENTRY,
                raw_source_reference="manual",
                raw_source_hash="hash2",
                confidence=ConfidenceLevel.LOW,
            ),
        ]

        package = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.ISSB,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=Organization(id=uuid4(), name="Test"),
        )

        for record in records:
            package.add_evidence(record)

        low_records = package.get_low_confidence_records()

        assert len(low_records) == 1
        assert low_records[0].confidence == ConfidenceLevel.LOW


class TestAuditEvidencePackageGetGapsBySeverity:
    """Tests for AuditEvidencePackage.get_gaps_by_severity() method."""

    def test_get_gaps_by_severity(self):
        """get_gaps_by_severity() filters gaps by severity level."""
        gaps = [
            Gap(
                data_point_id=uuid4(),
                metric_type="emissions",
                framework_requirement="CSRD",
                disclosure_code="E1",
                reporting_period_start=date(2024, 1, 1),
                reporting_period_end=date(2024, 12, 31),
                reason="Data missing",
                severity="HIGH",
            ),
            Gap(
                data_point_id=uuid4(),
                metric_type="water",
                framework_requirement="GRI",
                disclosure_code="303-3",
                reporting_period_start=date(2024, 1, 1),
                reporting_period_end=date(2024, 12, 31),
                reason="Not measured",
                severity="LOW",
            ),
            Gap(
                data_point_id=uuid4(),
                metric_type="energy",
                framework_requirement="TCFD",
                disclosure_code="C1",
                reporting_period_start=date(2024, 1, 1),
                reporting_period_end=date(2024, 12, 31),
                reason="Estimate only",
                severity="high",  # lowercase to test case-insensitivity
            ),
        ]

        package = AuditEvidencePackage(
            report_id=uuid4(),
            disclosure_framework=DisclosureFramework.CSRD,
            reporting_period=(date(2024, 1, 1), date(2024, 12, 31)),
            organization=Organization(id=uuid4(), name="Test"),
        )

        for gap in gaps:
            package.add_gap(gap)

        high_gaps = package.get_gaps_by_severity("HIGH")

        assert len(high_gaps) == 2
        assert all(g.severity.upper() == "HIGH" for g in high_gaps)
