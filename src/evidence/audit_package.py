"""
AuditEvidencePackage for ESG+SCRM disclosure reporting.

Packages evidence records with cryptographic proof and gap analysis
for CSRD, ISSB, GRI, and TCFD framework disclosures.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

import structlog

from src.evidence.evidence_record import (
    ChainProof,
    ConfidenceLevel,
    DisclosureFramework,
    EvidenceRecord,
)

logger = structlog.get_logger(__name__)


class OrganizationType(Enum):
    """Organization type for ESG reporting."""

    MID_MARKET = "mid_market"
    ENTERPRISE_DIVISION = "enterprise_division"


@dataclass
class Gap:
    """
    Represents a data gap in evidence coverage.

    Documents where required data points could not be collected
    or verified for a disclosure report.
    """

    data_point_id: UUID
    metric_type: str
    framework_requirement: str
    disclosure_code: str
    reporting_period_start: date
    reporting_period_end: date
    reason: str
    severity: str = "MEDIUM"
    estimated_value: Optional[Decimal] = None
    estimated_unit: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "data_point_id": str(self.data_point_id),
            "metric_type": self.metric_type,
            "framework_requirement": self.framework_requirement,
            "disclosure_code": self.disclosure_code,
            "reporting_period_start": self.reporting_period_start.isoformat(),
            "reporting_period_end": self.reporting_period_end.isoformat(),
            "reason": self.reason,
            "severity": self.severity,
            "estimated_value": (str(self.estimated_value) if self.estimated_value else None),
            "estimated_unit": self.estimated_unit,
        }


@dataclass
class Organization:
    """Organization metadata for audit packages."""

    id: UUID
    name: str
    industry: str = ""
    country: str = ""
    employee_count: int = 0
    type: Optional[OrganizationType] = None
    primary_buyer: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "industry": self.industry,
            "country": self.country,
            "employee_count": self.employee_count,
            "type": self.type.value if self.type else None,
            "primary_buyer": self.primary_buyer,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IntegrationStatus(Enum):
    """Integration connection status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class IntegrationType(Enum):
    """Integration type for ERP/IoT connectivity."""

    SAP_B1 = "sap_b1"
    XERO = "xero"
    QUICKBOOKS = "quickbooks"
    MQTT = "mqtt"
    MANUAL = "manual"


