---
name: discovery-four-ai-use-cases-layered
description: AI in ESG SCRM has four use cases with different economics — only anomaly detection belongs in core
type: DISCOVERY
date: 2026-05-07
created_at: 2026-05-07T00:00:00Z
author: agent
session_id: esg-scrm-mvp
session_turn: 1
project: esg-scrm-mvp
topic: marketing AI layer categorization
phase: analyze
tags: [ai-layer, marketing-ai, evidence-generation, buyer-intelligence]
---

# DISCOVERY: Four AI use cases in ESG SCRM with distinct economic models

## What was found

Analysis of "can we add a complementary marketing AI layer" revealed four distinct AI use cases in the ESG SCRM context, each with a different economic model and different embedding path:

| Use Case                                        | Economic Model                                | Embedding                              |
| ----------------------------------------------- | --------------------------------------------- | -------------------------------------- |
| Buyer ESG Intelligence (H&M ESR change tracker) | Marketing — generates qualified leads         | Public web property, no login required |
| Evidence Package Generation                     | Premium add-on — justifies $5–10K/year uplift | Inside Feature 3 (Evidence Vault)      |
| Questionnaire Auto-Completion                   | Core — makes Feature 2 viable at scale        | Inside Feature 2 (Supplier Collection) |
| Anomaly Detection + Alert Triage                | Core — operational safeguard                  | Inside Feature 2 (operational layer)   |

**The non-obvious finding**: The brief's "AI Copilot" was deferred as a single concept. In practice, AI has four distinct uses, only one of which belongs in the core product (anomaly detection). The other three are marketing assets or premium upsells. Bundling them as "AI Copilot" conflates uses with different buyers, different price points, and different integration paths.

**The second non-obvious finding**: Evidence Package Generation is the highest-immediate-ROI AI feature for the sustainability team, but it is also the highest legal risk — the LLM-generated narrative becomes part of an auditor-submitted evidence package. If the narrative is wrong, the auditor relies on it. The LLM must not generate factual claims about supplier data that have not been verified by a human. The constraint: AI generates the narrative structure, not the underlying data assertions.

## For Discussion

1. **Counterfactual**: What if the AI layer is the primary product, and Features 1–4 are the data sources that feed it? Does the marketing story change if the pitch is "AI-powered Scope 3 supplier intelligence" rather than "ESG compliance platform"?

2. **Scope**: The evidence package generation AI creates legal exposure if the LLM hallucinate data point values. What is the minimal human-review gate that makes this safe to ship? (Options: AI generates draft, human reviews before submission; AI generates only non-numerical narrative; AI is disallowed from generating content that enters the evidence chain)

3. **Revenue model**: The buyer ESG intelligence (H&M change tracker) is a marketing asset with no direct revenue. At what point does it become a product? Does it make sense to charge factories for access to the H&M ESR change tracker as a standalone subscription ($500/month)?
