"""create pool whitelist table

Revision ID: c2d3e4f5a6b7
Created at: 2026-06-27 22:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1e2f3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pool_whitelist",
        sa.Column("pool_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["pool.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("pool_id", "user_id"),
    )
    op.create_index(
        op.f("ix_pool_whitelist_pool_id"), "pool_whitelist", ["pool_id"]
    )
    op.create_index(
        op.f("ix_pool_whitelist_user_id"), "pool_whitelist", ["user_id"]
    )


def downgrade():
    op.drop_index(op.f("ix_pool_whitelist_user_id"), table_name="pool_whitelist")
    op.drop_index(op.f("ix_pool_whitelist_pool_id"), table_name="pool_whitelist")
    op.drop_table("pool_whitelist")
