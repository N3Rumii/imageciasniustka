import sqlalchemy as sa

from szurubooru.model.base import Base


class StatusHashtag(Base):
    __tablename__ = "status_hashtag"

    status_id = sa.Column(
        "status_id",
        sa.Integer,
        sa.ForeignKey("status.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    tag_id = sa.Column(
        "tag_id",
        sa.Integer,
        sa.ForeignKey("tag.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )

    tag = sa.orm.relationship("Tag")

    def __init__(self, status_id: int, tag_id: int) -> None:
        self.status_id = status_id
        self.tag_id = tag_id


class StatusReply(Base):
    __tablename__ = "status_reply"

    parent_status_id = sa.Column(
        "parent_status_id",
        sa.Integer,
        sa.ForeignKey("status.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    child_status_id = sa.Column(
        "child_status_id",
        sa.Integer,
        sa.ForeignKey("status.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )

    parent = sa.orm.relationship(
        "Status",
        foreign_keys=[parent_status_id],
        backref=sa.orm.backref("child_replies", cascade="all, delete-orphan"),
    )
    child = sa.orm.relationship(
        "Status",
        foreign_keys=[child_status_id],
        backref=sa.orm.backref("parent_replies", cascade="all, delete-orphan"),
    )

    def __init__(self, parent_id: int, child_id: int) -> None:
        self.parent_status_id = parent_id
        self.child_status_id = child_id


class StatusFavorite(Base):
    __tablename__ = "status_favorite"

    status_id = sa.Column(
        "status_id",
        sa.Integer,
        sa.ForeignKey("status.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    user_id = sa.Column(
        "user_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    time = sa.Column("time", sa.DateTime, nullable=False)

    status = sa.orm.relationship("Status")
    user = sa.orm.relationship("User")


class StatusRepost(Base):
    __tablename__ = "status_repost"

    status_id = sa.Column(
        "status_id",
        sa.Integer,
        sa.ForeignKey("status.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repost_status_id = sa.Column(
        "repost_status_id",
        sa.Integer,
        sa.ForeignKey("status.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    user_id = sa.Column(
        "user_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    time = sa.Column("time", sa.DateTime, nullable=False)

    original = sa.orm.relationship(
        "Status",
        foreign_keys=[status_id],
        backref=sa.orm.backref("reposts", cascade="all, delete-orphan"),
    )
    repost = sa.orm.relationship(
        "Status",
        foreign_keys=[repost_status_id],
        backref=sa.orm.backref("reposted_by", cascade="all, delete-orphan"),
    )
    user = sa.orm.relationship("User")


class Status(Base):
    __tablename__ = "status"

    status_id = sa.Column("id", sa.Integer, primary_key=True)
    user_id = sa.Column(
        "user_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    post_id = sa.Column(
        "post_id",
        sa.Integer,
        sa.ForeignKey("post.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    text = sa.Column("text", sa.UnicodeText, nullable=True)
    creation_time = sa.Column("creation_time", sa.DateTime, nullable=False)
    last_edit_time = sa.Column("last_edit_time", sa.DateTime)
    version = sa.Column("version", sa.Integer, default=1, nullable=False)
    private = sa.Column("private", sa.Boolean, nullable=False, default=False)

    user = sa.orm.relationship("User")
    post = sa.orm.relationship("Post")

    replies_rel = sa.orm.relationship(
        "StatusReply",
        foreign_keys="StatusReply.parent_status_id",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    favorites = sa.orm.relationship(
        "StatusFavorite", cascade="all, delete-orphan", lazy="joined"
    )
    hashtags = sa.orm.relationship(
        "StatusHashtag", cascade="all, delete-orphan", lazy="joined"
    )

    score = sa.orm.column_property(
        sa.sql.expression.select(sa.sql.expression.func.coalesce(
            sa.sql.expression.func.count(StatusFavorite.status_id), 0
        ))
        .where(StatusFavorite.status_id == status_id)
        .correlate_except(StatusFavorite)
        .scalar_subquery()
    )

    favorite_count = sa.orm.column_property(
        sa.sql.expression.select(
            sa.sql.expression.func.count(StatusFavorite.status_id)
        )
        .where(StatusFavorite.status_id == status_id)
        .correlate_except(StatusFavorite)
        .scalar_subquery()
    )

    reply_count = sa.orm.column_property(
        sa.sql.expression.select(
            sa.sql.expression.func.count(StatusReply.child_status_id)
        )
        .where(StatusReply.parent_status_id == status_id)
        .correlate_except(StatusReply)
        .scalar_subquery()
    )

    repost_count = sa.orm.column_property(
        sa.sql.expression.select(
            sa.sql.expression.func.count(StatusRepost.status_id)
        )
        .where(StatusRepost.status_id == status_id)
        .correlate_except(StatusRepost)
        .scalar_subquery()
    )

    __mapper_args__ = {
        "version_id_col": version,
        "version_id_generator": False,
    }
