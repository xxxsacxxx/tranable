# Tranable — Freight Operating Platform (MVP build)

This is the first working slice of the platform described in the two project PRDs:
**Enquiry-to-Delivery** (quote → order → booking → documents → delivery) and, not yet built,
**Invoice Reconciliation & Demurrage/Claims**. It follows the layered architecture in
`arch2.png` (the Quantiv platform architecture) as closely as makes sense for a single
first build, without standing up the full harness (no Kafka/Temporal/vector DB/multi-tenant
infra yet — see "What's deliberately stubbed" below).

## What's built

The full **enquiry-to-delivery loop works end to end** with real, seeded reference data:

1. Paste a free-text customer enquiry (email/WhatsApp/portal-style text).
2. The AI Gateway extracts a structured shipment requirement (origin, destination, mode,
   equipment, incoterm, ready date, cargo description...) and flags what's **known /
   inferred / missing**.
3. Cargo description is classified against an HS-code candidate list with confidence scores.
4. Origin/destination cities are normalized to the actual port/airport gateway used for
   rate lookup (OD normalization).
5. A deterministic pricing engine prices **Cheapest / Fastest / Recommended** options from
   seeded rate cards, with a full cost breakdown and win probability.
6. A grounded quote email is drafted automatically.
7. Approving an option converts the quote into an **Order + Shipment**, generates a
   **dynamic document checklist** from destination trade rules (e.g. Certificate of Origin
   required for UAE ceramics import), and creates an operations task to book the carrier.
8. Recording shipment milestones (booking confirmed, departed, arrived, delivered...)
   advances a shipment stage state machine and fires grounded customer-update emails.
9. Every AI Gateway call — extraction, HS classification, trade-rule lookup, email drafting —
   is logged to an **AI decision audit trail** (model, confidence, facts, inferences,
   evidence, recommended action) visible on both the quote and shipment screens.
10. A **Control Tower** dashboard rolls this up: quote pipeline value, shipment stages, open
    exceptions (e.g. `NO_RATE_AVAILABLE` when a lane has no rate card), touchless-shipment rate.

Two of the PRD's own worked examples run correctly out of the box (see "Try it" below).

## How this maps to the architecture diagram

