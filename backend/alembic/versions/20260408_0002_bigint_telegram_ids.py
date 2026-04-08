"""Align Telegram-related identifiers to BIGINT.

Revision ID: 20260408_0002
Revises: 20260407_0001
Create Date: 2026-04-08 10:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260408_0002"
down_revision = "20260407_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "telegram_user_id", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column("clients", "telegram_user_id", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column("forum_topics", "chat_id", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column("forum_topics", "topic_id", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column("forum_topics", "message_thread_id", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column("dialogs", "telegram_chat_id", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column("dialogs", "forum_thread_id", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column("messages", "telegram_message_id", existing_type=sa.Integer(), type_=sa.BigInteger())


def downgrade() -> None:
    op.alter_column("messages", "telegram_message_id", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column("dialogs", "forum_thread_id", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column("dialogs", "telegram_chat_id", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column("forum_topics", "message_thread_id", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column("forum_topics", "topic_id", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column("forum_topics", "chat_id", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column("clients", "telegram_user_id", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column("users", "telegram_user_id", existing_type=sa.BigInteger(), type_=sa.Integer())
