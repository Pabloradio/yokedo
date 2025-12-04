"""add default false to is_deleted

Revision ID: caf17025ae92
Revises: eeb643c4230e
Create Date: 2025-12-04 18:30:44.844409

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'caf17025ae92'
down_revision: Union[str, Sequence[str], None] = 'eeb643c4230e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "is_deleted",
        server_default=sa.false(),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )



def downgrade() -> None:
    op.alter_column(
        "users",
        "is_deleted",
        server_default=None,
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )
