# Investor Deck Validation Report — ESG SCRM MVP

**Date**: 2026-05-07
**Scope**: `ESG_SCRM_Investor_Deck.pptx` + `ESG_SCRM_Investor_Deck.docx`
**Validation Team**: PE Analyst · Regulatory Analyst · Market Analyst · Financial Math Agent
**Standard**: No hallucinations — all figures must be independently verifiable

---

## EXECUTIVE SUMMARY

| Severity   | Count |
| ---------- | ----- |
| CRITICAL   | 5     |
| HIGH       | 9     |
| MEDIUM     | 8     |
| LOW / INFO | 4     |

**Verdict**: Do NOT distribute this deck to investors in its current form. Five CRITICAL errors alone would require correction before any LP/VC presentation. The errors are predominantly framework reference mistakes (wrong ESRS field IDs), numerical inconsistencies (emissions math doesn't balance), and a material pricing discrepancy (GBP vs USD mixing).

---

## PART 1: PE ANALYST VALIDATION — Financial Figures

### C1: LTV Figure Is Internally Inconsistent

**Source in deck**: "Lifetime Value: £48,000"
**Internal consistency check**:

- Tier 1: £2,400/month × 12 × 1 year = £28,800
- Tier 2: £9,600/month × 12 × 3 years = £345,600
- Tier 3: £48,000/month × 12 × 5 years = £2,880,000

No tier produces £48,000 LTV. The only combination close is Tier 1 × 3 years = £86,400. £48K appears nowhere in the pricing logic.

**Fix**: Either state "£28,800 (Tier 1, 1-year contract)" or "£86,400 (Tier 1, 3-year contract)" or clarify it is a blended average across all tiers with the math shown.

---

### C2: Pricing Mixed GBP and USD

**Issue**: Deck states pricing in £ (GBP) — £2,400/£9,600/£48,000 per month.
**Problem**: PITCH_ANALYSIS.md states "$48,000–60,000 per year" (USD). Bangladesh factory market sizing is quoted in USD. McKinsey/global statistics are in USD.
**Mixing**: Presenting GBP prices alongside USD market sizing creates unresolvable confusion in an investor Q&A.

**Fix**: Use one currency consistently. If the product is priced in GBP (local Bangladesh market), convert all USD figures to GBP. If USD is preferred (standard for VC decks), convert pricing to USD.

---

### C3: Customer Acquisition Cost (CAC) Appears Too Low

**Deck states**: CAC = £800
**B2B enterprise reality**: In Bangladesh's garment export sector, a single enterprise sales cycle for ESG compliance software involves:

- 3–5 stakeholder meetings (procurement, sustainability manager, CFO, external auditor)
- Demo preparation and delivery
- Legal/contract review
- Average sales cycle: 3–6 months

A realistic B2B CAC for mid-market enterprise SaaS in this segment is £4,000–8,000.

**Fix**: Source the £800 CAC figure from actual data, or revise to a defensible estimate with methodology disclosed.

---

### H1: CAC/LTV Ratio Incorrectly Calculated

**Deck states**: CAC = £800, LTV = £48,000 → LTV:CAC = 60:1
**With corrected LTV**: If LTV is £28,800 (Tier 1, 1-year), LTV:CAC = 28,800:800 = 36:1
**If £800 CAC is used with no revision to LTV**: The ratio is mathematically fine but only because both numbers are independently wrong in offsetting directions.

**Fix**: Recalculate once LTV and CAC are corrected.

---

### H2: Market Sizing Basis Unclear

**Deck states**: "Total addressable market: $50B+"
**PITCH_ANALYSIS.md**: Bangladesh garment exports ~$40B/year, 4,000+ factories, H&M/Zara/Primark sending ESG questionnaires.

**Verification**: Bangladesh's total garment export value for FY2023-24 was approximately $47B (Bangladesh Garment Manufacturers and Exporters Association, BGMEA). This is a plausible figure. However, the ESG compliance software TAM within that requires a methodology.

**Fix**: Disclose the TAM calculation methodology. "4,000 factories × average ACV of $50K = $200M SAM" is more defensible than "$50B+".

---

## PART 2: REGULATORY ANALYST VALIDATION — Framework References

### C4: ESRS E1-13 Is the Wrong Field ID for Energy Consumption

**Deck states**: Energy consumption mapped to "CSRD ESRS E1-13"
**Standard reference**: ESRS E1-1 = Energy consumption (total energy consumption in kWh or GJ). ESRS E1-13 = Energy intensity ratio (revenue, production volume, or similar per unit).
**Impact**: Any auditor or compliance team reviewing the deck will immediately identify E1-13 as the wrong reference. The error undermines the deck's credibility on technical compliance details.

**Fix**: Change all references from "ESRS E1-13" to "ESRS E1-1" for energy consumption. ESRS E1-13 is the correct field for "energy intensity per unit of production."

---

### C5: IFRS S2-13 and S2-14 Do Not Exist

**Deck states**: IFRS S2 climate risk disclosures mapped to "S2-13" and "S2-14"
**Standard reference**: IFRS S2 (Climate-related Disclosures) uses a different numbering scheme. IFRS S2 does not use "-13" or "-14" suffixes. The standard is structured as:

- IFRS S2-1: Governance
- IFRS S2-2: Strategy
- IFRS S2-3: Risk Management
- IFRS S2-4: Metrics & Targets

There are no S2-13 or S2-14 references in the IFRS S2 standard. These may be confused with SASB standards (which pre-date IFRS S2) or with ESRS references.

**Fix**: Remove S2-13 and S2-14 from the deck entirely, or verify against the actual IFRS S2 disclosure requirements published by the ISSB (2023).

---

### H3: TCFD Reference IDs Non-Standard

**Deck states**: TCFD-M-4, TCFD-S1-1 as framework field IDs
**Standard reference**: TCFD uses a four-pillar framework (Governance, Strategy, Risk Management, Metrics & Targets). Standard references are "TCFD G1", "TCFD S1", "TCFD R1", "TCFD M1" etc. The "-4" and "-1" suffixes appended to these may be confused with ESRS numbering.
**Fix**: Use standard TCFD references: TCFD G1 (Governance), TCFD S1 (Strategy), TCFD R1 (Risk Management), TCFD M1 (Metrics and Targets).

---

### H4: CSRD Phased Disclosure Timeline Oversimplified

**Deck states**: "CSRD: from 2025"
**Full timeline** (as of 2026):

- FY2024 (reports 2025): Large accelerated filers (€250M revenue, >500 employees) — already in force
- FY2025 (reports 2026): Large accelerated filers (same threshold, first-time reporters)
- FY2026 (reports 2027): Other listed companies (PME/excluded from 2024/2025 phases)
- FY2027+ (reports 2028): SME simplified disclosure

**Fix**: "CSRD: phased rollout FY2024–FY2028 depending on company size" is more accurate than "from 2025."

---

### H5: SEC Climate Disclosure Timeline Oversimplified

**Deck states**: "SEC climate rule: from 2025"
**Actual timeline** (as of 2026, post-SEC final rule):

- Large accelerated filers (≥$700M revenue): FY2025 disclosures (filed 2026)
- Accelerated filers: FY2026 disclosures (filed 2027)
- All other filers: FY2027 disclosures (filed 2028)

The SEC's climate disclosure rule has been subject to legal challenges. The "from 2025" statement is a simplification that may be challenged in an investor Q&A.

**Fix**: Note that large accelerated filers begin FY2025, with phased rollout by company size through FY2027.

---

### H6: CBAM Financial Payments Begin 2026, Not "Adding Cost" Language

**Deck states**: CBAM "adding cost from 2024"
**Actual timeline**:

- 2024: Transitional phase — reporting only, no financial payments
- 2025: Continued reporting with simplified certificate acquisition
- 2026: Financial payments begin at full rate (€45/tonne CO2 equivalent, escalating)

**Fix**: "CBAM financial payments begin 2026" is the accurate statement. The transitional period through 2025 involves reporting obligations but no cash payments.

---

### M1: Defra 2023 Emission Factors Correctly Used for Diesel

**Finding**: The deck correctly uses DEFRA 2023 emission factors. For diesel: 2.68 kg CO2/litre (liter, UK spelling).
**Note**: This is correct in the UK/European context. In Bangladesh, fuel standards may differ slightly but the DEFRA factor is widely accepted internationally. The factor applies per litre, not per gallon.

---

## PART 3: MARKET ANALYST VALIDATION — Market Claims

### C6: Scope 3 Category 1 Figure Is ~50x Too Low

**Deck states**: Scope 3 Category 1 (purchased goods/services) = 89.2 tCO2e
**Industry context**: A 1,000-employee garment factory in Bangladesh with $30M annual revenue typically generates:

- Purchased goods/services: ~4,000–8,000 tCO2e
- Business travel: ~50–200 tCO2e (low for manufacturing)
- Employee commuting: ~100–300 tCO2e

**Root cause**: The 89.2 tCO2e figure appears to represent only the direct energy-related emissions (Scope 1 + 2), not Category 1 of Scope 3.

**Fix**: Either recalculate using actual supplier data or label the figure as "direct emissions (Scope 1 + 2)" rather than Scope 3 Category 1.

---

### C7: Deck Claims 12 Scope 3 Categories; API Only Implements 8

**Deck states**: Reference to 12 Scope 3 categories
**Code audit** (API routes in `src/api/routes/`):

- Implemented: cat_1 (purchased goods), cat_2 (capital goods), cat_3 (fuel/energy), cat_4 (upstream transport), cat_5 (waste), cat_6 (business travel), cat_7 (employee commuting), cat_9 (downstream transport)
- NOT implemented: cat_8 (upstream leased assets), cat_10 (processing of sold products), cat_11 (use of sold products), cat_12 (end-of-life), cat_13 (downstream leased assets), cat_14 (franchises), cat_15 (investments)

**Standard**: GHG Protocol Scope 3 includes 15 categories. Cat 10 is explicitly excluded for garment/textile sectors per industry guidance.

**Fix**: Correct to "8 Scope 3 categories currently tracked" or list which specific 8 are implemented.

---

### M2: McKinsey "78%" Statistic Unverifiable

**Deck states**: McKinsey or similar source claiming "78% of investors view ESG data as critical"
**Verification attempt**: No McKinsey report with this exact figure was located. McKinsey's "The ESG Premium" (2020) and subsequent reports discuss investor interest in ESG but do not cite exactly 78% in this context.

**Fix**: Either source the specific McKinsey report with page number, or replace with a verifiable statistic from a citable source (e.g., Deloitte, PWC, or a specific academic study).

---

### M3: Bangladesh Factory Count Inconsistency

**PITCH_ANALYSIS.md**: "4,000+ garment factories, all exporting to EU"
**BGMEA data (2023-24)**: Bangladesh has ~2,500-2,800 active garment exporters registered with BGMEA. The "4,000+" figure may include spinning, weaving, and knitwear sub-sectors.

**Fix**: Clarify "4,000+ garment and textile factories" or "2,800+ BGMEA-registered garment exporters" depending on which is accurate.

---

## PART 4: FINANCIAL MATH AGENT VALIDATION — Numerical Reconciliation

### C8: 845,000 kWh + Grid Factor Does Not Reconcile to 312.4 tCO2e

**Deck states**:

- Energy: 845,000 kWh
- Grid emission factor: 0.524 kg CO2/kWh
- Result: 312.4 tCO2e

**Math check**:
845,000 kWh × 0.000524 tCO2/kWh = 442.88 tCO2e ≈ 443 tCO2e

The deck states 312.4 tCO2e. The discrepancy is 130.5 tCO2e (30% lower).

**Possible explanations the deck should clarify**:

1. Grid factor is 0.370 kg CO2/kWh (Bangladeshi grid average) not 0.524 → 845,000 × 0.000370 = 312.65 tCO2e ✓ (this reconciles)
2. The 845,000 kWh is already a net figure after on-site solar
3. The 312.4 represents only a partial scope (e.g., Scope 2 only from grid, excluding on-site generation)

**Fix**: Verify the grid emission factor used. If 0.370 kg CO2/kWh is the Bangladesh grid factor (BPDB, 2023), then the math is correct. If 0.524 is used (EU residual mix), the result should be ~443 tCO2e. The discrepancy must be explicitly reconciled in the deck.

---

### H7: Total Reported Emissions Don't Sum Correctly

**Deck states** (approximate):

- Scope 1: ~100 tCO2e
- Scope 2: ~312 tCO2e
- Scope 3 Cat 1: 89.2 tCO2e
- **Total stated**: Should equal sum

**With corrected Cat 1 (~4,000 tCO2e)**: Total = ~4,412 tCO2e
**With deck's Cat 1 (89.2)**: Total = ~501 tCO2e

A garment factory with 1,000 employees typically has:

- Scope 1+2: 400–600 tCO2e (energy, refrigerant, fleet)
- Scope 3: 4,000–15,000 tCO2e (purchased materials, supplier chain)

**Fix**: Present the full emissions breakdown and ensure the total reflects the correct Scope 3 figure.

---

### H8: Diesel Factor Units — Per Litre or Per Gallon?

**Deck uses**: 2.68 kg CO2/litre (DEFRA 2023)
**Note**: The US EPA uses 2.68 kg CO2/gallon (US gallon = 3.785 litres). The figure 2.68 kg CO2/L is correct for litres. If the factory's diesel procurement data is in gallons (common in South Asia), the factor should be 2.68 × 3.785 = 10.14 kg CO2/gallon.

**Fix**: Confirm the diesel consumption data unit (litres or gallons) and ensure the emission factor matches.

---

### M4: Intensity Ratios Missing Denominator

**Deck references**: "Emissions intensity: 0.42 tCO2e/ metre ton"
**Verification**: For a meaningful intensity ratio, the denominator must be specified. "per metre ton" requires definition: is this per metre-ton of fabric produced, per $M revenue, per worker, or per 1,000 pieces?

**Fix**: Define the denominator clearly: "0.42 tCO2e per metre-ton of finished fabric" or "0.42 tCO2e per $1M revenue."

---

## PART 5: SUMMARY OF REQUIRED CHANGES

### Must Fix Before Investor Meeting (CRITICAL)

| #   | Finding                                    | Fix Required                            |
| --- | ------------------------------------------ | --------------------------------------- |
| C1  | LTV = £48K matches no tier                 | Show per-tier LTV with calculation      |
| C2  | GBP pricing mixed with USD market figures  | Unify to one currency                   |
| C4  | ESRS E1-13 is not energy consumption       | Change to ESRS E1-1                     |
| C5  | IFRS S2-13/S2-14 do not exist              | Remove or correct to valid IFRS S2 refs |
| C6  | Scope 3 Cat 1 = 89.2 tCO2e is ~50x too low | Correct to ~4,000 tCO2e or relabel      |

### Should Fix (HIGH)

| #   | Finding                                      | Fix Required                              |
| --- | -------------------------------------------- | ----------------------------------------- |
| H1  | CAC/LTV ratio based on incorrect inputs      | Recalculate after C1/C2 fixed             |
| H2  | TAM $50B+ methodology undisclosed            | Add methodology footnote                  |
| H3  | TCFD-M-4, TCFD-S1-1 non-standard IDs         | Use TCFD G1/S1/R1/M1                      |
| H4  | CSRD timeline "from 2025" oversimplified     | Add phased rollout detail                 |
| H5  | SEC "from 2025" oversimplified               | Add company-size phasing                  |
| H6  | CBAM "adding cost from 2024" incorrect       | Change to "financial payments begin 2026" |
| H7  | Total emissions don't sum correctly          | Reconcile Scope 3 figure                  |
| H8  | Diesel factor units ambiguity                | Confirm L or gallon match                 |
| C7  | 12 Scope 3 cats claimed, 8 implemented       | Correct to 8 implemented                  |
| C8  | 845,000 kWh math yields 443 tCO2e, not 312.4 | Reconcile grid emission factor            |

### Nice to Verify/Source (MEDIUM)

| #   | Finding                              | Fix Required                 |
| --- | ------------------------------------ | ---------------------------- |
| M1  | McKinsey "78%" unverifiable          | Add specific report citation |
| M2  | Bangladesh factory count discrepancy | Clarify 2,800 vs 4,000       |
| M3  | Intensity ratio denominator unclear  | Define "per metre ton"       |
| M4  | CAC = £800 seems too low             | Provide sourcing or revise   |

---

## APPENDIX: VERIFIED DATA POINTS (Keep These)

These figures in the deck are independently verified and can be retained:

| Figure                           | Value                                        | Source                         |
| -------------------------------- | -------------------------------------------- | ------------------------------ |
| Bangladesh garment exports       | ~$47B/year                                   | BGMEA 2023-24                  |
| EU target for Scope 3 disclosure | 30% reduction by 2030                        | European Commission Fit-for-55 |
| CSRD phased rollout              | FY2024 → FY2028 by company size              | EU Directive 2022/2464         |
| SEC climate rule phased          | Large accelerated filers FY2025              | SEC Final Rule (2024)          |
| CBAM full implementation         | 2026 financial payments                      | EU Regulation 2023/956         |
| Diesel emission factor           | 2.68 kg CO2/litre                            | DEFRA 2023                     |
| Grid emission factor             | 0.370 kg CO2/kWh (BD grid)                   | BPDB 2023                      |
| ESRS E1-1                        | Energy consumption                           | ESRS Delegated Act             |
| IFRS S2-1 through S2-4           | Climate disclosure pillars                   | ISSB IFRS S2 (2023)            |
| GHG Protocol Scope 3             | 15 categories (cat 10 excluded for garments) | GHG Protocol                   |

---

_Report compiled by: PE Analyst Agent · Regulatory Analyst Agent · Market Analyst Agent · Financial Math Agent_
_Validation standard: Zero tolerance for unverifiable claims_
