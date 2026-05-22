"""
Real SHA-256 hash chain computation for evidence vault.
Replaces theatrical hash strings with actual cryptographic verification.
"""

import hashlib
import hmac
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

import structlog

from src.evidence.evidence_record import ChainProof, EvidenceRecord

logger = structlog.get_logger(__name__)


def compute_hash(
    cluster: str,
    value: float,
    timestamp: str,
    prev_hash: Optional[str] = None,
) -> str:
    """
    Compute SHA-256 hash for a metric data point.

    Hash input format: "{cluster}:{value}:{timestamp}:{prev_hash}"
    If prev_hash is None, it's the genesis block (no upstream).
    """
    if prev_hash is None:
        prev_hash = "GENESIS"

    raw = f"{cluster}:{value}:{timestamp}:{prev_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_chain_record(
    cluster: str,
    value: float,
    timestamp: str,
    stored_hash: str,
    prev_hash: Optional[str] = None,
) -> bool:
    """
    Verify a single record's hash matches recomputation.
    Returns True if hash is valid, False if tampered.
    """
    computed = compute_hash(cluster, value, timestamp, prev_hash)
    return hmac.compare_digest(computed, stored_hash)


def build_chain_proof(
    records: list[dict],
) -> list[dict]:
    """
    Build a verifiable chain from a list of metric records.

    Each record should have: cluster, value, timestamp
    Returns records with computed hash and previous hash linked.
    """
    chain = []
    prev_hash = None

    for record in records:
        current_hash = compute_hash(
            record["cluster"],
            record["value"],
            record["timestamp"],
            prev_hash,
        )
        chain.append(
            {
                **record,
                "hash": current_hash,
                "previous_hash": prev_hash,
                "chain_valid": True,
            }
        )
        prev_hash = current_hash

    return chain


def compute_cryptographic_hash(
    data_point_id: UUID,
    value: Decimal,
    methodology: str,
    timestamp: datetime,
) -> str:
    """
    Compute SHA-256 cryptographic hash for an evidence record.

    Hash input format: "{data_point_id}:{value}:{methodology}:{timestamp}"

    Args:
        data_point_id: UUID of the data point
        value: Decimal value of the metric
        methodology: Method used to derive the value
        timestamp: datetime of the computation

    Returns:
        SHA-256 hash as a hexadecimal string
    """
    value_str = str(value)
    timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
    raw = f"{data_point_id}:{value_str}:{methodology}:{timestamp_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_chain_record_v2(
    record: EvidenceRecord,
    previous_hash: str,
) -> bool:
    """
    Verify a single evidence record's hash matches recomputation.

    Uses the evidence record's cryptographic_hash field to verify
    integrity against the stored hash.

    Args:
        record: EvidenceRecord to verify
        previous_hash: Hash of the previous record in the chain

    Returns:
        True if hash is valid, False if tampered
    """
    computed = compute_cryptographic_hash(
        data_point_id=record.data_point_id,
        value=record.value,
        methodology=record.calculation_formula or "",
        timestamp=record.reported_at or datetime.utcnow(),
    )
    is_valid = hmac.compare_digest(computed, record.cryptographic_hash)
    if not is_valid:
        logger.warning(
            "hash_chain.record_tampered",
            record_id=str(record.id),
            data_point_id=str(record.data_point_id),
            expected_hash=computed[:16] + "...",
            stored_hash=record.cryptographic_hash[:16] + "...",
        )
    return is_valid


def build_chain_proof_v2(
    evidence_records: list[EvidenceRecord],
) -> ChainProof:
    """
    Build a verifiable chain proof from a list of evidence records.

    Records are sorted by timestamp and each record's previous_hash
    is verified against the prior record's cryptographic hash.

    Args:
        evidence_records: List of EvidenceRecord objects

    Returns:
        ChainProof with verification results
    """
    if not evidence_records:
        return ChainProof(records=[], chain_valid=True)

    sorted_records = sorted(
        evidence_records,
        key=lambda r: r.reported_at or datetime.min,
    )

    for i, record in enumerate(sorted_records):
        if i == 0:
            if record.previous_hash != "GENESIS":
                logger.error(
                    "hash_chain.genesis_invalid",
                    record_id=str(record.id),
                    expected="GENESIS",
                    actual=record.previous_hash,
                )
                return ChainProof(records=sorted_records, chain_valid=False)
        else:
            prev_record = sorted_records[i - 1]
            if not hmac.compare_digest(record.previous_hash, prev_record.cryptographic_hash):
                logger.error(
                    "hash_chain.hash_mismatch",
                    record_id=str(record.id),
                    previous_record_id=str(prev_record.id),
                    expected_hash=prev_record.cryptographic_hash[:16] + "...",
                    actual_previous_hash=record.previous_hash[:16] + "...",
                )
                return ChainProof(records=sorted_records, chain_valid=False)

        if not verify_chain_record_v2(record, record.previous_hash):
            logger.error(
                "hash_chain.record_invalid",
                record_id=str(record.id),
            )
            return ChainProof(records=sorted_records, chain_valid=False)

    logger.info(
        "hash_chain.proof_built",
        record_count=len(sorted_records),
        chain_valid=True,
    )
    return ChainProof(records=sorted_records, chain_valid=True)
