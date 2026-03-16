# Repository Overview

This repository contains a long-term personal engineering project focused on backend architecture, data modeling, and production-oriented MLOps practices.

The system is being developed as a microservices-oriented backend platform where service boundaries, logical data ownership, migration strategies, and ML components evolve under operational constraints.

## Engineering Focus

The repo prioritizes:

- FastAPI-based backend services
- PostgreSQL as the primary datastore, including vector support where applicable
- Strict migration isolation with dedicated Alembic version tables per service
- Containerized local development environments
- CI/CD automation through GitHub Actions
- Progressive integration of ML components such as embeddings and similarity logic

Security, schema correctness, and reproducibility are treated as first-class concerns.

## Architectural Approach

Each service is responsible for:

- Its own API contracts
- Its own migration history
- Clear ownership over its subset of tables
- Minimal cross-service coupling

Services currently share a PostgreSQL database while preserving isolated migration metadata and explicit table ownership boundaries.

This repository reflects ongoing engineering work rather than a finished product. 
Selected architecture notes and design decisions are documented in the docs/ directory.