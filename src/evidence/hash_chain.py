"""
Real SHA-256 hash chain computation for evidence vault.
Replaces theatrical hash strings with actual cryptographic verification.
"""
import hashlib
from datetime import datetime
from typing import Optional


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
    return computed == stored_hash


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
        chain.append({
            **record,
            "hash": current_hash,
            "previous_hash": prev_hash,
            "chain_valid": True,
        })
        prev_hash = current_hash

    return chain
