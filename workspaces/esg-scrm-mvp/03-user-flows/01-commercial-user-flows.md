# User Flow: Factory CFO — H&M Scope 3 Compliance

## Persona

Rahim, CFO at Bangladesh Export Textiles Ltd. (2,000 employees, $50M revenue). Exports to H&M. Received letter from H&M requiring Scope 3 data within 6 months for contract renewal. No ESG staff. Uses WhatsApp daily. SAP Business One on premise.

## Flow 1: First Login + Factory Setup

### Step 1: Registration

- Rahim receives invitation link from sales team (or self-registers at app.esgscrm.com)
- Enters: name, email, password (minimum 8 chars, upper+lower+digit)
- Selects: organization name, industry (Garment/Textile), country (Bangladesh), number of employees
- System creates organization with default settings for Bangladesh garment sector
- **What Rahim sees**: "Welcome to ESG SCRM. Your organization is set up for Bangladesh garment manufacturing. Pre-configured with H&M ESR questionnaire template."

### Step 2: Dashboard Tour

- Dashboard loads with 5 tabs: Dashboard | Supply Chain | Risk & Alerts | Frameworks | Engagement
- All panels show empty state with clear CTAs: "Upload your energy data to get started"
- **Value delivered**: Rahim sees the product is real and configured for his industry

### Step 3: Data Upload

- Rahim clicks "Upload Data" on Dashboard
- Sees upload form with template download link: "Download CSV template for Bangladesh garment factories"
- Template has pre-filled column headers: date, factory_id, energy_kwh, water_m3, diesel_liters, co2_tonnes, waste_kg, headcount
- Rahim's finance team fills template with 3 months of utility bill data
- Uploads CSV → system validates columns → imports data → dashboard populates with real metrics
- **Value delivered**: Rahim sees HIS factory's energy consumption on the dashboard, not demo data

### Step 4: Emission Factor Application

- System auto-detects country (Bangladesh) from organization settings
- Applies Bangladesh-specific emission factors from GHG Protocol database
- Shows Rahim: "Your 3-month data: 450 tonnes CO2e (Scope 1: 180t, Scope 2: 270t). Based on Bangladesh grid emission factor 0.67 tCO2e/MWh."
- **Value delivered**: Rahim has a defensible Scope 1+2 number with cited emission factors

## Flow 2: Supplier Scope 3 Collection

### Step 5: Import Supplier List

- Rahim navigates to Supply Chain tab
- Clicks "Import Suppliers"
- Uploads CSV with: supplier_name, contact_name, phone_number, product_category, annual_spend_usd
- System imports 140 suppliers, auto-categorizes by spend (Tier 1: top 20 by spend = 80% of procurement)
- Shows: "20 Tier 1 suppliers identified. These represent 80% of your procurement spend and ~80% of your Scope 3 emissions."

### Step 6: Send WhatsApp Questionnaires

- Rahim navigates to Engagement tab
- Sees supplier list sorted by spend (highest first)
- Clicks "Send Questionnaire" → selects top 20 Tier 1 suppliers
- System shows preview: "You are about to send an ESG questionnaire to 20 suppliers via WhatsApp. The questionnaire is in Bengali and covers: energy use, water use, waste management, labor practices."
- Rahim confirms → system sends via WhatsApp Business API
- **Value delivered**: Rahim has initiated Scope 3 data collection in 5 minutes, not 3 weeks of manual emails

### Step 7: Monitor Responses

- Dashboard shows real-time response tracking: "8/20 suppliers responded (40%). Coverage: 65% of spend."
- Rahim can see which suppliers responded, which haven't
- For non-responders: "Send reminder" button → sends follow-up WhatsApp message
- **Value delivered**: Rahim knows exactly where his Scope 3 coverage stands, can chase non-responders

### Step 8: Review Supplier Data

- Rahim clicks on a responded supplier → sees structured ESG data
- Energy consumption, water use, waste data — all parsed from WhatsApp responses
- Confidence level shown: "HIGH" (supplier provided monthly data), "MEDIUM" (estimated from annual), "LOW" (incomplete response)
- **Value delivered**: Supplier ESG data is structured and confidence-tagged, not raw chat messages

## Flow 3: H&M Compliance Report

### Step 9: Generate Framework Report

- Rahim navigates to Frameworks tab
- Selects "H&M ESR Format" from dropdown
- System maps his factory data + supplier data to H&M's required format
- Shows preview: Scope 1: 720t CO2e, Scope 2: 1,080t CO2e, Scope 3: 2,340t CO2e (based on 20 suppliers, 65% spend coverage)
- **Value delivered**: Rahim has a complete emissions profile in H&M's format

### Step 10: Export Evidence Package

- Rahim clicks "Export for Audit"
- System generates PDF with:
  - Executive summary (emissions by scope)
  - Methodology statement (emission factors, calculation approach)
  - Per-metric evidence chain (source → calculation → reported value → confidence)
  - Supplier coverage statement (20/140 suppliers, 65% of spend)
  - Hash chain integrity verification
- **Value delivered**: Rahim has a document he can hand to H&M or an auditor

### Step 11: Submit to H&M

- Rahim downloads the PDF + Excel data file
- Emails to H&M's ESR team (or uses H&M's supplier portal to upload)
- **Value delivered**: Contract renewal requirement met. $40M revenue protected.

## Flow 4: Ongoing Monitoring (Year 1)

### Step 12: Monthly Data Upload

