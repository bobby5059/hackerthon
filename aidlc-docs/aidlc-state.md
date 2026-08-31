# AI-DLC State Tracking

## Project Information
- **Project Type**: Greenfield
- **Project Name**: Table Order Service
- **Start Date**: 2026-08-31T00:00:00Z
- **Current Phase**: CONSTRUCTION (in progress, per-unit)
- **Current Stage**: Unit `shared` — Functional Design + NFR Requirements complete (approved, PR #1); NFR Design pending

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
- [ ] Functional Design - EXECUTE
- [ ] NFR Requirements - EXECUTE
- [ ] NFR Design - EXECUTE
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
