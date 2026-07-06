import sqlalchemy as sa

from szurubooru.model.base import Base


class UserFollow(Base):
    __tablename__ = "user_follow"

    follower_id = sa.Column(
        "follower_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    followee_id = sa.Column(
        "followee_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    creation_time = sa.Column("creation_time", sa.DateTime, nullable=False)

    follower = sa.orm.relationship(
        "User",
        foreign_keys=[follower_id],
        backref=sa.orm.backref("following", cascade="all, delete-orphan"),
    )
    followee = sa.orm.relationship(
        "User",
        foreign_keys=[followee_id],
        backref=sa.orm.backref("followers", cascade="all, delete-orphan"),
    )
