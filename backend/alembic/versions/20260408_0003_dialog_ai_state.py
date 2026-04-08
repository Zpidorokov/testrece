"""Add dialog AI state storage.

Revision ID: 20260408_0003
Revises: 20260408_0002
Create Date: 2026-04-08 15:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260408_0003"
down_revision = "20260408_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dialogs", sa.Column("ai_state_json", sa.JSON(), nullable=True))
    op.execute("UPDATE dialogs SET ai_state_json = '{}' WHERE ai_state_json IS NULL")
    op.alter_column("dialogs", "ai_state_json", nullable=False)


def downgrade() -> None:
    op.drop_column("dialogs", "ai_state_json")
