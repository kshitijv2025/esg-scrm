# Spec 02: Supply-Chain ESG Data Collection

## What This Module Does

Automates supplier questionnaires for Scope 3 emissions. Suppliers receive questions via WhatsApp/LINE/WeChat and respond without leaving the messaging app. Data flows directly into Scope 3 calculations.

## Core Architecture

```
Platform → QuestionnaireEngine → MessagingGateway → Supplier (WhatsApp/LINE/WeChat)
                  ↑                                              ↓
                  └────────────── Scope 3 Calculator ←──────────┘
```

## Questionnaire Engine

### Questionnaire Flow

1. **Template Import** — Buyer uploads or selects a questionnaire template (H&M format, EcoVadis format, or custom)
2. **Supplier Selection** — Buyer selects which suppliers receive the questionnaire
3. **Localization** — Questions are translated to supplier's preferred language
4. **Channel Selection** — System picks best channel based on supplier's preferred_contact
5. **Dispatch** — Questions sent via WhatsApp/LINE/WeChat with numbered response format
6. **Response Collection** — Supplier replies are parsed, confidence tagged, stored
7. **Follow-Up** — Unanswered questions get automated reminders at Day 3, Day 7, Day 14
8. **Validation** — Buyer reviews responses, flags anomalies, approves
9. **Scope 3 Calculation** — Approved responses feed into Scope 3 DataPoints

### Question Routing

```
Supplier response (e.g., "2. 45000 kWh")
         ↓
NLUParser (Named List Understanding)
         ↓
Maps to: QuestionnaireQuestion(id=2, metric_type="energy_kwh")
         ↓
Confidence: HIGH if unit matches expected, MEDIUM if conversion needed, LOW if ambiguous
         ↓
Stored as: SupplierResponse
         ↓
Feed into: Scope3Calculator → DataPoint(scope3_category_1, confidence=SupplierResponse.confidence)
```

### Supported Response Formats

| Channel    | Format Supported                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------- |
| WhatsApp   | Numbered responses ("1. yes 2. 45000 kWh"), voice notes (transcribed), image attachments (certificates) |
| LINE       | Same as WhatsApp                                                                                        |
| WeChat     | Same as WhatsApp + Mini Program fallback                                                                |
| Email      | Structured reply with line items                                                                        |
| Web Portal | Form-based structured input                                                                             |

## Messaging Gateway

### Channel Abstraction Layer

```python
class MessagingGateway:
    async def send_questionnaire(
        questionnaire_id: UUID,
        supplier_id: UUID,
        questions: list[Question],
        channel: ENUM(whatsapp, line, wechat, email)
    ) → DispatchResult:

    async def receive_response(
        channel: ENUM(whatsapp, line, wechat, email),
        raw_message: str,
        message_metadata: dict
    ) → ParsedResponse:

    async def send_reminder(
        questionnaire_id: UUID,
        supplier_id: UUID,
        pending_questions: list[int],
        channel: ENUM(whatsapp, line, wechat, email)
    ) → None:
```

### WhatsApp Business API

Requirements:

- WhatsApp Business Account (WABA) — requires Facebook Business Manager verification
- Phone number (must be a real mobile, not VoIP)
- Message templates pre-approved by WhatsApp for outbound (reminders, alerts)
- Rate limit: 250 messages/customer/month on standard tier

Architecture:

```
Platform → WhatsApp Cloud API → Supplier WhatsApp
Platform ←Incoming Message Webhook← Supplier WhatsApp
```

Key challenges:

- Template messages require pre-approval for each template version
- Incoming messages only come from approved template message acknowledgments
- Two-way conversation requires template + free-form message combination
- **Recommended approach**: Use WhatsApp Business Solution Partner (BSP) like Twilio or MessageBird for easier compliance

### LINE (Thailand/Japan)

Requirements:

- LINE Official Account (OA) — must be verified for business messaging
- Messaging API channel — requires LINE Developer account
- Rich menu for structured response

Architecture:

```
Platform → LINE Messaging API → Supplier LINE
Platform ←Push API← Platform
```

Note: LINE has strict content policies. ESG questionnaire content must be reviewed.

### WeChat (China-only, deferred to v2)

Requirements:

- WeChat Official Account (订阅号 or 服务号)
- WeChat verification (requires Chinese business license)
- Mini Program for structured data collection

