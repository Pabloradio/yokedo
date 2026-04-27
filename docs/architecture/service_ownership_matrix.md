# Yokedo — Service Ownership Matrix

| Service              | Owns Tables                          | Notes |
|---------------------|--------------------------------------|------|
| auth-service        | users, user_sessions                 | Identity source |
| availability-service| availabilities, templates, overrides | Time domain |
| contacts-service    | contact_requests, contacts, events   | Social graph |
| api-gateway         | NONE                                 | Stateless |

## Rules
- Only owner service migrates its tables
- Foreign keys allowed via stubs