@dataclass
class Integration:
    """Integration entity for ERP and IoT connectivity."""

    id: UUID
    organization_id: UUID
    type: IntegrationType
    status: IntegrationStatus
    last_sync_at: Optional[datetime] = None
    credentials_encrypted: Optional[str] = None
    config: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "type": self.type.value,
            "status": self.status.value,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "credentials_encrypted": self.credentials_encrypted,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class AuditEvidencePackage:
    """
    Complete audit package for a sustainability disclosure report.

    Contains all evidence records, chain verification, confidence summary,
    and identified gaps for a specific framework and reporting period.
    """

    report_id: UUID
    disclosure_framework: DisclosureFramework
    reporting_period: tuple[date, date]
    organization: Organization

    # All evidence for this report
    evidence_records: list[EvidenceRecord] = field(default_factory=list)

    # Summary statistics
    confidence_summary: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Gaps (data not available)
    gaps: list[Gap] = field(default_factory=list)

    # Chain verification result
    chain_verified: bool = False
    chain_verification_date: Optional[datetime] = None

    # Metadata
    generated_at: Optional[datetime] = None
    generated_by: Optional[UUID] = None
    package_hash: str = ""

    def __post_init__(self) -> None:
        """Initialize derived fields after initialization."""
        if self.generated_at is None:
            self.generated_at = datetime.utcnow()
        if self.chain_verification_date is None and self.chain_verified:
            self.chain_verification_date = datetime.utcnow()

    def add_evidence(self, record: EvidenceRecord) -> None:
        """
        Add an evidence record to this package.

        Args:
            record: Evidence record to add
        """
        self.evidence_records.append(record)
        logger.debug(
            "audit_package.evidence_added",
            report_id=str(self.report_id),
            record_id=str(record.id),
            metric_type=record.metric_type,
        )

    def add_gap(self, gap: Gap) -> None:
        """
        Add a data gap to this package.

        Args:
            gap: Gap record to add
        """
        self.gaps.append(gap)
        logger.info(
            "audit_package.gap_added",
            report_id=str(self.report_id),
            metric_type=gap.metric_type,
            severity=gap.severity,
        )

    def verify_chain(self) -> bool:
        """
        Verify the cryptographic chain of all evidence records.

        Returns:
            True if chain is valid, False otherwise
        """
        if not self.evidence_records:
            logger.warning(
                "audit_package.no_records_to_verify",
                report_id=str(self.report_id),
            )
            self.chain_verified = False
            return False

        sorted_records = sorted(
            self.evidence_records,
            key=lambda r: r.reported_at or datetime.min,
        )
        proof = ChainProof(records=sorted_records)
        self.chain_verified = proof.verify()
        self.chain_verification_date = datetime.utcnow()

        logger.info(
            "audit_package.chain_verified",
            report_id=str(self.report_id),
            record_count=len(self.evidence_records),
            chain_valid=self.chain_verified,
        )
        return self.chain_verified

    def compute_confidence_summary(self) -> dict[str, dict[str, Any]]:
        """
        Compute summary statistics of confidence levels.

        Returns:
            Dictionary mapping ConfidenceLevel to count and percentage
        """
        if not self.evidence_records:
            self.confidence_summary = {}
            return self.confidence_summary

        summary: dict[str, dict[str, Any]] = {}
        total = len(self.evidence_records)

        for level in ConfidenceLevel:
            count = sum(1 for r in self.evidence_records if r.confidence == level)
            percentage = (count / total * 100) if total > 0 else 0.0
            summary[level.value] = {
                "count": count,
                "percentage": round(percentage, 2),
                "records": [
                    {"id": str(r.id), "metric_type": r.metric_type}
                    for r in self.evidence_records
                    if r.confidence == level
                ],
            }

        self.confidence_summary = summary
        logger.debug(
            "audit_package.confidence_computed",
            report_id=str(self.report_id),
            total_records=total,
            high_count=summary.get("HIGH", {}).get("count", 0),
            medium_count=summary.get("MEDIUM", {}).get("count", 0),
            low_count=summary.get("LOW", {}).get("count", 0),
        )
        return self.confidence_summary

    def compute_package_hash(self) -> str:
        """
        Compute SHA-256 hash of the entire package.

        Hash includes all evidence records' cryptographic hashes,
        report metadata, and gap information.
        """
        import hashlib

        hash_inputs = [
            str(self.report_id),
            self.disclosure_framework.value,
            self.reporting_period[0].isoformat(),
            self.reporting_period[1].isoformat(),
            str(self.organization.id),
        ]

        for record in sorted(self.evidence_records, key=lambda r: str(r.id)):
            hash_inputs.append(record.cryptographic_hash)

        for gap in sorted(self.gaps, key=lambda g: str(g.data_point_id)):
            hash_inputs.append(str(gap.data_point_id))
            hash_inputs.append(gap.reason)

        raw_hash = "|".join(hash_inputs)
        self.package_hash = hashlib.sha256(raw_hash.encode("utf-8")).hexdigest()

        logger.debug(
            "audit_package.hash_computed",
            report_id=str(self.report_id),
            hash=self.package_hash[:16] + "...",
        )
        return self.package_hash

    def get_high_confidence_records(
        self,
    ) -> list[EvidenceRecord]:
        """
        Get all evidence records with HIGH confidence.

        Returns:
            List of HIGH confidence evidence records
        """
        return [r for r in self.evidence_records if r.confidence == ConfidenceLevel.HIGH]

    def get_low_confidence_records(self) -> list[EvidenceRecord]:
        """
        Get all evidence records with LOW confidence.

        Returns:
            List of LOW confidence evidence records
        """
        return [r for r in self.evidence_records if r.confidence == ConfidenceLevel.LOW]

    def get_gaps_by_severity(self, severity: str) -> list[Gap]:
        """
        Get all gaps matching a specific severity level.

        Args:
            severity: Severity level to filter by

        Returns:
            List of gaps with the specified severity
        """
        return [g for g in self.gaps if g.severity.upper() == severity.upper()]

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the complete audit package to a dictionary.

        Returns:
            Dictionary representation of the audit package
        """
        return {
            "report_id": str(self.report_id),
            "disclosure_framework": self.disclosure_framework.value,
            "reporting_period": {
                "start": self.reporting_period[0].isoformat(),
                "end": self.reporting_period[1].isoformat(),
            },
            "organization": self.organization.to_dict(),
            "evidence_records": [r.to_dict() for r in self.evidence_records],
            "confidence_summary": self.confidence_summary,
            "gaps": [g.to_dict() for g in self.gaps],
            "chain_verified": self.chain_verified,
            "chain_verification_date": (
                self.chain_verification_date.isoformat() if self.chain_verification_date else None
            ),
            "generated_at": (self.generated_at.isoformat() if self.generated_at else None),
            "generated_by": str(self.generated_by) if self.generated_by else None,
            "package_hash": self.package_hash,
        }