Note: WeChat integration is complex and requires a Chinese entity or partner. Deferred to v2.

## Localization

### Supported Languages (MVP)

| Language   | Code | Region     |
| ---------- | ---- | ---------- |
| English    | en   | Default    |
| Bengali    | bn   | Bangladesh |
| Vietnamese | vi   | Vietnam    |
| Thai       | th   | Thailand   |
| Hindi      | hi   | India      |
| Indonesian | id   | Indonesia  |

### Translation Approach

1. Questions stored with all language variants in `QuestionnaireQuestion`
2. At dispatch, system selects language based on supplier.country
3. Response parsing uses language-specific unit extraction (e.g., "แกลลอน" vs "gallons")

### Unit Normalization

Suppliers report in local units. System normalizes before storage:

| Reported Unit | Normalized To | Conversion    |
| ------------- | ------------- | ------------- |
| kWh           | kWh           | Direct        |
| MWh           | kWh           | × 1000        |
| gallons (US)  | m³            | × 0.00378541  |
| gallons (UK)  | m³            | × 0.00454609  |
| liter         | m³            | × 0.001       |
| kg CO2        | tCO2          | ÷ 1000        |
| lb CO2        | tCO2          | × 0.000453592 |

## Scope 3 Calculator

### Supplier Response → Scope 3 DataPoint

```python
async def calculate_scope3_from_response(
    response: SupplierResponse,
    emission_factor: EmissionFactor
) → DataPoint:

    # Determine calculation method based on response quality
    if response.response_value.is_numeric and response.unit in STANDARD_UNITS:
        method = "activity_based"
        confidence = "HIGH"
    elif response.response_value.is_spend_based:
        method = "spend_based"
        confidence = "MEDIUM"
    else:
        method = "estimate"
        confidence = "LOW"

    value = convert_to_standard_unit(response.value, response.unit)
    tco2 = value * emission_factor.value

    return DataPoint(
        metric_type="scope3_category_1",
        value=tco2,
        calculation_method=method,
        confidence=confidence,
        upstream_data_points=[response.id]  # lineage
    )
```

### Response Rate Tracking

| Metric                 | Target             | Calculation                             |
| ---------------------- | ------------------ | --------------------------------------- |
| Response rate          | > 60%              | responses_received / questions_sent     |
| Complete response rate | > 80% of responded | complete_responses / responses_received |
| Time to first response | < 48 hours         | first_response_at - sent_at             |
| Time to complete       | < 14 days          | completed_at - sent_at                  |

### Fallback: Spend-Based Estimation

When supplier doesn't respond:

1. Use last known response (if available)
2. If no history, use industry benchmark × supplier spend
3. Flag as LOW confidence in Evidence Vault

```python
def estimate_scope3_supplier(
    supplier: Supplier,
    category: Scope3Category,
    last_response: SupplierResponse | None
) → DataPoint:
    if last_response:
        return last_response  # reuse with updated timestamp
    else:
        benchmark = get_industry_benchmark(supplier.industry, category)
        spend = get_supplier_spend_from_erp(supplier.id, category)
        return DataPoint(
            metric_type=category,
            value=spend * benchmark.emission_factor,
            calculation_method="spend_based",
            confidence="LOW",
            source="ERP spend + industry benchmark (no supplier response)"
        )
```

## Brief Traceability

| Brief Requirement                                              | Spec Section                                    |
| -------------------------------------------------------------- | ----------------------------------------------- |
| "Automated supplier questionnaires"                            | Questionnaire Engine, Questionnaire Flow        |
| "Suppliers respond via WhatsApp/LINE/WeChat"                   | Messaging Gateway, WhatsApp/LINE sections       |
| "Also support email and web portal as fallback"                | Supported Response Formats table                |
| "Calculate Scope 3 emissions from collected data"              | Scope 3 Calculator                              |
| "Localization in Bengali, Vietnamese, Thai, Hindi, Indonesian" | Localization section, Supported Languages table |
| "Automated follow-ups at Day 3, 7, 14"                         | Questionnaire Flow, send_reminder()             |
| "Mobile-first (suppliers checking WhatsApp)"                   | Channel Selection, Messaging Gateway            |
| "Target 60% supplier response rate"                            | Response Rate Tracking table                    |
| "LOW confidence when supplier doesn't respond"                 | Fallback: Spend-Based Estimation                |
