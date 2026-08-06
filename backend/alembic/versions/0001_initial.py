"""initial schema: leads, app_config

Revision ID: 0001
Revises:
Create Date: 2026-08-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEAD_STATUSES = (
    "new",
    "normalized",
    "enriched",
    "draft_ready",
    "approved",
    "rejected",
    "sent",
    "failed",
)


def upgrade() -> None:
    lead_status = postgresql.ENUM(*LEAD_STATUSES, name="lead_status")
    lead_status.create(op.get_bind())
    # Column below reuses the same type without letting create_table try to
    # CREATE TYPE again (it already exists from the line above).
    lead_status = postgresql.ENUM(*LEAD_STATUSES, name="lead_status", create_type=False)

    op.create_table(
        "leads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("enrichment", postgresql.JSONB(), nullable=True),
        sa.Column("draft_subject", sa.Text(), nullable=True),
        sa.Column("draft_body", sa.Text(), nullable=True),
        sa.Column(
            "status",
            lead_status,
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    # Duplicate-lookup index: same lowercased email within a recent window.
    op.execute(
        "CREATE INDEX ix_leads_email_lower_created_at "
        "ON leads (lower(email), created_at DESC)"
    )

    op.create_table(
        "app_config",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("app_config")
    op.drop_index("ix_leads_email_lower_created_at", table_name="leads")
    op.drop_table("leads")
    postgresql.ENUM(*LEAD_STATUSES, name="lead_status").drop(op.get_bind())
