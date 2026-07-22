"""create oauth2_client table for Mastodon API compatibility

Revision ID: m1a2s3t4o5d6
Revises: a1b2c3d4e5f6
Create Date: 2026-07-22 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "m1a2s3t4o5d6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "oauth2_client",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "client_id", sa.Unicode(64), nullable=False
        ),
        sa.Column(
            "client_secret", sa.Unicode(128), nullable=False
        ),
        sa.Column(
            "client_name", sa.Unicode(128), nullable=False
        ),
        sa.Column(
            "redirect_uris", sa.UnicodeText(), nullable=False
        ),
        sa.Column(
            "website", sa.Unicode(256), nullable=True
        ),
        sa.Column(
            "scopes", sa.Unicode(256), nullable=True
        ),
        sa.Column(
            "user_id", sa.Integer(), nullable=True
        ),
        sa.Column(
            "creation_time", sa.DateTime(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_oauth2_client_client_id"),
        "oauth2_client",
        ["client_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_oauth2_client_user_id"),
        "oauth2_client",
        ["user_id"],
    )


def downgrade():
    op.drop_index(
        op.f("ix_oauth2_client_user_id"), table_name="oauth2_client"
    )
    op.drop_index(
        op.f("ix_oauth2_client_client_id"), table_name="oauth2_client"
    )
    op.drop_table("oauth2_client")
