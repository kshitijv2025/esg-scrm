#!/usr/bin/env python3
"""Generate PITCH_ANALYSIS.docx and INVESTOR_PREREAD.docx with updated content."""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
import re

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def set_cell_shading(cell, color):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color)
    shading.set(qn('w:val'), 'clear')
    cell._tc.get_or_add_tcPr().append(shading)

def add_styled_table(doc, headers, rows, header_color="1B4332"):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Header row
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(h)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.size = Pt(9)
        set_cell_shading(cell, header_color)
    # Data rows
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(str(val))
            run.font.size = Pt(9)
    return table

def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x1B, 0x43, 0x32)
    return h

def add_body(doc, text, bold=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(10)
    return p

def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(text, style='List Bullet')
    p.paragraph_format.left_indent = Cm(1.27 + level * 0.63)
    for run in p.runs:
        run.font.size = Pt(10)
    return p

def add_numbered(doc, text):
    p = doc.add_paragraph(text, style='List Number')
    for run in p.runs:
        run.font.size = Pt(10)
    return p

# ============================================================
# DOCUMENT 1: PITCH_ANALYSIS.docx
# ============================================================

def create_pitch_analysis():
    doc = Document()

    # Styles
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(10)

    # Title Page
    for _ in range(6):
        doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("ESG + SCRM Startup")
    run.bold = True
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor(0x1B, 0x43, 0x32)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Full Pitch Analysis & Red-Team Report")
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x52, 0x78, 0x6B)

    doc.add_paragraph()
    tagline = doc.add_paragraph()
    tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = tagline.add_run("Complete analysis of the original startup proposal, all red-team critiques,\nfounder counter-arguments, detailed product breakdown, and the final investor verdict.")
    run.font.size = Pt(11)
    run.italic = True

    doc.add_page_break()

    # ---- PART 1 ----
    add_heading(doc, "Part 1: What Changed From the Original Proposal", level=1)
    add_heading(doc, "The Original Idea", level=2)
    add_body(doc, "The founding team proposed five ESG product concepts and a Supply Chain Risk Management overlay:")

    features = [
        "ESG Data Orchestration Platform — A mapping engine that takes one internal KPI and outputs it across multiple frameworks (CSRD, ISSB, GRI, TCFD). ETL pipelines pull from existing systems (SAP, Workday, Coupa).",
        "Supply-Chain ESG Data Collection — Automated supplier questionnaires and data feeds for Scope 3 emissions and supply chain ESG scoring.",
        "Assurance-Ready Evidence Vault — An audit trail with data lineage so external auditors (Big 4) can verify reports without manual evidence gathering.",
        "ESG ROI Engine — A module that translates ESG activities into financial metrics (cost savings, risk reduction, brand value) so CFOs see ROI, not just compliance cost.",
        "Mid-Market ESG Reporting in a Box — A turnkey solution for mid-market companies (500–5,000 employees) that can't afford Persefoni or Watershed.",
    ]
    for f in features:
        add_numbered(doc, f)
    add_bullet(doc, "Supplier ESG-Risk Scorecard — an SCRM layer where buyers assess, monitor, and score suppliers on ESG criteria, integrated with procurement workflows.")

    # What Evolved
    add_heading(doc, "What Evolved Through Our Analysis", level=2)
    add_styled_table(doc,
        ["Dimension", "Original Proposal", "After Analysis"],
        [
            ["Target Customer", "Broad — companies that need ESG reporting", "Focused — mid-market (500–5,000 employees) globally, facing CSRD/CSDDD compliance"],
            ["Value Proposition", "ESG reporting platform", "Compliance-first tool that delivers operational benefits"],
            ["Competitive Positioning", "Not addressed", "ESG + SCRM combined — nobody else does both"],
            ["Integration Strategy", "Connect to SAP, Workday, etc.", "Broad multi-system including SAP Business One, NetSuite, Xero, local HRIS, messaging APIs"],
            ["Product Scope", "5 separate products", "One integrated platform — compliance is wedge, SCRM + ROI are expansion"],
            ["Moat", "Not defined", "ESG + SCRM combination + mid-market design + broad integration + messaging-native engagement"],
            ["Go-to-Market", "Not defined", "Option C: mid-market (70%) + enterprise (30%) simultaneously"],
            ["Revenue Model", "Not defined", "SaaS $2,000–5,000/month mid-market, $60–150K/year enterprise"],
            ["Geography", "Not defined", "Global — starting with Asia (Bangladesh garments #1)"],
            ["Consumer Demand", "Not referenced", "76–80% of consumers prefer ESG-focused companies (PwC, NielsenIQ, Deloitte, McKinsey, IBM)"],
        ]
    )

    # Key Decisions
    add_heading(doc, "Key Strategic Decisions", level=2)
    decisions = [
        "Mid-market is the beachhead — companies most worried about compliance and least served by existing tools",
        "Compliance wins the deal, operations retains the customer",
        "ESG + SCRM combined is the USP — pricing is NOT the differentiator",
        "Broad integration is the differentiation",
        "Option C: do both mid-market and enterprise simultaneously",
        "5 customers in 90 days is the proof",
        "Global product, not region-specific",
    ]
    for d in decisions:
        add_numbered(doc, d)

    doc.add_page_break()

    # ---- PART 1A: USP vs Sweep ----
    add_heading(doc, "Part 1A: USP vs. Sweep", level=1)
    add_heading(doc, "The Four Structural USPs", level=2)
    add_styled_table(doc,
        ["USP", "Why Sweep Can't Copy It", "Moat Depth"],
        [
            ["ESG + SCRM combined", "Sweep is a reporting tool. Adding SCRM requires fundamentally different architecture.", "Very deep — 18+ months to replicate"],
            ["Mid-market buyer design", "Sweep is built for the Chief Sustainability Officer. We're built for the CFO/COO.", "Deep — requires rethinking entire UX"],
            ["Broad integration", "Sweep goes deep on SAP S/4HANA. We go broad — SAP Business One, NetSuite, Xero, local HRIS.", "Deep — per-market connectors expensive to replicate"],
            ["Messaging-native supplier engagement", "Mid-market suppliers respond to WhatsApp/LINE/WeChat, not email portals.", "Deep — requires per-market messaging infrastructure"],
        ]
    )

    add_heading(doc, "Product Comparison", level=2)
    add_styled_table(doc,
        ["Feature", "Sweep", "This Startup"],
        [
            ["ESG Framework Mapping", "CSRD, ISSB, GRI, TCFD, SBTi", "CSRD, ISSB, GRI, TCFD + local regulations per market"],
            ["Supply Chain Risk Management", "No — tracks supplier emissions only", "Yes — ESG scoring + disruption risk + financial health + geopolitical risk"],
            ["Supplier Data Collection", "Email questionnaires, supplier portal", "Messaging bot (WhatsApp/LINE/WeChat) + email + portal"],
            ["ROI Engine", "No — reporting tool only", "Yes — cost savings, risk reduction, brand value"],
            ["Buyer", "Chief Sustainability Officer", "CFO / COO"],
            ["Implementation time", "3–6 months with consultants", "3–6 weeks, self-serve"],
            ["Integrations", "Deep on SAP S/4HANA, Workday", "Broad — SAP Business One, NetSuite, Xero, local HRIS, procurement tools"],
        ]
    )

    add_heading(doc, "What Sweep Does Better", level=2)
    sweep_better = [
        "Carbon measurement depth: Granular carbon accounting for CDP and SBTi",
        "Enterprise features: SSO, SCIM, advanced permissions, SOC 2 certified",
        "Big 4 auditor trust: Established relationships with Deloitte, EY, PwC, KPMG",
        "Brand recognition: 200+ enterprise customers",
        "Team depth: 200+ people including ex-Big 4 sustainability consultants",
        "Funding runway: $100M+ — can survive 3–5 years without profitability",
    ]
    for s in sweep_better:
        add_bullet(doc, s)

    doc.add_page_break()

    # ---- PART 1B: Go-to-Market ----
    add_heading(doc, "Part 1B: Go-to-Market Strategy — Option C", level=1)
    add_body(doc, "Two parallel tracks — mid-market (70%) + enterprise division-level (30%).")

    add_heading(doc, "Track 1: Mid-Market (70% of effort)", level=2)
    add_styled_table(doc, ["", ""], [
        ["Goal", "Revenue + product-market fit + case studies"],
        ["Customer", "500–5,000 employees"],
        ["Buyer", "CFO / COO"],
        ["Deal size", "$24–60K/year"],
        ["Sales cycle", "4–8 weeks"],
        ["Target", "30–50 customers in 18 months"],
    ])

    add_heading(doc, "Track 2: Enterprise Division-Level (30% of effort)", level=2)
    add_styled_table(doc, ["", ""], [
        ["Goal", "Learn enterprise requirements + land 1–2 division deals"],
        ["Customer", "Division of a large enterprise (not company-wide)"],
        ["Buyer", "VP of Operations or Division CFO"],
        ["Deal size", "$60–100K/year"],
        ["Sales cycle", "3–6 months"],
    ])

    add_heading(doc, "Resource Allocation Over Time", level=2)
    add_styled_table(doc, ["Period", "Mid-Market Focus", "Enterprise Focus"], [
        ["Months 1–6", "80%", "20%"],
        ["Months 6–12", "60%", "40%"],
        ["Months 12–18", "40%", "60%"],
    ])

    doc.add_page_break()

    # ---- PART 1C: Target Markets ----
    add_heading(doc, "Part 1C: Target Markets — Asian Mid-Market Companies", level=1)
    add_styled_table(doc, ["Rank", "Market", "Why"], [
        ["1", "Bangladesh (garments)", "4,000+ garment factories exporting to EU. Every one receiving ESG questionnaires from H&M, Zara, Primark TODAY."],
        ["2", "Vietnam (textiles + electronics + furniture)", "EU is top export market. EUDR + CSDDD creating immediate demand."],
        ["3", "India (pharma + auto components + IT services)", "Largest number of mid-market companies. EU + US compliance pressure."],
        ["4", "Thailand (auto parts + food processing)", "Automotive supply chain to EU/Japan. Toyota/BMW supplier requirements."],
        ["5", "Indonesia (palm oil + textiles)", "EUDR is existential for palm oil exporters — comply or lose EU market access."],
    ])

    doc.add_page_break()

    # ---- PART 1D: The Core Problem ----
    add_heading(doc, "Part 1D: The Core Problem", level=1)
    add_heading(doc, "How Mid-Market Companies Do ESG Today", level=2)
    add_styled_table(doc, ["Method", "% of Companies", "Annual Cost"], [
        ["Excel + Email", "70–80%", "40–60 hours per cycle, poor data quality, no audit trail"],
        ["Consultant + PowerPoint", "15–20%", "$10–30K per report, static PDF, no continuity"],
        ["Point Solutions", "5–10%", "$5–15K per tool, fragmented, no unified view"],
        ["Nothing", "5–10%", "Risk of losing major buyer contracts"],
    ])

    add_heading(doc, "The Real Problem: Not One Questionnaire, Ten", level=2)
    add_styled_table(doc, ["Month", "Buyer", "Format", "What Happens"], [
        ["January", "H&M", "Excel, their template", "15 pages of ESG data"],
        ["February", "Zara (Inditex)", "Web portal, their system", "180 questions, same data, different structure"],
        ["March", "Primark", "PDF form", "12 pages, different grouping"],
        ["April", "C&A", "EcoVadis platform", "200+ questions"],
        ["May", "Marks & Spencer", "Proprietary Excel", "25 pages, UK-specific metrics"],
        ["July", "Target (US)", "Different web portal", "Imperial units, US frameworks"],
        ["September", "H&M", "Updated questionnaire v2", "They changed 30 questions"],
        ["October", "New buyer", "Unknown format", "Start from scratch"],
    ])
    add_body(doc, "Same data entered 8–12 times per year in different formats. That's the problem.", bold=True)

    add_heading(doc, "Before & After", level=2)
    add_body(doc, "Before (Current State — 10 weeks, one buyer):")
    before = [
        "Week 1–2: Receive ESG questionnaire from H&M",
        "Week 2–3: Email plant manager for energy data → wait for reply",
        "Week 3–4: Email HR for diversity data → wait for reply",
        "Week 4–5: Call 20 suppliers for ESG certificates → 8 respond",
        "Week 5–6: Manually enter everything into Excel",
        "Week 6–7: H&M sends back 30 clarification questions",
        "Week 8–10: Final submission",
    ]
    for b in before:
        add_numbered(doc, b)

    add_body(doc, "After (With This Platform — 5 days, one buyer):")
    after = [
        "Day 1: Upload H&M questionnaire → platform auto-maps 70–80% to existing data",
        "Day 2: Platform sends automated messages to 5 suppliers; suppliers reply via WhatsApp",
        "Day 3–4: Compliance officer reviews and fills remaining 20–30%",
        "Day 5: Auto-generated report with full audit trail → submit to H&M",
        "Next week: Zara's questionnaire arrives → same data, different format, auto-filled with zero extra work",
    ]
    for a in after:
        add_numbered(doc, a)

    doc.add_page_break()

    # ---- PART 1E: Technical Foundation ----
    add_heading(doc, "Part 1E: Technical Foundation", level=1)
    add_heading(doc, "Emission Calculation: Three Methods", level=2)
    add_styled_table(doc, ["Method", "How It Works", "Confidence", "Example"], [
        ["1. Direct Measurement", "Physical meter or sensor reading", "HIGH", "Electricity meter: 1,200,000 kWh × Vietnam grid factor = 864 tonnes CO2"],
        ["2. Activity-Based", "Activity data × published emission factor", "MEDIUM", "Diesel: 50,000 litres × 2.68 kg CO2/litre = 134 tonnes CO2"],
        ["3. Spend-Based Estimate", "Financial spend × industry emission factor", "LOW", "Flights spend: $200,000 × 0.255 kg CO2/$ = 51 tonnes CO2"],
    ])

    add_heading(doc, "Scope 3: Where SCRM Meets ESG", level=2)
    add_styled_table(doc, ["Category", "What It Covers", "Tonnes CO2", "Method"], [
        ["1. Purchased goods & services", "Cotton, polyester, dyes, packaging", "~2,051", "Spend-based initially, improves as suppliers engage"],
        ["4. Upstream transportation", "Shipping raw materials to factory", "~56", "Weight × distance × transport mode factor"],
        ["5. Waste generated", "Fabric scraps, chemical waste", "~15", "Waste records × disposal method factors"],
        ["7. Employee commuting", "How 2,000 workers get to work", "~484", "Employee survey × transport factors"],
        ["9. Downstream transportation", "Shipping finished garments to H&M", "~53", "Shipment records × mode factors"],
        ["Total Scope 3", "", "~2,659", ""],
        ["Scope 1 + 2", "Factory operations + electricity", "~1,064", ""],
        ["Grand Total", "", "~3,723", "Scope 3 is 72%"],
    ])

    add_heading(doc, "Three-Layer Data Maturity Model", level=2)
    add_styled_table(doc, ["Layer", "When", "Method", "Confidence"], [
        ["1. Spend-based", "Day 1", "$1.2M cotton spend × 0.94 kg CO2/$ = 1,128 tonnes", "LOW but immediate"],
        ["2. Supplier-specific", "Month 2–3", "Supplier provides energy/fertilizer data → 580 tonnes", "MEDIUM — 49% lower"],
        ["3. Verified", "Month 6+", "Supplier uses the tool → data flows automatically quarterly", "HIGH"],
    ])

    doc.add_page_break()

    # ---- PART 1F: EcoVadis Differentiation (NEW) ----
    add_heading(doc, "Part 1F: EcoVadis Differentiation Analysis", level=1)
    add_body(doc, "Competitive analysis of EcoVadis identified key weaknesses and product opportunities. The following maps each suggestion to our plan and identifies three new features.")

    add_heading(doc, "EcoVadis Weaknesses (Our Entry Points)", level=2)
    weaknesses = [
        "Static, backward-looking — Annual assessments, no real-time performance",
        "Compliance-heavy, not decision-oriented — Produces scores, not actions",
        "Painful UX + manual effort — Long questionnaires, heavy documentation burden",
        "Weak linkage to financial impact — ESG score doesn't equal ROI clarity",
        "Shallow supplier visibility — Relies heavily on self-reported supplier data",
    ]
    for i, w in enumerate(weaknesses, 1):
        add_numbered(doc, w)

    add_heading(doc, "Feature Comparison: EcoVadis Suggestions vs Our Plan", level=2)
    add_styled_table(doc,
        ["What the Doc Says", "Doing It Now?", "Doable?", "Why Not Now"],
        [
            ["Real-time ESG OS with ERP + IoT + live alerts", "Partial", "Month 0", "Sensors exist, ERP is integration point"],
            ["AI Copilot — auto-fill, policies, conversational", "Partial", "3-6 months", "Need regulatory knowledge base first"],
            ["Supplier Intelligence Graph — news, sanctions", "No", "3-6 months (v1), 12+ (full)", "English + sanctions is API calls. Multilingual is harder"],
            ["ESG → Profit Engine — CFO dashboards", "Yes", "Already in plan", "—"],
            ["SaaS tiered pricing", "Yes", "Already in plan", "—"],
            ["Supplier network monetization", "No", "Year 2", "Need buyers on platform first"],
            ["Premium modules as add-ons", "Implicit", "Yes", "—"],
            ["Data monetization — benchmarks, API", "No", "Year 2+", "Need customer data volume"],
            ["Consulting + implementation", "No", "Skip", "Distracts from product"],
            ["Construction/infrastructure niche", "No", "Skip", "Garment focus is sharper"],
        ]
    )

    add_heading(doc, "Three New Features Added to Product Roadmap", level=2)

    add_heading(doc, "Feature 6: Real-Time ESG Monitoring", level=3)
    add_body(doc, "Live sustainability command center connecting to existing IoT sensors and ERP systems for real-time emissions, energy, and resource monitoring with threshold alerts.")
    add_body(doc, "Why Month 0: Mid-market export manufacturers already have PLC-controlled production lines, smart energy meters, water flow meters, and building management systems. We're not installing sensors — we're reading existing sensor data through the ERP systems we're already connecting to.")
    add_body(doc, "Differentiation: EcoVadis gives an annual score. We give a live dashboard.")

    add_heading(doc, "Feature 7: AI Sustainability Copilot", level=3)
    add_body(doc, "Conversational AI that auto-fills questionnaires, generates ESG policies, suggests improvements, and provides step-by-step improvement roadmaps.")
    add_body(doc, "Why 3-6 months: The ESG co-founder builds the regulatory knowledge base and validates AI output. The tech is LLM integration — the differentiator is domain-accurate content.")
    add_body(doc, "Differentiation: EcoVadis tells you your score. We tell you how to improve it and generate the documents you need.")

    add_heading(doc, "Feature 8: Supplier Intelligence Graph", level=3)
    add_body(doc, "Independent supplier risk intelligence using news, sanctions lists, trade data, and ESG violation databases — not relying on supplier self-reporting.")
    add_body(doc, "Why 3-6 months for v1: English-language news APIs + sanctions lists + sentiment analysis via LLM = straightforward API integration. Full multilingual version takes 12+ months.")
    add_body(doc, "Differentiation: EcoVadis relies on self-reported data. We build independent intelligence that flags risks the supplier would never self-report.")

    add_heading(doc, "Updated Product Summary", level=3)
    add_styled_table(doc, ["Feature", "Status", "Timeline"], [
        ["ESG Data Orchestration Platform", "In plan", "Month 0"],
        ["Supply-Chain ESG Data Collection", "In plan", "Month 0"],
        ["Assurance-Ready Evidence Vault", "In plan", "Month 0"],
        ["ESG ROI Engine", "In plan", "Month 0"],
        ["Mid-Market ESG Reporting in a Box", "In plan", "Month 0"],
        ["Supplier ESG-Risk Scorecard (SCRM)", "In plan", "Month 0"],
        ["Real-Time ESG Monitoring", "NEW", "Month 0"],
        ["AI Sustainability Copilot", "NEW", "3-6 months"],
        ["Supplier Intelligence Graph", "NEW", "3-6 months (v1), 12+ months (full)"],
    ], header_color="2D6A4F")

    doc.add_page_break()

    # ---- PART 2: Red-Team Critiques ----
    add_heading(doc, "Part 2: Red-Team & Destroy — All Critiques", level=1)

    add_heading(doc, "Round 1: The Initial Destroy", level=2)
    critiques_1 = [
        ("Critique 1: SAP and Workday Will Eat You", "SAP and Workday already own the data. When they add ESG modules, they have distribution, trust, and zero switching cost."),
        ("Critique 2: No Technical Co-Founder, No Product", "Three MBA students pitching a data engineering product with no technical founder. The product requires ETL pipelines, API integrations, data mapping engines, and assurance-grade audit trails."),
        ("Critique 3: No Moat — Anyone Can Build This", "ESG reporting is fundamentally a data transformation problem. The frameworks are public. The mapping logic is deterministic."),
        ("Critique 4: Sweep, Persefoni, and Watershed Already Exist", "They have raised $100M+ each. They have hundreds of enterprise customers and war chests."),
        ("Critique 5: Regulation-Dependent Business = Fragile Business", "If your entire value prop is CSRD compliance, what happens when regulation is delayed, weakened, or replaced?"),
        ("Critique 6: No Customers, No Traction, No Proof", "Zero paying customers, zero LOIs, zero pilot programs. You have a document, not a business."),
    ]
    for title, desc in critiques_1:
        add_body(doc, title, bold=True)
        add_body(doc, desc)

    add_heading(doc, "Round 2: Deeper Structural Flaws", level=2)
    critiques_2 = [
        ("Critique 7: Sweep Feature-Parity is a Race You Lose", "To win against Sweep, you need everything they have plus something they don't. Building feature parity with a $100M-funded competitor is a losing strategy."),
        ("Critique 8: Compliance Tool Branding Limits Your Ceiling", "If you brand as ESG compliance tool, CFOs treat you as a cost center. That means pricing pressure, low retention, and zero expansion revenue."),
        ("Critique 9: Mid-Market is Where Startups Go to Die", "Mid-market companies have higher churn risk, lower ACV, and less ability to pay for premium integrations."),
        ("Critique 10: The Technical Co-Founder Question Was Never Fully Answered", "Has he shipped enterprise SaaS before? Does he have vesting? Is he committed full-time?"),
        ("Critique 11: Consumer ESG Preference Data is Interesting But Indirect", "Mid-market CFOs buy because regulators require it, not because consumers prefer ESG."),
    ]
    for title, desc in critiques_2:
        add_body(doc, title, bold=True)
        add_body(doc, desc)

    add_heading(doc, "Round 3: The Final Gate", level=2)
    critiques_3 = [
        ("Critique 12: Gross Margin Risk", "If every customer requires heavy custom integration work, the business is consulting dressed up as SaaS. 50–60% gross margin instead of 80%+."),
        ("Critique 13: The 18-Month Clock", "Sweep has $100M+ and 200+ customers. They will eventually move down-market. Roughly 18 months before the well-funded incumbent notices the mid-market segment."),
        ("Critique 14: Technical Co-Founder Vesting", "Even with a technical co-founder, the structural risk remains if he walks in month 6. A 4-year vesting schedule with 1-year cliff must be signed before any money is wired."),
    ]
    for title, desc in critiques_3:
        add_body(doc, title, bold=True)
        add_body(doc, desc)

    doc.add_page_break()

    # ---- PART 3: Full Transcripts ----
    add_heading(doc, "Part 3: All Red-Team Conversations (Full Transcript)", level=1)

    # Round 1
    add_heading(doc, "Round 1: The Initial Destroy", level=2)
    add_body(doc, "Founders: As a VC investor listening to this as a startup pitch by three MBA students, destroy this idea as to why you will not invest.", bold=True)
    add_body(doc, "VC Response:")
    vc_points_1 = [
        "Problem 1: You're Building on Someone Else's Land — SAP already has Sustainability Control Tower. Workday already has ESG reporting modules.",
        "Problem 2: Three MBAs and No Builder — You're pitching a data engineering product and your team is three people who take meetings for a living.",
        "Problem 3: Sweep Already Did This — Sweep raised $100M+. Persefoni raised $100M+. Watershed raised $100M+.",
        "Problem 4: Regulatory Dependency is Not a Business Model — A business that only works when the government forces people to buy it is not a business.",
        "Problem 5: No Moat — ESG reporting is a data transformation problem. The frameworks are public. There is nothing proprietary about it.",
        "Problem 6: Show Me the Money — Zero customers. Zero LOIs. Zero pilots. You have a document, not a business.",
    ]
    for v in vc_points_1:
        add_bullet(doc, v)
    add_body(doc, "Verdict: Pass.", bold=True)

    # Round 2
    add_heading(doc, "Round 2: Founder Pushback & Deeper Destroy", level=2)
    add_body(doc, "Founders: We have a technical co-founder who has shipped enterprise SaaS before. What would it take to get money invested?", bold=True)
    add_body(doc, "VC Response: The tech co-founder changes the conversation. Not enough to write a cheque, but enough to keep talking. Here's what it would take:")
    vc_requirements = [
        "5 paying customers — Signed contracts with money in the bank, not LOIs or pilots.",
        "A technical co-founder who's committed — Full-time, with equity vesting, who has shipped enterprise SaaS.",
        "Integration proof — At least one live ERP integration in production.",
        "Clear differentiation from Sweep — Not 'we're cheaper.' What SPECIFIC thing does your product do that Sweep cannot do?",
        "A revenue model that makes sense — ACV, gross margin, expansion revenue thesis.",
        "A story that doesn't start and end with regulation — What keeps customers paying in year 3?",
    ]
    for r in vc_requirements:
        add_numbered(doc, r)

    add_body(doc, "Founders: Will get 5 paying customers. Our product is valuable even without regulation. Will you now invest?", bold=True)
    add_body(doc, "VC Response — Round 2 Destroy: Not yet. The 5 customers need to be the RIGHT 5. If all 5 are family companies → you proved you can network, not sell. If all 5 churn in 6 months → you proved you can close but can't retain.")

    # Round 3
    add_heading(doc, "Round 3: Consumer ESG Defense & Strategy Questions", level=2)
    add_body(doc, "Founders: Consumers also prefer companies which are ESG focused. What about surveys showing consumers prefer ESG companies?", bold=True)

    add_heading(doc, "Consumer ESG Preference Data", level=3)
    add_styled_table(doc, ["Survey Source", "Key Finding"], [
        ["PwC (2023/2024)", "76% of consumers prefer companies acting responsibly on ESG. Willing to pay ~9.7% premium."],
        ["NielsenIQ", "73% of global consumers would change consumption habits to reduce environmental impact."],
        ["Deloitte (2024)", "1 in 3 consumers actively chose a more sustainable brand. Cost-of-living crisis has NOT killed ESG demand."],
        ["McKinsey", "66–80% willingness to pay more for sustainable products, trend accelerating."],
        ["IBM", "51% of consumers say sustainability is more important than 12 months ago."],
        ["Simon-Kucher", "63% have changed purchasing behavior toward sustainability in past 5 years."],
        ["First Insight / Wharton", "68% willing to pay more for sustainable products. Gap between saying and doing is narrowing."],
    ])

    add_body(doc, "VC Response: The consumer data proves ESG is structural, not a fad. But consumer preference doesn't directly translate to B2B SaaS demand. The consumer data supports the macro thesis but doesn't close the micro sale.")

    # Round 4
    add_heading(doc, "Round 4: The 90-Day Challenge & Final Verdict", level=2)
    add_body(doc, "Founders: Done, see you in 90 days with 5 customers. Will you write a cheque then?", bold=True)
    add_body(doc, "VC Final Verdict: Conditional yes.")

    add_heading(doc, "Investment Tiers", level=3)
    add_styled_table(doc, ["Tier", "Scenario", "Cheque", "Valuation"], [
        ["Tier 1", "5 customers, $2-5K/month ACV, 3+ inbound, weekly usage, 1+ renewal", "$2M seed", "$8-10M pre-money"],
        ["Tier 2", "5 customers, all warm network, low ACV, high churn risk", "$500K-1M pre-seed", "$3-4M pre-money"],
        ["Tier 3", "None mid-market, no integration live, not using SCRM layer", "No thanks", "—"],
    ])

    add_heading(doc, "Three Remaining Concerns", level=3)
    concerns = [
        "Gross margin — proof that onboarding is configurable, not bespoke",
        "18-month clock — plan for when Sweep moves down-market",
        "Tech co-founder vesting — 4-year vesting, 1-year cliff, signed before wire",
    ]
    for c in concerns:
        add_numbered(doc, c)

    doc.add_page_break()

    # ---- CLOSING ----
    add_heading(doc, "Closing", level=1)
    add_body(doc, "The founders didn't fold. Through every round of criticism — 'SAP will kill you,' 'you have no moat,' 'three MBAs with no tech,' 'Sweep already exists,' 'regulation-dependent businesses are fragile,' 'mid-market is where startups go to die' — they came back with counter-arguments, consumer data, sharper positioning, and a concrete 90-day execution plan.")
    add_body(doc, "That matters more than the idea. Ideas are cheap. The ability to take a beating and still be standing — that's what you bet on.")
    add_body(doc, "The founders are going to get 5 customers. If they're the right 5 — the kind that prove the thesis, not just the ability to sell to friends — and they come back with signed contracts, live integrations, and weekly usage data, they won't just get one cheque. They'll get introductions to three other funds who should co-invest.")
    add_body(doc, "ESG is structurally permanent. The mid-market gap is real. The consumer data confirms the tailwind. The 90-day sprint to 5 customers is the right filter.")
    add_body(doc, "The founders have 90 days. The clock is ticking.", bold=True)

    doc.add_paragraph()
    disclaimer = doc.add_paragraph()
    run = disclaimer.add_run("This analysis was prepared as part of the Machine Learning for Decision Making course, Term 4. All VC responses are simulated for educational purposes — the pushback reflects real investor concerns but is not actual investment advice.")
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    doc.save("/Users/kshitijverma/Desktop/Class Notes/Term 4/Machine Learning For Decision Making/ESG SCRM/PITCH_ANALYSIS.docx")
    print("PITCH_ANALYSIS.docx saved.")


