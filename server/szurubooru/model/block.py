"""User block model — one user blocking another."""

import sqlalchemy as sa
from datetime import datetime

from szurubooru.model.base import Base


class UserBlock(Base):
    """A user blocking another user.
    When A blocks B: B's content is hidden from A, B cannot DM A,
    and B's profile CSS is stripped when viewed by A.
    """

    __tablename__ = "user_block"

    block_id = sa.Column("id", sa.Integer, primary_key=True)
    blocker_id = sa.Column(
        "blocker_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    blocked_id = sa.Column(
        "blocked_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creation_time = sa.Column(
        "creation_time", sa.DateTime, nullable=False, default=datetime.utcnow
    )

    blocker = sa.orm.relationship(
        "User", foreign_keys=[blocker_id], backref="blocked_users"
    )
    blocked = sa.orm.relationship(
        "User", foreign_keys=[blocked_id], backref="blocked_by_users"
    )

    __table_args__ = (
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block"),
        sa.Index("ix_user_block_blocker", "blocker_id"),
        sa.Index("ix_user_block_blocked", "blocked_id"),
    )
