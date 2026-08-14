# Yokedo — Architecture Contract (v1)

## Purpose
Define non-negotiable cross-service rules to maintain system coherence.

## Core Rules

### 1. Source of Truth
- PostgreSQL real state > docs > design ideas

### 2. Service Ownership
- Each service owns its tables
- No service may modify external tables

### 3. Identity & Auth
- API Gateway validates identity via auth-service
- Downstream services trust:
  - X-User-ID
  - X-User-Is-Admin
- Client-sent identity headers must be ignored

### 4. Time Handling
- Storage: always UTC
- Business logic: timezone-aware

### 5. Matching & Social Graph
- `contacts-service` is the source of truth for contact relationships and social-graph authorization.
- `availability-service` owns availability rules, projections and overlap calculations.
- `availability-service` must not infer, persist or independently manage contact relationships.
- Matching may only be calculated between users whose relationship has been explicitly authorized by `contacts-service`.
- `contacts-service` decides which user IDs are eligible to participate in a matching operation.
- `availability-service` decides whether the authorized users have overlapping availability.
- The integration must use an explicit internal service contract; direct reads from tables owned by another service are forbidden.
- The concrete endpoint, request granularity and batching strategy are intentionally deferred until the matching use cases are implemented.
- Matching results are computed dynamically and are not persisted by `availability-service`.

### 6. Contact Acquisition Policy
- The MVP uses an invitation-first contact acquisition model.
- `invitation_links` and `invitation_acceptances` are the active entry path for creating contact relationships.
- Open user search and unsolicited cold contact initiation are excluded from the MVP.
- `contact_requests` remains owned by `contacts-service`, but is classified as **reserved and deprioritized for the MVP**.
- `contact_requests` does not participate in the Invitation MVP flow and must not be exposed as the primary contact acquisition mechanism.
- No additional development or schema hardening should be performed for `contact_requests` unless a future product iteration explicitly reactivates that flow.
- The table must not be removed without a separate schema and product decision.

### 7. Migrations
- One Alembic version table per service
- include_object mandatory

### 8. Forbidden
- Cross-service ORM imports
- Shared migration metadata
