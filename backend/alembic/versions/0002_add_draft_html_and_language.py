"""add draft_body_html and draft_language to leads

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("draft_body_html", sa.Text(), nullable=True))
    op.add_column("leads", sa.Column("draft_language", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "draft_language")
    op.drop_column("leads", "draft_body_html")
