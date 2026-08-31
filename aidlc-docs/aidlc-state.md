# AI-DLC State Tracking

## Project Information
- **Project Type**: Greenfield
- **Project Name**: Table Order Service
- **Start Date**: 2026-08-31T00:00:00Z
- **Current Phase**: CONSTRUCTION (in progress, per-unit)
- **Current Stage**: Unit `shared` — Functional Design + NFR Requirements complete (approved, PR #1); NFR Design pending. Unit 1 (backend-api) → Functional Design APPROVED + NFR Requirements APPROVED + **NFR Design APPROVED** (2026-08-31, Q1~Q6 all A). Artifacts: construction/backend-api/nfr-design/{nfr-design-patterns.md, logical-components.md}. Infrastructure Design = SKIP (local). **Code Generation (backend-api) NOT started** — user paused before Code Generation. Reconciliation w/ `shared` intact: Q10→A (no menu availability), 409 uses SESSION_CLOSED, has_new always false. No contract §3/§4/§9 change.
- **Execution Mode**: PARALLEL (2026-08-31) — 4 units developed concurrently by separate owners against Integration Contract v1.0 (SSOT). Original strict sequential order relaxed; contract is the coordination boundary (see unit-of-work-dependency.md §4). This owner: backend-api.

## Workspace State
- **Existing Code**: No
- **Reverse Engineering Needed**: No
- **Workspace Root**: ~/aidlc-workshop/table-order

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only
- **Structure patterns**: See code-generation.md Critical Rules

## Stage Progress

### INCEPTION Phase
- [x] Workspace Detection
- [x] Reverse Engineering (skipped - greenfield)
- [x] Requirements Analysis
- [x] User Stories
- [x] Workflow Planning
- [x] Application Design - EXECUTE
- [x] Units Generation - EXECUTE

### CONSTRUCTION Phase (per-unit loop)
**Units (4, order)**: 1) backend-api  2) shared  3) customer-web  4) admin-web

#### Unit 1: backend-api
- [x] Functional Design - EXECUTE (APPROVED 2026-08-31: domain-entities / business-logic-model / business-rules; SECURITY compliance — no blocking findings)
- [x] NFR Requirements - EXECUTE (APPROVED 2026-08-31: Q1~Q12 all recommended A; nfr-requirements.md + tech-stack-decisions.md; FastAPI+Pydantic v2 / Python 3.12 / SQLAlchemy 2.0; SECURITY-05 bounds + rate limit 5/5min concrete; no blocking findings; no contract §3/§4 change)
- [x] NFR Design - EXECUTE (APPROVED 2026-08-31: nfr-design-patterns.md + logical-components.md; Q1~Q6 all A — sync def+threadpool+per-request session, single engine+QueuePool+connect-hook PRAGMA WAL/FK/busy_timeout, write-contention retry 3x 10/20/40ms→fail closed, AppError taxonomy→HTTP mapping, auth/authz dep chain deny-by-default/IDOR, in-memory sliding-window rate limiter w/ sweep+cap eviction; middleware chain fixed; SECURITY no blocking, 01/02/06/07 N/A; no contract §3/§4 change)
- [ ] Infrastructure Design - SKIP (local dev only, no cloud/IaC)
- [ ] Code Generation - EXECUTE

#### Unit 2: shared
- [x] Functional Design - EXECUTE (approved 2026-08-31; PR #1)
- [x] NFR Requirements - EXECUTE (approved 2026-08-31; PR #1)
- [ ] NFR Design - EXECUTE
- [ ] Infrastructure Design - SKIP
- [ ] Code Generation - EXECUTE

#### Unit 3: customer-web
- [ ] Functional Design - EXECUTE
- [ ] NFR Requirements - EXECUTE
- [ ] NFR Design - EXECUTE
- [ ] Infrastructure Design - SKIP
- [ ] Code Generation - EXECUTE

#### Unit 4: admin-web
- [ ] Functional Design - EXECUTE
- [ ] NFR Requirements - EXECUTE
- [ ] NFR Design - EXECUTE
- [ ] Infrastructure Design - SKIP
- [ ] Code Generation - EXECUTE

#### After all units
- [ ] Build and Test - EXECUTE

### OPERATIONS Phase
- [ ] Operations (placeholder)

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | Yes | Requirements Analysis |
| Resiliency Baseline | No | Requirements Analysis |
| Property-Based Testing | Partial (pure functions & serialization round-trips only) | Requirements Analysis |
