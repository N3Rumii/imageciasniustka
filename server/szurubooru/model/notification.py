import sqlalchemy as sa

from szurubooru.model.base import Base


class Notification(Base):
    __tablename__ = "notification"

    TYPE_POST_LIKE = "post_like"
    TYPE_POST_DISLIKE = "post_dislike"
    TYPE_POST_FAVORITE = "post_favorite"
    TYPE_POST_COMMENT = "post_comment"
    TYPE_STATUS_FAVORITE = "status_favorite"
    TYPE_STATUS_REPLY = "status_reply"
    TYPE_NEW_POST = "new_post"
    TYPE_NEW_STATUS = "new_status"
    TYPE_NEW_MESSAGE = "new_message"

    notification_id = sa.Column("id", sa.Integer, primary_key=True)
    user_id = sa.Column(
        "user_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id = sa.Column(
        "actor_id",
        sa.Integer,
        sa.ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type = sa.Column("type", sa.Unicode(32), nullable=False, index=True)
    post_id = sa.Column(
        "post_id",
        sa.Integer,
        sa.ForeignKey("post.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status_id = sa.Column(
        "status_id",
        sa.Integer,
        sa.ForeignKey("status.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    comment_id = sa.Column(
        "comment_id",
        sa.Integer,
        sa.ForeignKey("comment.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_read = sa.Column(
        "is_read", sa.Boolean, nullable=False, default=False
    )
    is_dismissed = sa.Column(
        "is_dismissed", sa.Boolean, nullable=False, default=False
    )
    creation_time = sa.Column(
        "creation_time", sa.DateTime, nullable=False
    )
    group_key = sa.Column(
        "group_key", sa.Unicode(64), nullable=True, index=True
    )
    group_count = sa.Column(
        "group_count", sa.Integer, nullable=False, default=1
    )

    user = sa.orm.relationship("User", foreign_keys=[user_id])
    actor = sa.orm.relationship("User", foreign_keys=[actor_id])
    post = sa.orm.relationship("Post")
    status = sa.orm.relationship("Status")
    comment = sa.orm.relationship("Comment")
