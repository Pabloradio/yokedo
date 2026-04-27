# Yokedo — API & Conventions

## Headers
- X-User-ID (UUID)
- X-User-Is-Admin (bool)
- X-Request-ID (trace)

## Errors
- Consistent HTTP codes:
  - 400: validation
  - 403: forbidden
  - 404: not found
  - 409: conflict

## IDs
- Always UUID

## Time
- All timestamps in UTC (ISO 8601)

## Pagination
- Cursor-based preferred

## Idempotency
- Required for write endpoints where applicable
