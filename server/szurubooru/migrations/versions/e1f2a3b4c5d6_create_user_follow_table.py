"""create user_follow table

Revision ID: e1f2a3b4c5d6
Created at: 2026-07-02 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = ("5b5c940b4e78", "d1e2f3c4a5b6")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_follow",
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("followee_id", sa.Integer(), nullable=False),
        sa.Column("creation_time", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["follower_id"], ["user.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["followee_id"], ["user.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("follower_id", "followee_id"),
    )
    op.create_index(
        op.f("ix_user_follow_follower_id"),
        "user_follow",
        ["follower_id"],
    )
    op.create_index(
        op.f("ix_user_follow_followee_id"),
        "user_follow",
        ["followee_id"],
    )


def downgrade():
    op.drop_index(
        op.f("ix_user_follow_followee_id"), table_name="user_follow"
    )
    op.drop_index(
        op.f("ix_user_follow_follower_id"), table_name="user_follow"
    )
    op.drop_table("user_follow")
