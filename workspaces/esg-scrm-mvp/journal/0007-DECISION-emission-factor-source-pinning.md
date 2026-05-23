# DECISION: Every emission factor pinned to specific source document + version + table

## What

VC raised AI quality assurance concern: if emission factors are wrong, Scope 3 submissions are wrong and liability is ours. Answer: every factor is pinned to a specific source document, year, and table — not just "GHG Protocol."

## Detail

The Evidence Vault already tags every DataPoint with emission_factor_source. The gap: "GHG Protocol" is not auditable. "GHG Protocol 2022, Table 7.3, Equation 7.2" is auditable.

Per VC: "The liability concern goes away if every AI-generated number has a human-verifiable evidence chain behind it. What you need is: every factor is tagged with its source document and version."

## Decision

EmissionFactor table fields:

- source: string (e.g., "GHG Protocol", "DEFRA", "IEA")
- year: int (e.g., 2022, 2023, 2024)
- table_or_equation: string (e.g., "Table 7.3", "Equation 7.2", "Section 6.4.1")

EvidenceRecord.methodology field shows the exact factor used with version info.

## Source

VC red team Round 4 — AI quality assurance question

## Action

Update specs/05-data-model.md §EmissionFactor to include table_or_equation field.
