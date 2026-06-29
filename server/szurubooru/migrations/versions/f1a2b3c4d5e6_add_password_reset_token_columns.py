"""
Add password_reset_token and password_reset_token_expiration columns to user table
for secure token-based password reset flow.

Revision ID: f1a2b3c4d5e6
Created at: 2025-03-04 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column(
            "password_reset_token",
            sa.Unicode(length=128),
            nullable=True,
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "password_reset_token_expiration",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("user", "password_reset_token_expiration")
    op.drop_column("user", "password_reset_token")
