"""Create user_block table for user blocking.

Revision ID: f2a3b4c5d6e7
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a3b4c5d6e7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_block",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "blocker_id",
            sa.Integer,
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "blocked_id",
            sa.Integer,
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("creation_time", sa.DateTime, nullable=False),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block"),
        sa.Index("ix_user_block_blocker", "blocker_id"),
        sa.Index("ix_user_block_blocked", "blocked_id"),
    )


def downgrade():
    op.drop_table("user_block")
