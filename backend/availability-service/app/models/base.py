# app/models/base.py

from sqlalchemy.orm import declarative_base

# Shared Base for all SQLAlchemy models in this microservice
Base = declarative_base()
