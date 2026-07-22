"""create notification table

Revision ID: a1b2c3d4e5f6
Revises: e1f2a3b4c5d6
Create Date: 2026-07-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'notification',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column(
            'user_id',
            sa.Integer,
            sa.ForeignKey('user.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'actor_id',
            sa.Integer,
            sa.ForeignKey('user.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'type',
            sa.Unicode(32),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'post_id',
            sa.Integer,
            sa.ForeignKey('post.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'status_id',
            sa.Integer,
            sa.ForeignKey('status.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'comment_id',
            sa.Integer,
            sa.ForeignKey('comment.id', ondelete='SET NULL'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'is_read',
            sa.Boolean,
            nullable=False,
            default=False,
            server_default=sa.text('false'),
        ),
        sa.Column(
            'is_dismissed',
            sa.Boolean,
            nullable=False,
            default=False,
            server_default=sa.text('false'),
        ),
        sa.Column(
            'creation_time',
            sa.DateTime,
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.Column(
            'group_key',
            sa.Unicode(64),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'group_count',
            sa.Integer,
            nullable=False,
            default=1,
            server_default=sa.text('1'),
        ),
    )


def downgrade():
    op.drop_table('notification')
