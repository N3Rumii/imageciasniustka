import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import sqlalchemy as sa

from szurubooru import db, errors, model, rest
from szurubooru.func import posts, serialization, statuses, users

logger = logging.getLogger(__name__)


class NotificationNotFoundError(errors.NotFoundError):
    pass


class NotificationAccessError(errors.AuthError):
    pass


def _can_notify_for_post(
    post: model.Post, target_user: model.User
) -> bool:
    """Check if target_user should be notified about this post."""
    if not post.is_private:
        return True
    if post.user_id == target_user.user_id:
        return True
    whitelist_ids = [u.user_id for u in post.whitelist_users]
    return target_user.user_id in whitelist_ids


def create_notification(
    user_id: int,
    actor_id: Optional[int],
    notif_type: str,
    post_id: Optional[int] = None,
    status_id: Optional[int] = None,
    comment_id: Optional[int] = None,
    group_key: Optional[str] = None,
) -> Optional[model.Notification]:
    """Create a notification. If group_key is set and an existing unread,
    non-dismissed notification with the same key exists, increment its
    group_count instead of creating a new row."""
    # Don't notify self
    if actor_id is not None and user_id == actor_id:
        return None

    if not user_id:
        return None

    # If group_key is set, try to find an existing notification to increment
    if group_key:
        existing = (
            db.session.query(model.Notification)
            .filter(
                model.Notification.user_id == user_id,
                model.Notification.type == notif_type,
                model.Notification.group_key == group_key,
                model.Notification.is_dismissed == False,  # noqa: E712
            )
            .order_by(model.Notification.creation_time.desc())
            .first()
        )
        if existing:
            existing.group_count += 1
            existing.is_read = False
            existing.creation_time = datetime.utcnow()
            return existing

    notification = model.Notification()
    notification.user_id = user_id
    notification.actor_id = actor_id
    notification.type = notif_type
    notification.post_id = post_id
    notification.status_id = status_id
    notification.comment_id = comment_id
    notification.creation_time = datetime.utcnow()
    notification.group_key = group_key
    notification.group_count = 1
    db.session.add(notification)
    return notification


def get_notifications(
    user: model.User,
    offset: int = 0,
    limit: int = 50,
    include_dismissed: bool = False,
) -> List[model.Notification]:
    """Return paginated notifications for the user, newest first."""
    query = (
        db.session.query(model.Notification)
        .filter(model.Notification.user_id == user.user_id)
    )
    if not include_dismissed:
        query = query.filter(
            model.Notification.is_dismissed == False  # noqa: E712
        )
    return (
        query
        .order_by(model.Notification.creation_time.desc())
        .offset(offset)
        .limit(min(limit, 100))
        .all()
    )


def get_unread_count(user: model.User) -> int:
    """Return count of unread, non-dismissed notifications."""
    return (
        db.session.query(sa.func.count(model.Notification.notification_id))
        .filter(
            model.Notification.user_id == user.user_id,
            model.Notification.is_read == False,  # noqa: E712
            model.Notification.is_dismissed == False,  # noqa: E712
        )
        .scalar()
        or 0
    )


def _get_notification_for_user(
    notification_id: int, user: model.User
) -> model.Notification:
    notification = (
        db.session.query(model.Notification)
        .filter(model.Notification.notification_id == notification_id)
        .one_or_none()
    )
    if not notification:
        raise NotificationNotFoundError(
            "Notification %r not found." % notification_id
        )
    if notification.user_id != user.user_id:
        raise NotificationAccessError(
            "You do not have permission to access this notification."
        )
    return notification


def mark_read(notification_id: int, user: model.User) -> None:
    notification = _get_notification_for_user(notification_id, user)
    notification.is_read = True


def mark_all_read(user: model.User) -> None:
    (
        db.session.query(model.Notification)
        .filter(
            model.Notification.user_id == user.user_id,
            model.Notification.is_read == False,  # noqa: E712
        )
        .update({"is_read": True}, synchronize_session=False)
    )


def dismiss_notification(notification_id: int, user: model.User) -> None:
    notification = _get_notification_for_user(notification_id, user)
    notification.is_dismissed = True


