"""Add profile customization columns to user table.

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-07-07 00:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f1a2b3c4d5e6"


def upgrade():
    op.add_column("user", sa.Column("profile_bio", sa.UnicodeText, nullable=True))
    op.add_column("user", sa.Column("profile_css", sa.UnicodeText, nullable=True))
    op.add_column(
        "user",
        sa.Column("profile_header_url", sa.Unicode(256), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("profile_accent_color", sa.Unicode(7), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column(
            "profile_layout", sa.Unicode(16), nullable=False, server_default="list"
        ),
    )


def downgrade():
    op.drop_column("user", "profile_layout")
    op.drop_column("user", "profile_accent_color")
    op.drop_column("user", "profile_header_url")
    op.drop_column("user", "profile_css")
    op.drop_column("user", "profile_bio")
