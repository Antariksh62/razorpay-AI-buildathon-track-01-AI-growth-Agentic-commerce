# Graph Report - razorpay-agent-buildathon  (2026-08-27)

## Corpus Check
- 16 files · ~9,612 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 122 nodes · 191 edges · 14 communities (10 shown, 4 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 32 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 13|Community 13]]

## God Nodes (most connected - your core abstractions)
1. `get_db_connection()` - 17 edges
2. `add_audit_log()` - 13 edges
3. `Razorpay Agentic Commerce — Bounded & Gated Autonomous Commerce Engine` - 10 edges
4. `getMandate()` - 8 edges
5. `evaluate_checkout_intent()` - 7 edges
6. `AI Agent Orchestrator` - 7 edges
7. `add_mandate_spend()` - 6 edges
8. `MandateConfig` - 6 edges
9. `search_merchant_catalog()` - 5 edges
10. `create_cart_quote()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `AI Agent Orchestrator` --uses--> `Declarative Policy Engine`  [INFERRED]
  backend/agent.py → README.md
- `Antigravity Declarative Policy Engine for Agentic Commerce.     Enforces bounded` --rationale_for--> `Declarative Policy Engine`  [EXTRACTED]
  backend/policy.py → README.md
- `AI Agent Orchestrator` --calls--> `Google GenAI SDK`  [INFERRED]
  backend/agent.py → backend/requirements.txt
- `get_catalog()` --calls--> `get_db_connection()`  [INFERRED]
  backend/main.py → backend/database.py
- `evaluate_catalog_search()` --calls--> `add_audit_log()`  [INFERRED]
  backend/policy.py → backend/database.py

## Communities (14 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.12
Nodes (11): React Split-Screen UI, Audit Console, Chat Interface, apiClient, getAuditLogs(), getCatalog(), refreshMandate(), revokeMandate() (+3 more)

### Community 1 - "Community 1"
Cohesion: 0.1
Nodes (22): AI Agent Orchestrator, AgentOrchestrator, create_cart_quote(), detect_and_correct_typo(), execute_razorpay_checkout(), Execute end-to-end Razorpay checkout using policy-gated intent mandate authoriza, Check stock and create a locked cart quote for single or multi-item checkout., Execute end-to-end Razorpay checkout using policy-gated intent mandate authoriza (+14 more)

### Community 2 - "Community 2"
Cohesion: 0.1
Nodes (19): 1. Backend Setup & Seeding, 1. Overview & Core Philosophy, 2. Frontend Setup & Launch, 2. Track 01 Problem Statement & Solution Mapping, 3. System Architecture Diagram, 4. End-to-End Transaction Flowchart, 5. Technical Stack & Component Map, 6. Built-In Edge Cases & Defensive Safeguards (+11 more)

### Community 3 - "Community 3"
Cohesion: 0.31
Nodes (15): add_audit_log(), add_mandate_spend(), get_active_mandate(), get_db_connection(), get_mandate(), init_db(), mark_mandate_used(), Cumulative spend update: adds approved transaction amount to current_spend_inr. (+7 more)

### Community 4 - "Community 4"
Cohesion: 0.2
Nodes (9): get_recent_audit_logs(), audit_stream(), fetch_audit_logs(), fetch_mandate(), get_catalog(), handle_chat(), on_startup(), Server-Sent Events (SSE) endpoint streaming real-time SQLite audit log updates t (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.33
Nodes (10): AuditLog, CatalogItem, ChatRequest, ChatResponse, CheckoutRequest, MandateConfig, MandateResponse, QuoteRequest (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.4
Nodes (5): DeclarativePolicyEngine, evaluate_cart_quote(), evaluate_catalog_search(), Antigravity Declarative Policy Engine for Agentic Commerce.     Enforces bounded, Declarative Policy Engine

## Knowledge Gaps
- **35 isolated node(s):** `Detects misspelled terms in user prompt and returns (misspelled_word, corrected_`, `Search the merchant catalog for available products matching a query, price ceili`, `Check stock and create a locked cart quote for single or multi-item checkout.`, `Execute end-to-end Razorpay checkout using policy-gated intent mandate authoriza`, `Orchestrates buyer interaction through dynamic catalog matching, typo auto-corre` (+30 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_db_connection()` connect `Community 3` to `Community 0`, `Community 1`, `Community 4`?**
  _High betweenness centrality (0.161) - this node is a cross-community bridge._
- **Why does `getMandate()` connect `Community 3` to `Community 0`, `Community 5`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `MandateConfig` connect `Community 5` to `Community 0`, `Community 3`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `get_db_connection()` (e.g. with `search_merchant_catalog()` and `create_cart_quote()`) actually correct?**
  _`get_db_connection()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `add_audit_log()` (e.g. with `execute_razorpay_checkout()` and `.process_prompt()`) actually correct?**
  _`add_audit_log()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `getMandate()` (e.g. with `evaluate_checkout_intent()` and `updateMandate()`) actually correct?**
  _`getMandate()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Detects misspelled terms in user prompt and returns (misspelled_word, corrected_`, `Search the merchant catalog for available products matching a query, price ceili`, `Check stock and create a locked cart quote for single or multi-item checkout.` to the rest of the system?**
  _35 weakly-connected nodes found - possible documentation gaps or missing edges._