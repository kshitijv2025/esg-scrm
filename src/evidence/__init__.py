"""
Evidence Vault - Cryptographic chain-of-custody for ESG+SCRM disclosures.

Supports CSRD, ISSB, GRI, and TCFD disclosure frameworks.
"""

from src.evidence.audit_package import (
    AuditEvidencePackage,
    Gap,
    Organization,
)
from src.evidence.evidence_record import (
    ChainProof,
    ConfidenceLevel,
    DisclosureFramework,
    EvidenceRecord,
    EvidenceType,
    LineageNode,
    RetentionPolicy,
)
from src.evidence.confidence import (
    aggregate_confidence,
    determine_confidence,
    get_confidence_rationale,
)
from src.evidence.hash_chain import (
    build_chain_proof,
    build_chain_proof_v2,
    compute_cryptographic_hash,
    compute_hash,
    verify_chain_record,
    verify_chain_record_v2,
)

__all__ = [
    # Evidence record and lineage
    "EvidenceRecord",
    "LineageNode",
    "ChainProof",
    # Audit package
    "AuditEvidencePackage",
    "Gap",
    "Organization",
    # Enums
    "ConfidenceLevel",
    "DisclosureFramework",
    "EvidenceType",
    "RetentionPolicy",
    # Confidence rules
    "determine_confidence",
    "aggregate_confidence",
    "get_confidence_rationale",
    # Hash chain
    "compute_hash",
    "verify_chain_record",
    "build_chain_proof",
    "compute_cryptographic_hash",
    "verify_chain_record_v2",
    "build_chain_proof_v2",
]