def dismiss_all(user: model.User) -> None:
    (
        db.session.query(model.Notification)
        .filter(
            model.Notification.user_id == user.user_id,
            model.Notification.is_dismissed == False,  # noqa: E712
        )
        .update({"is_dismissed": True}, synchronize_session=False)
    )


def notify_followers_new_post(
    post: model.Post, actor: model.User
) -> None:
    """Notify all followers of actor about a new post (if post is not private
    or follower has access). Group bulk uploads in 5-minute windows."""
    from szurubooru.model.user_follow import UserFollow

    followers = (
        db.session.query(UserFollow.follower_id)
        .filter(UserFollow.followee_id == actor.user_id)
        .all()
    )
    if not followers:
        return

    group_key = "bulk_%d_%d" % (
        actor.user_id,
        int(datetime.utcnow().timestamp() / 300),
    )

    for (follower_id,) in followers:
        if follower_id == actor.user_id:
            continue
        # Check privacy - only notify if follower can view the post
        if not _can_notify_for_post(
            post,
            db.session.query(model.User)
            .filter(model.User.user_id == follower_id)
            .one(),
        ):
            continue
        create_notification(
            user_id=follower_id,
            actor_id=actor.user_id,
            notif_type=model.Notification.TYPE_NEW_POST,
            post_id=post.post_id,
            group_key=group_key,
        )


def notify_followers_new_status(
    status_obj: model.Status, actor: model.User
) -> None:
    """Notify all followers of actor about a new status (if not private)."""
    from szurubooru.model.user_follow import UserFollow

    if status_obj.private:
        return

    followers = (
        db.session.query(UserFollow.follower_id)
        .filter(UserFollow.followee_id == actor.user_id)
        .all()
    )
    if not followers:
        return

    for (follower_id,) in followers:
        if follower_id == actor.user_id:
            continue
        create_notification(
            user_id=follower_id,
            actor_id=actor.user_id,
            notif_type=model.Notification.TYPE_NEW_STATUS,
            status_id=status_obj.status_id,
        )


class NotificationSerializer(serialization.BaseSerializer):
    def __init__(
        self, notification: model.Notification, auth_user: model.User
    ) -> None:
        self.notification = notification
        self.auth_user = auth_user

    def _serializers(self) -> Dict[str, Callable[[], Any]]:
        return {
            "id": self.serialize_id,
            "type": self.serialize_type,
            "isRead": self.serialize_is_read,
            "creationTime": self.serialize_creation_time,
            "groupCount": self.serialize_group_count,
            "actor": self.serialize_actor,
            "post": self.serialize_post,
            "status": self.serialize_status,
            "comment": self.serialize_comment,
        }

    def serialize_id(self) -> Any:
        return self.notification.notification_id

    def serialize_type(self) -> Any:
        return self.notification.type

    def serialize_is_read(self) -> Any:
        return self.notification.is_read

    def serialize_creation_time(self) -> Any:
        return self.notification.creation_time

    def serialize_group_count(self) -> Any:
        return self.notification.group_count

    def serialize_actor(self) -> Any:
        if not self.notification.actor:
            return None
        return users.serialize_micro_user(
            self.notification.actor, self.auth_user
        )

    def serialize_post(self) -> Any:
        if not self.notification.post_id:
            return None
        try:
            return posts.serialize_post(
                self.notification.post,
                self.auth_user,
                options=["id", "thumbnailUrl", "type"],
            )
        except Exception:
            return None

    def serialize_status(self) -> Any:
        if not self.notification.status_id:
            return None
        try:
            return statuses.serialize_micro_status(
                self.notification.status, self.auth_user
            )
        except Exception:
            return None

    def serialize_comment(self) -> Any:
        if not self.notification.comment_id:
            return None
        from szurubooru.func import comments
        try:
            return comments.serialize_comment(
                self.notification.comment, self.auth_user
            )
        except Exception:
            return None


def serialize_notification(
    notification: Optional[model.Notification],
    auth_user: model.User,
    options: List[str] = [],
) -> Optional[rest.Response]:
    if not notification:
        return None
    return NotificationSerializer(notification, auth_user).serialize(options)
