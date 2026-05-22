# Competitive Landscape — ESG SCRM

## Competitor Matrix

| Competitor               | Segment                      | Pricing                      | ESG Data Orchestration     | Supplier Collection        | Evidence Vault          | Real-Time Monitoring |
| ------------------------ | ---------------------------- | ---------------------------- | -------------------------- | -------------------------- | ----------------------- | -------------------- |
| **EcoVadis**             | Enterprise + mid-market      | $2K-50K/year (supplier tier) | No — ratings only          | Portal-based (email login) | Rating certificate only | No                   |
| **Sedex/SMETA**          | Supply chain audits          | $3K-15K/year                 | No                         | Audit-based (onsite)       | Audit report PDF        | No                   |
| **Persefoni**            | Enterprise carbon accounting | $25-100K+/year               | Yes — framework mapping    | No supplier collection     | Audit trail (basic)     | No real-time         |
| **Watershed**            | Enterprise ESG               | $50-200K+/year               | Yes — multi-framework      | No supplier messaging      | Enterprise audit trail  | Manual "continuous"  |
| **Sweep**                | Enterprise ESG platform      | $30-150K+/year               | Yes — deep SAP integration | No WhatsApp/messaging      | Enterprise audit trail  | No live sensors      |
| **Workiva**              | Enterprise reporting/audit   | $25-75K+/year                | Framework mapping          | No supplier collection     | Strong audit trail      | No monitoring        |
| **Sphera/OneTrust**      | Enterprise ESG management    | $50-150K+/year               | LCA + reporting            | Limited supplier portal    | Enterprise audit        | No live monitoring   |
| **Higg Index / Worldly** | Apparel sustainability       | $1K-10K/year                 | Higg FEM/FSL mapping       | Self-assessment portal     | Facility-level data     | No live monitoring   |

## Gap Analysis — Where No One Plays

### 1. Mid-Market + Messaging-Native Supplier Collection (NO ONE DOES THIS)

EcoVadis and Sedex both require suppliers to create accounts on web portals. This is a deal-killer for a Bangladesh dye house owner who checks WhatsApp between production runs. No competitor offers WhatsApp/LINE/WeChat-native supplier ESG data collection.

**Why no one does it**: Western-founded ESG platforms assume desktop-first users. The supplier portal model works for European/US suppliers. It fails in Bangladesh, Vietnam, and Indonesia where mobile messaging is the primary business communication channel.

**Our moat**: The messaging infrastructure (WhatsApp Business API + LINE + WeChat + response parsing + localization) takes 6-12 months to build correctly. Once built, it's a genuine barrier to entry.

### 2. Real-Time IoT Monitoring for Mid-Market (NO ONE DOES THIS)

Watershed has "continuous monitoring" but it's manual data uploads, not live sensor feeds. No mid-market ESG platform connects to MQTT/IoT sensors for real-time emissions/energy/water dashboards.

**Why no one does it**: Enterprise ESG platforms target CSOs who need reports, not operations managers who need dashboards. IoT integration is technically hard and factory-specific. The mid-market segment doesn't justify the engineering investment for enterprise vendors.

**Our moat**: The MQTT pipeline is built. Competitors would need 3-6 months to replicate. But the moat is narrow — the value is in the connector library, not the dashboard.

### 3. Per-Data-Point Confidence Tagging (UNIQUE)

No competitor tags individual data points with HIGH/MEDIUM/LOW confidence levels. EcoVadis rates companies overall. Persefoni reports by category. None goes down to individual metric confidence.

**Why no one does it**: It creates legal liability. If you tag a Scope 3 number as "MEDIUM confidence" and a regulator challenges it, you need a defensible methodology. Most platforms avoid this by not offering it.

**Our moat**: Defensible if the methodology is sound. Risky if it's not.

### 4. Self-Serve Onboarding in 3-6 Weeks (CLAIMED, NOT PROVEN)

Sweep, Persefoni, Watershed all require 3-6 month enterprise implementations with consultants. No competitor offers self-serve onboarding for mid-market ESG.

**Why no one does it**: ERP integration genuinely takes months. The "3-6 weeks" claim requires either (a) CSV upload instead of live ERP connection, or (b) a pre-built connector library that doesn't exist yet.

**Our moat**: None until proven. The 3-6 week claim is a positioning statement, not a technical reality. Must be validated with a real customer.

## Asia-Focused ESG Platforms

### Existing players in the region

- **Higg Index / Worldly** (formerly Sustainable Apparel Coalition): dominant in apparel, self-assessment model, no live monitoring, no WhatsApp collection. Pricing accessible ($1K-10K/year). Weak on Scope 3 supplier engagement.
- **Greenee** (Japan): carbon accounting for Japanese SMEs, no supplier collection, no monitoring.
- **Carbonstop** (China): Chinese carbon management, WeChat integration exists, but limited to Chinese market.

### Where we fit

- **Bangladesh garment → H&M/Zara**: No local competitor. EcoVadis is too expensive. Higg Index doesn't collect supplier data. We are the only WhatsApp-native, Bengali-localized, H&M-scope-3-focused option.
- **Vietnam textile/electronics**: LINE + Zalo integration needed. No local competitor for messaging-native collection.
- **India pharma/auto**: WhatsApp dominant. No local ESG competitor with WhatsApp collection.

## Competitive Positioning

### Head-to-head vs EcoVadis

- **We lose on**: Brand recognition, network effects (130K rated companies), audit acceptance
- **We win on**: Price ($24-60K vs $50K+), messaging-native supplier collection, real-time monitoring, mid-market speed
- **Strategy**: Don't compete head-to-head. Position as "EcoVadis for supplier data collection, not supplier ratings." Complement, don't replace.

### Head-to-head vs doing nothing / Excel

- **We lose on**: Cost (free vs $24K/year), familiarity, no vendor lock-in
- **We win on**: Time saved (3 weeks → 2 days for H&M questionnaire), audit credibility, Scope 3 coverage
- **Strategy**: Lead with H&M contract renewal risk. "Your H&M contract requires Scope 3 data. Excel won't get you there."

## Key Insight

The competitive moat is NOT any single feature. It's the **combination** of messaging-native supplier collection + per-data-point confidence tagging + IoT monitoring in one platform at mid-market pricing. No competitor offers all four. The risk is that no competitor offers all four because **no one has validated that mid-market buyers want all four**. The CFO buys Feature 2 (supplier collection). The operations manager wants Feature 4 (monitoring). The auditor wants Feature 3 (evidence vault). The CFO signs the check for Feature 2.
