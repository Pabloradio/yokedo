"""add contacts and contact events tables

Revision ID: 0f1351f66ee0
Revises: bc1aa76a2bf0
Create Date: 2026-04-07 19:03:01.502689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f1351f66ee0"
down_revision: Union[str, Sequence[str], None] = "bc1aa76a2bf0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "contacts",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_low_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("user_high_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("current_status", sa.String(length=32), nullable=False),
        sa.Column("initial_connection_source", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            """
            (
                current_status = 'active'
                AND disconnected_at IS NULL
            )
            OR
            (
                current_status = 'inactive'
                AND disconnected_at IS NOT NULL
                AND disconnected_at >= connected_at
            )
            """,
            name=op.f("ck_contacts_status_timestamp_consistency"),
        ),
        sa.CheckConstraint(
            "current_status IN ('active', 'inactive')",
            name=op.f("ck_contacts_current_status"),
        ),
        sa.CheckConstraint(
            "initial_connection_source IN ('contact_request', 'invitation_link')",
            name=op.f("ck_contacts_initial_connection_source"),
        ),
        sa.CheckConstraint(
            "user_low_id < user_high_id",
            name=op.f("ck_contacts_user_low_id_lt_user_high_id"),
        ),
        sa.ForeignKeyConstraint(
            ["user_high_id"],
            ["users.id"],
            name=op.f("fk_contacts_user_high_id_users"),
        ),
        sa.ForeignKeyConstraint(
            ["user_low_id"],
            ["users.id"],
            name=op.f("fk_contacts_user_low_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contacts")),
        sa.UniqueConstraint(
            "user_low_id",
            "user_high_id",
            name="ux_contacts_user_low_id_user_high_id",
        ),
    )
    op.create_index("ix_contacts_current_status", "contacts", ["current_status"], unique=False)
    op.create_index(
        "ix_contacts_current_status_user_high_id",
        "contacts",
        ["current_status", "user_high_id"],
        unique=False,
    )
    op.create_index(
        "ix_contacts_current_status_user_low_id",
        "contacts",
        ["current_status", "user_low_id"],
        unique=False,
    )
    op.create_index("ix_contacts_user_high_id", "contacts", ["user_high_id"], unique=False)
    op.create_index("ix_contacts_user_low_id", "contacts", ["user_low_id"], unique=False)

    op.create_table(
        "contact_events",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("contact_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            """
            source IN (
                'contact_request_acceptance',
                'invitation_link_acceptance',
                'manual_disconnect',
                'manual_reconnect'
            )
            """,
            name=op.f("ck_contact_events_source"),
        ),
        sa.CheckConstraint(
            "event_type IN ('connected', 'disconnected')",
            name=op.f("ck_contact_events_event_type"),
        ),
        sa.CheckConstraint(
            """
            (
                event_type = 'connected'
                AND source IN (
                    'contact_request_acceptance',
                    'invitation_link_acceptance',
                    'manual_reconnect'
                )
            )
            OR
            (
                event_type = 'disconnected'
                AND source = 'manual_disconnect'
            )
            """,
            name=op.f("ck_contact_events_event_type_source_consistency"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_contact_events_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            name=op.f("fk_contact_events_contact_id_contacts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contact_events")),
    )
    op.create_index(
        "ix_contact_events_actor_user_id",
        "contact_events",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_contact_events_contact_id",
        "contact_events",
        ["contact_id"],
        unique=False,
    )
    op.create_index(
        "ix_contact_events_contact_id_event_at",
        "contact_events",
        ["contact_id", "event_at"],
        unique=False,
    )
    op.create_index(
        "ix_contact_events_event_at",
        "contact_events",
        ["event_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_contact_events_event_at", table_name="contact_events")
    op.drop_index("ix_contact_events_contact_id_event_at", table_name="contact_events")
    op.drop_index("ix_contact_events_contact_id", table_name="contact_events")
    op.drop_index("ix_contact_events_actor_user_id", table_name="contact_events")
    op.drop_table("contact_events")

    op.drop_index("ix_contacts_user_low_id", table_name="contacts")
    op.drop_index("ix_contacts_user_high_id", table_name="contacts")
    op.drop_index("ix_contacts_current_status_user_low_id", table_name="contacts")
    op.drop_index("ix_contacts_current_status_user_high_id", table_name="contacts")
    op.drop_index("ix_contacts_current_status", table_name="contacts")
    op.drop_table("contacts")