# ============================================================
# DOCUMENT 2: INVESTOR_PREREAD.docx
# ============================================================

def create_investor_preread():
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(10)

    # ---- COVER PAGE ----
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("CONFIDENTIAL")
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("[Company Name]")
    run.bold = True
    run.font.size = Pt(32)
    run.font.color.rgb = RGBColor(0x1B, 0x43, 0x32)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("ESG + Supply Chain Risk Management Platform")
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x52, 0x78, 0x6B)

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Investor Pre-Read")
    run.font.size = Pt(14)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Seed Round — [Date]")
    run.font.size = Pt(12)
    run.italic = True

    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Prepared by [Founders]")
    run.font.size = Pt(11)

    doc.add_page_break()

    # ---- TABLE OF CONTENTS ----
    add_heading(doc, "Table of Contents", level=1)
    toc_items = [
        "1. Executive Summary",
        "2. The Problem",
        "3. Our Solution",
        "4. Technical Overview",
        "5. Market Opportunity",
        "6. Competitive Landscape",
        "7. Business Model",
        "8. Go-to-Market Strategy",
        "9. Team",
        "10. 90-Day Milestone Plan",
        "11. The Ask",
        "12. Why Now",
    ]
    for item in toc_items:
        add_body(doc, item)

    doc.add_page_break()

    # ---- 1. EXECUTIVE SUMMARY ----
    add_heading(doc, "1. Executive Summary", level=1)
    add_body(doc, "[Company Name] is building the first integrated ESG compliance + Supply Chain Risk Management platform purpose-built for mid-market companies (500–5,000 employees) globally.")
    add_body(doc, "The Problem: Mid-market companies face a tsunami of ESG compliance requirements from buyers, regulators, and frameworks — but they're still using Excel and email to manage it. The same data is entered 8–12 times per year in different formats.")
    add_body(doc, "The Solution: One platform that auto-maps data across frameworks (CSRD, ISSB, GRI, TCFD), collects supplier data via messaging apps (WhatsApp/LINE/WeChat), monitors supply chain risk in real-time, and translates everything into CFO-ready ROI metrics.")
    add_body(doc, "The Ask: $1.5–2.5M seed round to reach 30–50 customers in 18 months.")

    # ---- 2. THE PROBLEM ----
    doc.add_page_break()
    add_heading(doc, "2. The Problem", level=1)

    add_heading(doc, "The Compliance Cascade", level=2)
    add_body(doc, "EU regulations (CSRD, CSDDD, EUDR, CBAM) now require companies to report ESG data AND ensure their suppliers meet ESG standards. This creates a compliance cascade — a mid-market garment factory in Bangladesh must now report to H&M, Zara, Primark, C&A, and Marks & Spencer, each with different formats and frameworks.")

    add_heading(doc, "How Companies Handle It Today", level=2)
    add_styled_table(doc, ["Method", "% of Companies", "Cost"], [
        ["Excel + Email", "70–80%", "40–60 hours per cycle, poor data quality, no audit trail"],
        ["Consultant + PowerPoint", "15–20%", "$10–30K per report, static, no year-over-year continuity"],
        ["Point Solutions (EcoVadis, CDP)", "5–10%", "$5–15K per tool, fragmented, no unified view"],
        ["Nothing", "5–10%", "Risk of losing major buyer contracts"],
    ])

    add_heading(doc, "Not One Questionnaire — Ten", level=2)
    add_body(doc, "A typical garment factory receives 8–12 buyer questionnaires per year, each requesting the same ESG data in different formats. H&M sends an Excel template in January. Zara sends a web portal link in February. Primark sends a PDF in March. The same data — emissions, water usage, labor practices — is re-entered from scratch each time.")

    # ---- 3. OUR SOLUTION ----
    doc.add_page_break()
    add_heading(doc, "3. Our Solution", level=1)
    add_body(doc, "An integrated ESG + SCRM platform with 9 core capabilities:")

    solutions = [
        ("1. ESG Data Orchestration Platform", "A mapping engine that takes one internal KPI and outputs it across multiple frameworks (CSRD, ISSB, GRI, TCFD). One data entry, multiple framework outputs."),
        ("2. Supply-Chain ESG Data Collection", "Automated supplier questionnaires and data feeds for Scope 3 emissions. Suppliers respond via WhatsApp/LINE/WeChat — not email portals."),
        ("3. Assurance-Ready Evidence Vault", "Full audit trail with data lineage. Every number tagged with source, methodology, and confidence level. Big 4 auditors can verify without manual evidence gathering."),
        ("4. ESG ROI Engine", "Translates ESG activities into financial metrics — cost savings, risk reduction, brand value. CFOs see ROI, not just compliance cost."),
        ("5. Mid-Market ESG Reporting in a Box", "Turnkey solution for companies that can't afford Persefoni or Watershed. 3–6 week implementation vs 3–6 months."),
        ("6. Real-Time ESG Monitoring (NEW)", "Live sustainability command center connecting to existing IoT sensors and ERP systems. Real-time emissions, energy, and resource monitoring with threshold alerts. Mid-market export manufacturers already have smart meters, PLC-controlled lines, and building management systems — we read existing sensor data through ERP integrations."),
        ("7. AI Sustainability Copilot (NEW — 3-6 months)", "Conversational AI that auto-fills questionnaires, generates ESG policies, suggests improvements, and provides step-by-step roadmaps. Ask 'How do I improve from score 62 to 75?' and get an actionable plan."),
        ("8. Supplier Intelligence Graph (NEW — 3-6 months v1)", "Independent supplier risk intelligence using news APIs, sanctions lists (OFAC, EU), trade data, and ESG violation databases. Independent truth vs declared truth — the score doesn't depend on supplier self-reporting."),
        ("9. Supplier ESG-Risk Scorecard (SCRM Layer)", "Buyers assess, monitor, and score suppliers on ESG + disruption risk + financial health + geopolitical risk. Integrated with procurement workflows."),
    ]
    for title, desc in solutions:
        add_body(doc, title, bold=True)
        add_body(doc, desc)

    # ---- 4. TECHNICAL OVERVIEW ----
    doc.add_page_break()
    add_heading(doc, "4. Technical Overview", level=1)

    add_heading(doc, "Emission Calculation Methods", level=2)
    add_styled_table(doc, ["Method", "How It Works", "Confidence"], [
        ["Direct Measurement", "Physical meter or sensor reading", "HIGH"],
        ["Activity-Based Calculation", "Activity data × published emission factor", "MEDIUM"],
        ["Spend-Based Estimate", "Financial spend × industry emission factor", "LOW"],
    ])
    add_body(doc, "The tool always uses the best available method. Every data point is tagged with method, source, and confidence level. Emission factor databases: GHG Protocol, DEFRA, IPCC, EPA, IEA, Ecoinvent.")

    add_heading(doc, "ERP Integrations", level=2)
    add_styled_table(doc, ["System", "Use Case"], [
        ["SAP S/4HANA", "Enterprise ERP — procurement, finance, utility data"],
        ["SAP ECC", "Legacy SAP installations"],
        ["SAP Business One", "Mid-market ERP — primary target"],
        ["Oracle", "Enterprise financials + procurement"],
        ["NetSuite", "Cloud ERP for mid-market"],
        ["Xero", "SME accounting — entry point"],
    ])

    add_heading(doc, "HRIS Integrations", level=2)
    add_styled_table(doc, ["System", "Use Case"], [
        ["Workday", "Enterprise HR — diversity, headcount, compensation data"],
        ["BambooHR", "Mid-market HRIS"],
        ["ADP", "Payroll + workforce data"],
        ["Personio", "European mid-market HR"],
        ["Local HRIS per market", "Country-specific HR systems in target markets"],
    ])

    add_heading(doc, "Real-Time Monitoring Architecture", level=2)
    add_body(doc, "Mid-market export manufacturers already have IoT infrastructure: PLC-controlled production lines, smart energy meters, water flow meters, building management systems. The platform reads existing sensor data through the same ERP API pipelines used for batch reporting. No sensor installation required — just higher-frequency data pulls.")
    add_body(doc, "Alerts: threshold-based notifications (emissions exceeded, energy spike, water usage anomaly). Dashboard: live metrics alongside compliance data.")

    add_heading(doc, "Supplier Intelligence Architecture (v1)", level=2)
    add_body(doc, "v1 (3-6 months): English-language news APIs (GDELT, NewsAPI) + sanctions lists (OFAC, EU) + LLM sentiment analysis. Exact company name matching. Straightforward API integration.")
    add_body(doc, "Full version (12+ months): Multilingual news parsing (Bengali, Vietnamese, Thai, Hindi) + fuzzy entity resolution + trade data integration + financial distress signals.")

    # ---- 5. MARKET OPPORTUNITY ----
    doc.add_page_break()
    add_heading(doc, "5. Market Opportunity", level=1)

    add_heading(doc, "Regulatory Drivers", level=2)
    regs = [
        "CSRD (EU) — 50,000+ companies must report ESG data by 2025–2026",
        "CSDDD (EU) — Companies must ensure suppliers meet ESG standards (due diligence)",
        "EUDR (EU) — Deforestation-free supply chains for palm oil, soy, coffee, etc.",
        "CBAM (EU) — Carbon border adjustment — importers pay for embedded carbon",
        "ISSB (Global) — International Sustainability Standards Board baseline",
        "SEC Climate Disclosure (US) — Climate risk reporting for US-listed companies",
    ]
    for r in regs:
        add_bullet(doc, r)

    add_heading(doc, "Consumer ESG Demand", level=2)
    add_styled_table(doc, ["Source", "Finding"], [
        ["PwC", "76% prefer ESG-focused companies. Willing to pay 9.7% premium"],
        ["NielsenIQ", "73% would change habits to reduce environmental impact"],
        ["Deloitte", "1 in 3 chose a more sustainable brand. Cost-of-living didn't kill ESG"],
        ["McKinsey", "66–80% willing to pay more for sustainable products"],
    ])

    add_heading(doc, "Priority Target Markets", level=2)
    add_styled_table(doc, ["Priority", "Market", "Why"], [
        ["1", "Bangladesh (garments)", "4,000+ factories, all exporting to EU, receiving ESG questionnaires today"],
        ["2", "Vietnam (textiles + electronics)", "EU top export market. EUDR + CSDDD creating demand"],
        ["3", "India (pharma + auto + IT)", "Largest number of mid-market companies. EU + US pressure"],
        ["4", "Thailand (auto + food)", "Automotive supply chain to EU/Japan"],
        ["5", "Indonesia (palm oil + textiles)", "EUDR is existential — comply or lose EU access"],
    ])

    # ---- 6. COMPETITIVE LANDSCAPE ----
    doc.add_page_break()
    add_heading(doc, "6. Competitive Landscape", level=1)
    add_styled_table(doc,
        ["", "This Startup", "Sweep", "EcoVadis", "Persefoni", "Resilinc"],
        [
            ["ESG Reporting", "Yes", "Yes", "No", "Yes", "No"],
            ["Supply Chain Risk", "Yes", "No", "Partial", "No", "Yes"],
            ["Real-Time Monitoring", "Yes", "No", "No", "No", "Partial"],
            ["AI Copilot", "Planned (3-6 mo)", "No", "No", "No", "No"],
            ["Supplier Intelligence", "Planned (3-6 mo)", "No", "Self-reported only", "No", "Partial"],
            ["Mid-Market Focus", "Yes", "No", "Partial", "No", "No"],
            ["Messaging-Native Collection", "Yes", "No", "No", "No", "No"],
            ["ROI Engine", "Yes", "No", "No", "No", "No"],
            ["Target Buyer", "CFO/COO", "CSO", "Procurement", "CSO", "Supply Chain"],
            ["Funding", "$0 (raising)", "$100M+", "$500M+", "$100M+", "$100M+"],
        ]
    )

    # ---- 7. BUSINESS MODEL ----
    doc.add_page_break()
    add_heading(doc, "7. Business Model", level=1)

    add_heading(doc, "Pricing Tiers", level=2)
    add_styled_table(doc, ["Tier", "Customer", "Price", "Includes"], [
        ["Mid-Market", "500–5,000 employees", "$24–60K/year ($2-5K/month)", "Full platform + 1 ERP integration + messaging supplier collection"],
        ["Enterprise Division", "Division of large enterprise", "$60–150K/year", "Full platform + multiple integrations + dedicated support + SCRM"],
        ["Premium Add-Ons", "Any tier", "+$10-30K/year", "AI Copilot, Supplier Intelligence Graph, advanced analytics"],
    ])

    add_heading(doc, "Unit Economics (Target)", level=2)
    add_styled_table(doc, ["Metric", "Target"], [
        ["Gross Margin", "80%+"],
        ["LTV:CAC Ratio", "3:1+"],
        ["Net Revenue Retention", "110%+"],
        ["Payback Period", "6–12 months"],
    ])

    add_heading(doc, "Future Revenue Streams (Year 2+)", level=2)
    future = [
        "Supplier network monetization — Suppliers pay to get rated, benchmark, and improve (EcoVadis model)",
        "Data monetization — Industry benchmarks, anonymized reports, API access for investors/consultants",
        "Premium modules — AI Copilot, Supplier Intelligence Graph, advanced integrations as paid add-ons",
    ]
    for f in future:
        add_bullet(doc, f)

    # ---- 8. GO-TO-MARKET ----
    doc.add_page_break()
    add_heading(doc, "8. Go-to-Market Strategy", level=1)
    add_body(doc, "Option C: Run mid-market (70%) and enterprise division-level (30%) simultaneously.")

    add_heading(doc, "Track 1: Mid-Market (70%)", level=2)
    add_bullet(doc, "Target: 30–50 customers in 18 months")
    add_bullet(doc, "Buyer: CFO / COO")
    add_bullet(doc, "Deal size: $24–60K/year")
    add_bullet(doc, "Sales cycle: 4–8 weeks")
    add_bullet(doc, "Entry: Compliance filing (CSRD) → expand to SCRM + ROI Engine")

    add_heading(doc, "Track 2: Enterprise Division-Level (30%)", level=2)
    add_bullet(doc, "Target: 1–2 division deals in 18 months")
    add_bullet(doc, "Buyer: VP Operations / Division CFO")
    add_bullet(doc, "Deal size: $60–100K/year")
    add_bullet(doc, "Sales cycle: 3–6 months")
    add_bullet(doc, "Why division-level: Unilever has 400+ brands. One division is a 2,000-person company with its own budget. Same logo, 4x faster cycle.")

    add_heading(doc, "Classic Precedents", level=2)
    add_styled_table(doc, ["Company", "Started As", "Displaced"], [
        ["Salesforce", "SMB CRM (cheap, fast, cloud)", "Siebel (enterprise, on-premise)"],
        ["HubSpot", "Small business marketing", "Marketo, Eloqua"],
        ["Zoom", "Small team video calls", "Cisco WebEx, Skype"],
        ["Datadog", "Startup infrastructure monitoring", "HP OpenView, BMC"],
    ])

    # ---- 9. TEAM ----
    doc.add_page_break()
    add_heading(doc, "9. Team", level=1)
    add_body(doc, "[Founders] — Three co-founders with complementary expertise:")
    team = [
        "Business / Strategy lead — [Name, background]",
        "Technical co-founder — [Name, enterprise SaaS experience, 4-year vesting with 1-year cliff]",
        "ESG domain expert — [Name, ESG regulatory knowledge, builds knowledge base for AI Copilot and Supplier Intelligence scoring]",
    ]
    for t in team:
        add_bullet(doc, t)

    # ---- 10. 90-DAY PLAN ----
    add_heading(doc, "10. 90-Day Milestone Plan", level=1)
    add_styled_table(doc, ["Period", "Milestone", "Success Metric"], [
        ["Days 1–30", "MVP launch with core features: Data Orchestration + ERP integration + Real-Time Monitoring + supplier messaging collection", "1 ERP integration live, platform deployed"],
        ["Days 30–60", "Onboard first 3 pilot customers from Bangladesh garments", "3 pilot contracts signed, weekly active usage"],
        ["Days 60–90", "Close 2 paying customers + begin AI Copilot development + begin Supplier Intelligence Graph v1", "2 paying customers ($2-5K/month), product roadmap validated"],
    ])

    add_heading(doc, "18-Month Roadmap", level=2)
    add_styled_table(doc, ["Period", "Focus", "Features"], [
        ["Months 1–6", "Core platform + market entry", "ERP integrations, framework mapping, real-time monitoring, supplier messaging, ROI Engine"],
        ["Months 6–12", "AI layer + market expansion", "AI Copilot, Supplier Intelligence Graph v1, Vietnam + India market entry"],
        ["Months 12–18", "Enterprise push + intelligence expansion", "Multilingual supplier intelligence, enterprise features, supplier network monetization pilot"],
    ])

    # ---- 11. THE ASK ----
    doc.add_page_break()
    add_heading(doc, "11. The Ask", level=1)
    add_styled_table(doc, ["", ""], [
        ["Raise", "$1.5–2.5M seed round"],
        ["Use of Funds", "40% engineering (product build), 30% sales & marketing (customer acquisition), 20% operations (infrastructure + integrations), 10% working capital"],
        ["Runway", "18 months"],
        ["Target", "30–50 customers, $1M+ ARR"],
        ["Valuation", "$8–10M pre-money (Tier 1 milestones met)"],
    ])

    add_heading(doc, "Investment Tiers", level=2)
    add_styled_table(doc, ["Tier", "Milestones", "Investment", "Valuation"], [
        ["Tier 1 — Take My Money", "5 customers, $2-5K/month ACV, 3+ inbound, weekly usage, 1+ renewal", "$2M seed", "$8-10M pre-money"],
        ["Tier 2 — Come Back in 6 Mo", "5 customers, warm network, low ACV, high churn risk", "$500K-1M pre-seed", "$3-4M pre-money"],
        ["Tier 3 — No Thanks", "None mid-market, no integration, not using SCRM", "No investment", "—"],
    ])

    # ---- 12. WHY NOW ----
    add_heading(doc, "12. Why Now", level=1)
    why_now = [
        "CSRD compliance deadlines hit 2025–2026 — companies need a solution NOW, not in 2 years",
        "Mid-market gap is real — Sweep, Persefoni, and Watershed all target enterprise. Nobody is purpose-building for 500–5,000 employee companies",
        "ESG + SCRM combined is structurally unique — no competitor does both in one platform",
        "18-month window before well-funded incumbents move down-market",
        "Consumer demand confirms structural tailwind — 76–80% prefer ESG-focused companies",
        "Asian mid-market is underserved — Bangladesh, Vietnam, India, Thailand, Indonesia have thousands of companies facing EU compliance for the first time",
        "IoT infrastructure exists — mid-market manufacturers already have sensors, smart meters, and PLC lines. Real-time monitoring is a software problem, not a hardware problem",
    ]
    for w in why_now:
        add_bullet(doc, w)

    add_body(doc, "")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("The founders have 90 days. The clock is ticking.")
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x1B, 0x43, 0x32)

    doc.save("/Users/kshitijverma/Desktop/Class Notes/Term 4/Machine Learning For Decision Making/ESG SCRM/INVESTOR_PREREAD.docx")
    print("INVESTOR_PREREAD.docx saved.")


# ============================================================
# RUN BOTH
# ============================================================

if __name__ == "__main__":
    create_pitch_analysis()
    create_investor_preread()
    print("Both documents created successfully.")
