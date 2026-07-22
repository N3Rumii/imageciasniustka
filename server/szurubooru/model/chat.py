"""Chat models — encrypted messaging.

The server stores only public keys and ciphertext blobs.
Plaintext never touches the database.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from szurubooru.model.base import Base


class UserKey(Base):
    """A user's X25519 public key for E2E messaging."""

    __tablename__ = "user_key"

    user_key_id = sa.Column("id", sa.Integer, primary_key=True)
    user_id = sa.Column(
        "user_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    public_key = sa.Column(
        "public_key", sa.Text, nullable=False
    )
    created_at = sa.Column(
        "created_at", sa.DateTime, nullable=False
    )

    user = sa.orm.relationship("User")


class Conversation(Base):
    """A pairwise conversation between two users."""

    __tablename__ = "conversation"

    conversation_id = sa.Column("id", sa.Integer, primary_key=True)
    user1_id = sa.Column(
        "user1_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user2_id = sa.Column(
        "user2_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = sa.Column("created_at", sa.DateTime, nullable=False)
    last_message_at = sa.Column("last_message_at", sa.DateTime, nullable=True)
    name = sa.Column("name", sa.Text, nullable=True)
    convo_type = sa.Column("convo_type", sa.Text, default="dm")

    user1 = sa.orm.relationship("User", foreign_keys=[user1_id])
    user2 = sa.orm.relationship("User", foreign_keys=[user2_id])

    __table_args__ = (
        sa.UniqueConstraint("user1_id", "user2_id"),
    )


class Message(Base):
    """An encrypted message. Ciphertext only — server cannot read."""

    __tablename__ = "chat_message"

    message_id = sa.Column("id", sa.Integer, primary_key=True)
    conversation_id = sa.Column(
        "conversation_id",
        sa.Integer,
        sa.ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id = sa.Column(
        "sender_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # AES-256-GCM ciphertext (base64-encoded)
    ciphertext = sa.Column("ciphertext", sa.Text, nullable=False)
    # 12-byte IV (base64-encoded)
    iv = sa.Column("iv", sa.Text, nullable=False)
    post_id = sa.Column(
        "post_id",
        sa.Integer,
        sa.ForeignKey("post.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = sa.Column("created_at", sa.DateTime, nullable=False)

    post = sa.orm.relationship("Post")
    conversation = sa.orm.relationship(
        "Conversation", backref=sa.orm.backref("messages", lazy="dynamic")
    )
    sender = sa.orm.relationship("User")

    # Index for SSE streaming: find messages newer than X
    __table_args__ = (
        sa.Index("ix_chat_message_created", "created_at"),
    )
