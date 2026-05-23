"""
EvidenceRecord and LineageNode dataclasses for the ESG+SCRM Evidence Vault.

Implements cryptographic chain-of-custody for emissions and sustainability data
per CSRD, ISSB, GRI, and TCFD disclosure frameworks.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger(__name__)


class EvidenceType(Enum):
    """Source type for evidence chain records."""

    API_EXTRACTION = "api_extraction"
    MANUAL_ENTRY = "manual_entry"
    SUPPLIER_RESPONSE = "supplier_response"
    SENSOR_READING = "sensor_reading"
    CALCULATION = "calculation"


class ConfidenceLevel(Enum):
    """Confidence level for evidence quality assessment."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RetentionPolicy(Enum):
    """Data retention policy for compliance."""

    CSRD_7YR = "csrd_7yr"
    UNLIMITED = "unlimited"


class DisclosureFramework(Enum):
    """Supported sustainability disclosure frameworks."""

    CSRD = "CSRD"
    ISSB = "ISSB"
    GRI = "GRI"
    TCFD = "TCFD"


@dataclass
class EvidenceRecord:
    """
    Cryptographically verifiable evidence record for sustainability metrics.

    Tracks the chain of custody from raw source through any calculations
    to the final reported value included in disclosure reports.
    """

    id: UUID
    data_point_id: UUID
    organization_id: UUID

    # The reported value
    value: Decimal
    unit: str
    metric_type: str

    # The chain of custody
    evidence_type: EvidenceType
    raw_source_reference: str
    raw_source_hash: str

    # Calculation trail (if derived)
    calculation_inputs: list[UUID] = field(default_factory=list)
    calculation_formula: str = ""
    calculation_result: Decimal = field(default_factory=lambda: Decimal("0"))

    # Confidence
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    confidence_rationale: str = ""

    # Cryptographic integrity
    cryptographic_hash: str = ""
    previous_hash: str = ""
    chain_valid: bool = True

    # Audit metadata
    included_in_report: Optional[UUID] = None
    reported_at: Optional[datetime] = None
    reported_by: Optional[UUID] = None
    retained_until: Optional[datetime] = None

    # Retention policy
    retention_policy: RetentionPolicy = RetentionPolicy.CSRD_7YR

    def __post_init__(self) -> None:
        """Validate and compute derived fields after initialization."""
        if not isinstance(self.value, Decimal):
            self.value = Decimal(str(self.value))
        if self.cryptographic_hash and not self.previous_hash:
            logger.warning(
                "evidence_record.no_previous_hash",
                record_id=str(self.id),
                data_point_id=str(self.data_point_id),
            )
        if self.retention_policy == RetentionPolicy.CSRD_7YR and self.retained_until is None:
            self.retained_until = datetime.utcnow()

    def compute_cryptographic_hash(
        self,
        data_point_id: UUID,
        value: Decimal,
        methodology: str,
        timestamp: datetime,
    ) -> str:
        """
        Compute SHA-256 cryptographic hash for this evidence record.

        Hash input format: "{data_point_id}:{value}:{methodology}:{timestamp}"
        """
        import hashlib

        raw = f"{data_point_id}:{value}:{methodology}:{timestamp.isoformat()}"
        self.cryptographic_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return self.cryptographic_hash

    def verify_chain_record(
        self,
        stored_hash: str,
        data_point_id: UUID,
        value: Decimal,
        methodology: str,
        timestamp: datetime,
    ) -> bool:
        """
        Verify a single record's hash matches recomputation.

        Returns True if hash is valid, False if tampered.
        """
        computed = self.compute_cryptographic_hash(data_point_id, value, methodology, timestamp)
        self.chain_valid = computed == stored_hash
        return self.chain_valid

    @classmethod
    def create_genesis(
        cls,
        data_point_id: UUID,
        organization_id: UUID,
        value: Decimal,
        unit: str,
        metric_type: str,
        evidence_type: EvidenceType,
        raw_source_reference: str,
        raw_source_hash: str,
        methodology: str = "",
    ) -> "EvidenceRecord":
        """
        Create the first evidence record in a chain (no previous hash).

        Used when establishing a new metric data point with no prior history.
        """
        now = datetime.utcnow()
        record_id = uuid4()
        record = cls(
            id=record_id,
            data_point_id=data_point_id,
            organization_id=organization_id,
            value=value,
            unit=unit,
            metric_type=metric_type,
            evidence_type=evidence_type,
            raw_source_reference=raw_source_reference,
            raw_source_hash=raw_source_hash,
            previous_hash="GENESIS",
            reported_at=now,
        )
        record.compute_cryptographic_hash(
            data_point_id=data_point_id,
            value=value,
            methodology=methodology,
            timestamp=now,
        )
        return record

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage and API responses."""
        return {
            "id": str(self.id),
            "data_point_id": str(self.data_point_id),
            "organization_id": str(self.organization_id),
            "value": str(self.value),
            "unit": self.unit,
            "metric_type": self.metric_type,
            "evidence_type": self.evidence_type.value,
            "raw_source_reference": self.raw_source_reference,
            "raw_source_hash": self.raw_source_hash,
            "calculation_inputs": [str(uid) for uid in self.calculation_inputs],
            "calculation_formula": self.calculation_formula,
            "calculation_result": str(self.calculation_result),
            "confidence": self.confidence.value,
            "confidence_rationale": self.confidence_rationale,
            "cryptographic_hash": self.cryptographic_hash,
            "previous_hash": self.previous_hash,
            "chain_valid": self.chain_valid,
            "included_in_report": (
                str(self.included_in_report) if self.included_in_report else None
            ),
            "reported_at": (self.reported_at.isoformat() if self.reported_at else None),
            "reported_by": str(self.reported_by) if self.reported_by else None,
            "retained_until": (self.retained_until.isoformat() if self.retained_until else None),
            "retention_policy": self.retention_policy.value,
        }


@dataclass
class LineageNode:
    """
    Recursive ancestry tracking for derived calculations.

    Enables full audit trail from final reported value back to
    raw sensor readings, API responses, or manual entries.
    """

    id: UUID
    metric_type: str
    value: Decimal
    unit: str
    source: str
    extraction_timestamp: datetime
    confidence: ConfidenceLevel
    children: list["LineageNode"] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Ensure value is Decimal after initialization."""
        if not isinstance(self.value, Decimal):
            self.value = Decimal(str(self.value))

    def add_child(self, child: "LineageNode") -> None:
        """Add a child node to this lineage node."""
        self.children.append(child)

    def get_ancestors(self) -> list["LineageNode"]:
        """
        Get all ancestor nodes in depth-first order.

        Returns list of all nodes from this node to the root,
        excluding this node.
        """
        ancestors: list[LineageNode] = []
        for child in self.children:
            ancestors.append(child)
            ancestors.extend(child.get_ancestors())
        return ancestors

    def get_root(self) -> "LineageNode":
        """Get the root node of this lineage tree."""
        if not self.children:
            return self
        return self.children[0].get_root()

    def compute_aggregate_confidence(self) -> ConfidenceLevel:
        """
        Compute aggregate confidence using MIN rule.

        When DataPoints combine, the aggregate confidence is the
        minimum of all input confidences.
        """
        all_confidences = [self.confidence]
        for child in self.children:
            all_confidences.append(child.compute_aggregate_confidence())
        confidence_order = [
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
        ]
        min_confidence = min(all_confidences, key=lambda c: confidence_order.index(c))
        return min_confidence

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage and API responses."""
        return {
            "id": str(self.id),
            "metric_type": self.metric_type,
            "value": str(self.value),
            "unit": self.unit,
            "source": self.source,
            "extraction_timestamp": self.extraction_timestamp.isoformat(),
            "confidence": self.confidence.value,
            "children": [child.to_dict() for child in self.children],
        }

    @classmethod
    def from_evidence_record(
        cls,
        record: EvidenceRecord,
        source: str = "",
    ) -> "LineageNode":
        """
        Create a LineageNode from an EvidenceRecord.

        Args:
            record: The evidence record to convert
            source: Human-readable description of the source
        """
        return cls(
            id=record.id,
            metric_type=record.metric_type,
            value=record.value,
            unit=record.unit,
            source=source or record.raw_source_reference,
            extraction_timestamp=record.reported_at or datetime.utcnow(),
            confidence=record.confidence,
            children=[],
        )


@dataclass
class ChainProof:
    """Verifiable chain proof linking multiple evidence records."""

    records: list[EvidenceRecord]
    chain_valid: bool = True
    verification_date: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Set verification date if not provided."""
        if self.verification_date is None:
            self.verification_date = datetime.utcnow()

    def verify(self) -> bool:
        """
        Verify the entire chain of records.

        Checks that each record's previous_hash matches the
        cryptographic hash of the preceding record.
        """
        if not self.records:
            return True

        self.chain_valid = True
        for i, record in enumerate(self.records):
            if i == 0:
                if record.previous_hash != "GENESIS":
                    logger.error(
                        "chain_proof.genesis_invalid",
                        record_id=str(record.id),
                        previous_hash=record.previous_hash,
                    )
                    self.chain_valid = False
                    return False
            else:
                prev_record = self.records[i - 1]
                if record.previous_hash != prev_record.cryptographic_hash:
                    logger.error(
                        "chain_proof.hash_mismatch",
                        record_id=str(record.id),
                        expected_previous_hash=prev_record.cryptographic_hash,
                        actual_previous_hash=record.previous_hash,
                    )
                    self.chain_valid = False
                    return False

            if not record.chain_valid:
                logger.warning(
                    "chain_proof.record_invalid",
                    record_id=str(record.id),
                )
                self.chain_valid = False
                return False

        logger.info(
            "chain_proof.verified",
            record_count=len(self.records),
            chain_valid=self.chain_valid,
        )
        return self.chain_valid
