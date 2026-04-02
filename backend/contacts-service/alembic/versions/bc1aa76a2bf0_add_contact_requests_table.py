from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'bc1aa76a2bf0'
down_revision: Union[str, Sequence[str], None] = '411f9e923497'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contact_requests',

        # --- Identifiers ---
        sa.Column(
            'id',
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),

        sa.Column(
            'requester_id',
            UUID(as_uuid=True),
            nullable=False,
        ),

        sa.Column(
            'requested_id',
            UUID(as_uuid=True),
            nullable=False,
        ),

        # --- State ---
        sa.Column(
            'status',
            sa.String(length=20),
            nullable=False,
        ),

        # --- Optional ---
        sa.Column(
            'message',
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            'source',
            sa.String(length=50),
            nullable=True,
        ),

        # --- Audit ---
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),

        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),

        sa.Column(
            'responded_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            'responded_by',
            UUID(as_uuid=True),
            nullable=True,
        ),

        # --- Constraints ---
        sa.CheckConstraint(
            "requester_id != requested_id",
            name="ck_contact_requests_no_self_request",
        ),

        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'cancelled')",
            name="ck_contact_requests_status_valid",
        ),
    )

    # --- Indexes ---
    op.create_index(
        "idx_contact_requests_requested_status",
        "contact_requests",
        ["requested_id", "status"],
    )

    op.create_index(
        "idx_contact_requests_requester_status",
        "contact_requests",
        ["requester_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_contact_requests_requester_status",
        table_name="contact_requests",
    )

    op.drop_index(
        "idx_contact_requests_requested_status",
        table_name="contact_requests",
    )

    op.drop_table("contact_requests")