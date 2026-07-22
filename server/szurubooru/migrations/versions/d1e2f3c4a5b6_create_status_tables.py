"""create status tables

Revision ID: d1e2f3c4a5b6
Created at: 2026-07-01 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "d1e2f3c4a5b6"
down_revision = "c1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "status",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("post_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.UnicodeText(), nullable=True),
        sa.Column("creation_time", sa.DateTime(), nullable=False),
        sa.Column("last_edit_time", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("private", sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_status_user_id"), "status", ["user_id"])
    op.create_index(op.f("ix_status_post_id"), "status", ["post_id"])

    op.create_table(
        "status_reply",
        sa.Column("parent_status_id", sa.Integer(), nullable=False),
        sa.Column("child_status_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_status_id"], ["status.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["child_status_id"], ["status.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("parent_status_id", "child_status_id"),
    )
    op.create_index(
        op.f("ix_status_reply_parent_status_id"),
        "status_reply",
        ["parent_status_id"],
    )
    op.create_index(
        op.f("ix_status_reply_child_status_id"),
        "status_reply",
        ["child_status_id"],
    )

    op.create_table(
        "status_favorite",
        sa.Column("status_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["status_id"], ["status.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("status_id", "user_id"),
    )
    op.create_index(
        op.f("ix_status_favorite_status_id"), "status_favorite", ["status_id"]
    )
    op.create_index(
        op.f("ix_status_favorite_user_id"), "status_favorite", ["user_id"]
    )

    op.create_table(
        "status_repost",
        sa.Column("status_id", sa.Integer(), nullable=False),
        sa.Column("repost_status_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["status_id"], ["status.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["repost_status_id"], ["status.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("repost_status_id"),
    )
    op.create_index(
        op.f("ix_status_repost_status_id"), "status_repost", ["status_id"]
    )
    op.create_index(
        op.f("ix_status_repost_repost_status_id"),
        "status_repost",
        ["repost_status_id"],
    )
    op.create_index(
        op.f("ix_status_repost_user_id"), "status_repost", ["user_id"]
    )

    op.create_table(
        "status_hashtag",
        sa.Column("status_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["status_id"], ["status.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tag.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("status_id", "tag_id"),
    )
    op.create_index(
        op.f("ix_status_hashtag_status_id"), "status_hashtag", ["status_id"]
    )
    op.create_index(
        op.f("ix_status_hashtag_tag_id"), "status_hashtag", ["tag_id"]
    )


def downgrade():
    op.drop_index(op.f("ix_status_hashtag_tag_id"), table_name="status_hashtag")
    op.drop_index(
        op.f("ix_status_hashtag_status_id"), table_name="status_hashtag"
    )
    op.drop_table("status_hashtag")

    op.drop_index(op.f("ix_status_repost_user_id"), table_name="status_repost")
    op.drop_index(
        op.f("ix_status_repost_repost_status_id"), table_name="status_repost"
    )
    op.drop_index(
        op.f("ix_status_repost_status_id"), table_name="status_repost"
    )
    op.drop_table("status_repost")

    op.drop_index(
        op.f("ix_status_favorite_user_id"), table_name="status_favorite"
    )
    op.drop_index(
        op.f("ix_status_favorite_status_id"), table_name="status_favorite"
    )
    op.drop_table("status_favorite")

    op.drop_index(
        op.f("ix_status_reply_child_status_id"), table_name="status_reply"
    )
    op.drop_index(
        op.f("ix_status_reply_parent_status_id"), table_name="status_reply"
    )
    op.drop_table("status_reply")

    op.drop_index(op.f("ix_status_post_id"), table_name="status")
    op.drop_index(op.f("ix_status_user_id"), table_name="status")
    op.drop_table("status")
