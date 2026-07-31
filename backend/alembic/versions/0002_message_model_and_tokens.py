"""add model/token tracking columns to messages, for per-model usage analytics

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("model", sa.String(64), nullable=True))
    op.add_column("messages", sa.Column("prompt_tokens", sa.Integer, nullable=True))
    op.add_column("messages", sa.Column("completion_tokens", sa.Integer, nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "completion_tokens")
    op.drop_column("messages", "prompt_tokens")
    op.drop_column("messages", "model")
