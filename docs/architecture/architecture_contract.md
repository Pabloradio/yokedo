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
- availability-service: NO social graph logic
- contacts-service: owns relationships

### 6. Migrations
- One Alembic version table per service
- include_object mandatory

### 7. Forbidden
- Cross-service ORM imports
- Shared migration metadata