| Architecture layer | In this build |
|---|---|
| **Engagement Layer** | Next.js frontend (`frontend/`) + REST API (`backend/app/api/`). Portals/MCP/agent-to-agent are out of scope for this build. |
| **Orchestration & Case Management** | `OrderAgent` (`backend/app/agents/order_agent.py`) owns quote/shipment state, stage transitions (`EVENT_STAGE_MAP`), and task generation. No durable workflow engine (Temporal) yet — state lives in Postgres and transitions are synchronous. |
| **Agentic Layer — Domain Agents** | `OrderAgent` = the diagram's "Order Agent: quote → booking". |
| **Agentic Layer — Shared Capability Services** | Document checklist (`brain/rules/document_checklist.py`), Email drafting (`ai_gateway`'s `customer_email` task). Voice and generic Retrieval are not built. |
| **The Brain — Rules & Policy** | `backend/app/brain/rules/`: deterministic quote/pricing calculation, OD normalization, document-requirement rules, demurrage/free-time math. Explicitly kept out of AI per both PRDs. |
| **The Brain — Knowledge (RAG)** | Not built — the `TradeRule` table stands in for a small seeded rule set rather than a real knowledge base/vector store. |
| **The Brain — Precedent** | `AIDecision` table is the start of this (every AI call + its outcome is recorded); no feedback/promotion-into-rules loop yet. |
| **Data Foundation** | Postgres via SQLAlchemy (`backend/app/models/`) — case store (Quote/Order/Shipment), evidence store (Document), reference data (Country/Location/Carrier/RateCard/TradeRule/HSCode), audit log (AuditLog + AIDecision). |
| **Integration & Ingestion** | Manual text paste stands in for document/email ingestion; no EDI/carrier-API/customs connectors. |
| **Control & Governance / Observability / Security** | Partially present: every AI call is logged with model/confidence/evidence (governance + observability groundwork). No model-gateway routing tiers, no RBAC/tenancy/SSO yet — this build is single-tenant, no auth. |

## What's deliberately stubbed (and how to tell)

Per the build decision made at kickoff, the **AI Gateway interface is real, but every task
handler behind it is a deterministic heuristic**, not a live model call — every `AIDecision`
row records `model: "stub-heuristic-v1"` (or `deterministic-rules-engine` for pure rule
lookups) so it's always visible in the audit trail which decisions came from a real model.
Swapping in a real Claude call means implementing `AIGateway._call_model` and the relevant
`_task_*` methods in `backend/app/brain/ai_gateway/gateway.py` — every caller (`OrderAgent`,
`document_checklist.py`) and the audit trail stay unchanged, by design.

Not built in this pass: authentication/RBAC, multi-tenancy, carrier/customs API integrations,
email ingestion (paste-text stands in for it), booking automation with real carriers, PDF
quote/document generation, and the Invoice Reconciliation & Demurrage/Claims workflow from
the other PRD (the rules engine already has a `demurrage.py` free-time/LFD calculator ready
for that build).

## Repository layout

```
tranable/
  backend/
    app/
      models/        Data Foundation: SQLAlchemy models (reference, customer, quote, shipment, documents, events, audit)
      brain/
        rules/        Deterministic engines: quote_calc, od_normalization, document_checklist, demurrage
        ai_gateway/    AIGateway — the single AIService.generate(task, context) interface
      agents/          OrderAgent — the domain agent orchestrating the enquiry-to-delivery workflow
      api/             FastAPI routers + serializers
      core/            config, db session
    seed/seed_data.py  Reference + demo data (lanes, carriers, HS codes, trade rules, customers)
  frontend/
    app/               Next.js App Router pages: control tower, quotes (list/new/detail), shipments (list/detail)
    components/        Nav, shared UI primitives
    lib/api.ts         Typed fetch client for the backend
```

## Running it

Backend (FastAPI + Postgres):
```
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Postgres running locally, database/user matching .env (DATABASE_URL)
python app/create_tables.py
python seed/seed_data.py
uvicorn app.main:app --reload --port 8000
```

Frontend (Next.js):
```
cd frontend
npm install
npm run dev   # http://localhost:3000, calls the API at NEXT_PUBLIC_API_URL (.env.local)
```

## Try it

On the **New Enquiry** page, these two enquiries (taken directly from PRD2's own worked
examples) run through the full pipeline and produce priced, approvable quotes:

- *"Need to ship 2 x 40HC containers of ceramic tiles from Foshan to Jebel Ali. Cargo ready
  20 October. Please quote door-to-door including customs."* — ocean FCL, resolves to the
  Shenzhen (Yantian) → Jebel Ali lane, HS 690721.
- *"Please quote 3 pallets of automotive parts from Shanghai to Dubai, ready around 15
  October, including pickup, customs clearance and delivery."* — air, resolves to Shanghai
  Pudong → Dubai Intl, HS 870829.

Approving either creates a shipment with a UAE-import document checklist (Certificate of
Origin auto-required). From the shipment page, recording events (Booking Confirmed →
Departed → Arrived → Delivered) advances the stage and drafts customer-update emails.

An enquiry for a lane with no seeded rate card (e.g. Mumbai → Los Angeles) correctly falls
into `MISSING_INFO` with a `NO_RATE_AVAILABLE` exception surfaced on the Control Tower.

## Suggested next steps (Phase 2/3 per the PRD)

1. Wire `AIGateway` to a real Claude call for extraction/HS classification/root-cause,
   behind the same interface.
2. Build the Invoice Reconciliation & Demurrage/Claims workflow (PRD1) — the data model
   already has `Container.last_free_day`/`free_days` and `brain/rules/demurrage.py` ready.
3. Add auth + RBAC (finance/operations/customs/admin roles are already named in the PRDs)
   and multi-tenancy (`tenant_id`) before this goes near real customer data.
4. Replace manual event entry with real carrier/customs API or EDI ingestion.
5. Add PDF generation for the quote and shipping documents.