- Finance team uploads monthly CSV (same template)
- Dashboard updates with trend: "April emissions: 12% below target"
- Threshold alerts fire if emissions exceed configured limits
- **Value delivered**: Rahim has ongoing visibility, not just a one-time report

### Step 13: Quarterly Supplier Re-survey

- System sends quarterly WhatsApp questionnaire to suppliers
- Tracks response rate trends: "Q2 response rate: 55% (up from 40% in Q1)"
- **Value delivered**: Scope 3 data improves over time, not just a snapshot

---

# User Flow: Supplier — WhatsApp Questionnaire Response

## Persona

Karim, owner of Karim Dyeing Works (80 employees, supplies dyeing services to Bangladesh Export Textiles). Speaks Bengali. Uses WhatsApp on Android phone. No ESG knowledge. No desktop computer at factory.

## Flow

### Step 1: Receive WhatsApp Message

- Karim receives WhatsApp message from verified business account: "Bangladesh Export Textiles Ltd. requests ESG data for their H&M compliance. Please respond to 5 questions. Takes 2 minutes. বাংলায় দেখুন [See in Bengali]"
- Karim taps "বাংলায় দেখুন"
- **What Karim sees**: Bengali-language message with 5 simple questions

### Step 2: Respond to Questions

- Q1: "আপনার কারখানায় গত মাসে কত ইউনিট বিদ্যুৎ খরচ হয়েছে? [How many units of electricity did your factory consume last month?]"
- Karim types: "১২০০০" (12000 in Bengali numerals) or "12000"
- Q2: "পানি খরচ (ঘনমিটার)? [Water consumption (cubic meters)?]"
- Karim types: "450"
- Q3: "বর্জ্য পদার্থ কিভাবে নিষ্পত্তি করা হয়? [How is waste disposed?]" — Multiple choice: পুনর্ব্যবহার [Recycle] / ল্যান্ডফিল [Landfill] / অন্যান্য [Other]
- Karim taps: "পুনর্ব্যবহার"
- Q4: "কতজন শ্রমিক কাজ করেন? [How many workers are employed?]"
- Karim types: "80"
- Q5: "আপনার কারখানায় কি পরিবেশগত লাইসেন্স আছে? [Does your factory have an environmental license?]"
- Karim taps: "হ্যাঁ [Yes]"
- **Value delivered**: Karim completed ESG questionnaire in 2 minutes without leaving WhatsApp, without creating an account, without understanding what ESG means

### Step 3: Confirmation

- System sends confirmation: "ধন্যবাদ! আপনার তথ্য গৃহীত হয়েছে। [Thank you! Your data has been received.] Bangladesh Export Textiles Ltd. আপনার সহযোগিতার জন্য কৃতজ্ঞ। [is grateful for your cooperation.]"
- **Value delivered**: Karim knows his response was received, doesn't need to follow up

---

# User Flow: Auditor — Evidence Verification

## Persona

Sarah, senior associate at EY Dhaka. Conducting H&M supply chain ESG audit for Bangladesh Export Textiles Ltd.

## Flow

### Step 1: Receive Audit Access

- Sarah receives an email from ESG SCRM: "Bangladesh Export Textiles Ltd. has granted you auditor access. Click to view evidence."
- Sarah clicks link → logs in with email → sees read-only auditor dashboard
- **What Sarah sees**: Organization overview, reporting period, total emissions by scope, data completeness score

### Step 2: Verify Evidence Chain

- Sarah navigates to a specific metric: "Scope 2 electricity: 1,080 tCO2e"
- Sees evidence chain:
  - Source: "CSV upload, 2026-04-15, uploaded by Rahim Ahmed (CFO)"
  - Raw data: "12,450 kWh, April 2026"
  - Emission factor: "Bangladesh grid, 0.67 tCO2e/MWh, GHG Protocol 2024"
  - Calculation: "12,450 × 0.67 / 1000 = 8.34 tCO2e"
  - Confidence: HIGH (actual meter reading + verified emission factor)
  - Hash: SHA-256 chain verification: ✓ INTEGRITY VERIFIED
- **Value delivered**: Sarah can verify the calculation in 30 seconds, not 3 days of requesting documents

### Step 3: Export Audit Package

- Sarah clicks "Export Full Audit Package"
- Downloads ZIP containing:
  - Executive summary PDF
  - Per-metric evidence with hash chain
  - Emission factor references with source citations
  - Supplier coverage methodology
  - Raw data files (CSV)
- **Value delivered**: Sarah has a complete, organized audit package instead of 400 pages of disorganized documents

---

# User Flow: Factory Manager — Real-Time Monitoring

## Persona

Ali, operations manager at Bangladesh Export Textiles. Responsible for daily production. Has a smartphone but doesn't use the ESG platform — gets alerts via WhatsApp.

## Flow

### Step 1: Threshold Alert

- Ali receives WhatsApp alert: "⚠️ Energy consumption alert: Factory floor 2 exceeded daily target by 18% (4,200 kWh vs 3,500 kWh target). Check air conditioning units."
- Ali walks to floor 2, finds AC running in empty loading bay
- Turns off AC → next reading drops below threshold
- **Value delivered**: Ali caught an energy waste event the same day, not at month-end

### Step 2: Weekly Summary

- Every Monday, Ali receives WhatsApp summary: "Last week: 28,000 kWh (5% below target). Best day: Thursday. Worst day: Saturday (overtime shift). Water: on target. No alerts."
- **Value delivered**: Ali has operational visibility without logging into a dashboard
