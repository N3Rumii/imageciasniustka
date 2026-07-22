"""OAuth2 client and access token models for Mastodon API compatibility."""

import sqlalchemy as sa

from szurubooru.model.base import Base


class OAuth2Client(Base):
    """Registered Mastodon API client application."""

    __tablename__ = "oauth2_client"

    oauth2_client_id = sa.Column("id", sa.Integer, primary_key=True)
    client_id = sa.Column(
        "client_id",
        sa.Unicode(64),
        nullable=False,
        unique=True,
        index=True,
    )
    client_secret = sa.Column(
        "client_secret", sa.Unicode(128), nullable=False
    )
    client_name = sa.Column(
        "client_name", sa.Unicode(128), nullable=False
    )
    redirect_uris = sa.Column(
        "redirect_uris", sa.UnicodeText, nullable=False
    )
    website = sa.Column("website", sa.Unicode(256), nullable=True)
    scopes = sa.Column("scopes", sa.Unicode(256), nullable=True)
    user_id = sa.Column(
        "user_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    creation_time = sa.Column("creation_time", sa.DateTime, nullable=False)

    user = sa.orm.relationship("User")
