"""create post whitelist table

Revision ID: b1e2f3c4d5e6
Created at: 2026-06-27 14:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "b1e2f3c4d5e6"
down_revision = "adcd63ff76a2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "post_whitelist",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id", "user_id"),
    )
    op.create_index(
        op.f("ix_post_whitelist_post_id"), "post_whitelist", ["post_id"]
    )
    op.create_index(
        op.f("ix_post_whitelist_user_id"), "post_whitelist", ["user_id"]
    )


def downgrade():
    op.drop_index(op.f("ix_post_whitelist_user_id"), table_name="post_whitelist")
    op.drop_index(op.f("ix_post_whitelist_post_id"), table_name="post_whitelist")
    op.drop_table("post_whitelist")
