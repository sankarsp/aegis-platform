"""payment rails

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_rails",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("operator", sa.String(length=160), nullable=False),
        sa.Column("region", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("message_standard", sa.String(length=200), nullable=False),
        sa.Column("settlement", sa.String(length=200), nullable=False),
        sa.Column("availability", sa.String(length=120), nullable=False),
        sa.Column("txn_limit", sa.String(length=160), nullable=False),
        sa.Column("routes_to", sa.JSON(), nullable=False),
        sa.Column("regulations", sa.JSON(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("cde_ids", sa.JSON(), nullable=False),
        sa.Column("model_ids", sa.JSON(), nullable=False),
        sa.Column("report_id", sa.String(length=40), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("controls", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("payment_rails")
