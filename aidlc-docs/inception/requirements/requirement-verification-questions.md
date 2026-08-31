# Requirements Clarification Questions - Table Order Service

Please answer the following questions to clarify requirements for the table order service.

## Question 1: Technology Stack - Frontend
What technology should be used for the customer-facing web UI?

A) React with TypeScript

B) Vue.js

C) Angular

D) Plain HTML/CSS/JavaScript

E) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2: Technology Stack - Backend
What backend framework/technology is preferred?

A) Node.js with Express/Fastify

B) Python (Django/Flask/FastAPI)

C) Java (Spring Boot)

D) Go

E) Other (please describe after [Answer]: tag below)

[Answer]: B (Python — FastAPI recommended for async/SSE support)

## Question 3: Database Choice
What type of database should be used?

A) Relational (PostgreSQL, MySQL)

B) NoSQL Document (MongoDB, DynamoDB)

C) NoSQL Key-Value (Redis for caching only)

D) Other (please describe after [Answer]: tag below)

[Answer]: D (SQLite — relational, file-based; ideal for MVP/local deployment)

## Question 4: Real-Time Communication
For real-time order monitoring, should the system support:

A) Server-Sent Events (SSE) only

B) WebSocket

C) Polling mechanism

D) Other (please describe after [Answer]: tag below)

[Answer]: C (Polling — chosen for MVP simplicity; note: original requirements doc specified SSE, this decision overrides it. 2s display requirement to be met via polling interval, e.g. ~2s)

## Question 5: Multi-Language Support
Should the UI support multiple languages from day one?

A) Yes - multiple languages required

B) No - Korean only for MVP

C) Other (please describe after [Answer]: tag below)

[Answer]: B (Korean only for MVP — consistent with constraints.md)

## Question 6: Table Identification
How should tables be identified?

A) QR code on each table (customer scans)

B) Tablet/device pre-configured with table ID

C) Manual table number entry

D) Other (please describe after [Answer]: tag below)

[Answer]: B (Tablet/device pre-configured with table ID + password, then auto-login — matches requirements 3.1.1)

## Question 7: Menu Management
Should the admin be able to manage menu items (add/update/delete)?

A) Yes - full menu management required

B) No - static menu for MVP

C) Other (please describe after [Answer]: tag below)

[Answer]: B (Static/seeded menu for MVP — consistent with MVP scope section which excludes admin menu management from MVP)

## Question 8: Order Status Visibility
What order statuses should be tracked?

A) Pending, Confirmed, Preparing, Ready, Completed

B) Pending, Confirmed, Completed only

C) Other (please describe after [Answer]: tag below)

[Answer]: C (Pending / Preparing / Completed — 대기중/준비중/완료, per requirements 3.1.5 & 3.2.2)

## Question 9: Customer Login Persistence
After auto-login, how long should the customer session last?

A) Duration of the dining session (until checkout)

B) Configurable duration (e.g., 8 hours)

C) Until the browser is closed

D) Other (please describe after [Answer]: tag below)

[Answer]: D (16-hour table session — matches the 16h session created at tablet setup in requirements 3.2.3; session also ends when admin marks table 'checkout complete', whichever comes first)

## Question 10: Admin JWT Token Duration
Confirm admin JWT token expiration: 16 hours?

A) Yes - 16 hours is correct

B) No - different duration needed

[Answer]: A (Yes — 16 hours, per requirements 3.2.1)

## Question 11: Order Modifications
Can customers modify or cancel orders after placing them?

A) Yes - full modification allowed

B) Yes - modification allowed within a time window

C) No - orders cannot be modified

D) Other (please describe after [Answer]: tag below)

[Answer]: C (No — customers cannot modify/cancel confirmed orders; only admin can delete an order per requirements 3.2.3)

## Question 12: Deployment Target
Where should the application be deployed?

A) Cloud (AWS, Azure, GCP)

B) On-premises

C) Local development environment for now

D) Other (please describe after [Answer]: tag below)

[Answer]: C (Local development environment for now — pairs well with SQLite)

## Extension Configuration Questions

### Question 13: Security Requirements
Should security baseline rules be enforced for this project?

A) Yes - enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)

B) No - skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

C) Other (please describe after [Answer]: tag below)

[Answer]: A (Yes — enforce SECURITY baseline; project has JWT auth, bcrypt password hashing, login attempt limiting)

### Question 14: Resiliency Requirements
Should the resiliency baseline be applied to this project?

A) Yes - apply the resiliency baseline as directional best practices and design-time guidance (recommended for business-critical workloads)

B) No - skip the resiliency baseline (suitable for PoCs, prototypes, and experimental projects)

C) Other (please describe after [Answer]: tag below)

[Answer]: B (No — skip resiliency baseline; local MVP deployment, revisit before production)

### Question 15: Property-Based Testing
Should property-based testing (PBT) rules be enforced for this project?

A) Yes - enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)

B) Partial - enforce PBT rules only for pure functions and serialization round-trips

C) No - skip all PBT rules (suitable for simple CRUD applications)

D) Other (please describe after [Answer]: tag below)

[Answer]: B (Partial — enforce PBT only for pure functions and serialization round-trips, e.g. cart total/price calculations)
