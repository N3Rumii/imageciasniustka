import re
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import sqlalchemy as sa

from szurubooru import db, errors, model, rest
from szurubooru.func import posts, serialization, tags, users, util


class StatusNotFoundError(errors.NotFoundError):
    pass


class StatusAccessDeniedError(errors.AuthError):
    pass


class InvalidStatusTextError(errors.ValidationError):
    pass


class StatusAlreadyFavoritedError(errors.ValidationError):
    pass


class StatusNotFavoritedError(errors.ValidationError):
    pass


class StatusAlreadyRepostedError(errors.ValidationError):
    pass


class StatusNotRepostedError(errors.ValidationError):
    pass


class InvalidStatusRelationError(errors.ValidationError):
    pass


HASHTAG_REGEX = re.compile(r"#([\w\u00C0-\u024F]+)")


def _clean_text(text: Optional[str]) -> Optional[str]:
    """Trim whitespace and collapse excessive blank lines."""
    if not text:
        return text
    # Strip leading/trailing whitespace
    text = text.strip()
    if not text:
        return None
    # Collapse 3+ consecutive newlines into at most 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def extract_hashtags(text: str) -> List[str]:
    """Extract unique hashtag names from text."""
    if not text:
        return []
    return list(dict.fromkeys(HASHTAG_REGEX.findall(text)))


def _get_status_by_id(
    status_id: int, user: Optional[model.User] = None
) -> model.Status:
    status = (
        db.session.query(model.Status)
        .filter(model.Status.status_id == status_id)
        .one_or_none()
    )
    if not status:
        raise StatusNotFoundError("Status %r not found." % status_id)
    if status.private and (
        not user or (status.user_id != user.user_id and user.rank != model.User.RANK_ADMINISTRATOR)
    ):
        raise StatusAccessDeniedError(
            "You do not have permission to view this status."
        )
    return status


def create_status(
    text: Optional[str],
    user: Optional[model.User],
    image_content: Optional[bytes] = None,
    parent_status_id: Optional[int] = None,
    private: bool = False,
    post_type: str = "status",
) -> model.Status:
    """Create a new status. If image_content is provided, a linked Post is also
    created and hashtags from the text become Post tags. If no image but
    image_content is None and text is None, this creates an image-only status
    for a pre-existing Post (used by the auto-feed integration)."""

    # Spam prevention: reject duplicate content from same user within 60s
    if user and user.user_id:
        cleaned = _clean_text(text)
        recent_cutoff = datetime.utcnow() - timedelta(seconds=60)
        duplicate = (
            db.session.query(model.Status)
            .filter(
                model.Status.user_id == user.user_id,
                model.Status.text == cleaned,
                model.Status.creation_time >= recent_cutoff,
            )
            .first()
        )
        if duplicate:
            raise errors.ValidationError(
                "You already posted this. Wait a moment before posting again."
            )

    status = model.Status()
    status.user = user
    status.text = _clean_text(text)
    status.creation_time = datetime.utcnow()
    status.private = private
    status.post_type = post_type if post_type in ("status", "blog") else "status"
    if post_type == "blog" and status.text and len(status.text) > 3000:
        raise InvalidStatusTextError(
            "Blog posts are limited to 3000 characters."
        )
    if post_type != "blog" and status.text and len(status.text) > 1000:
        raise InvalidStatusTextError(
            "Statuses are limited to 1000 characters."
        )
    db.session.add(status)
    db.session.flush()

    # Handle parent reply
    if parent_status_id is not None:
        parent = _get_status_by_id(parent_status_id, user)
        db.session.add(model.StatusReply(parent.status_id, status.status_id))
        # If replying with image AND parent has image, chain Posts
        # (handled below after post creation)
        _chain_posts = bool(image_content and parent.post_id)

    # Handle image: create a linked Post on the image board
    parent_for_relations = None
    if image_content:
        from szurubooru.func import posts as posts_func
        tag_names = []
        if text:
            tag_names = extract_hashtags(text)
        post, new_tags = posts_func.create_post(
            image_content, tag_names, user
        )
        db.session.flush()
        status.post_id = post.post_id

        # If this is a reply with image to an image-post parent, chain
        if parent_status_id is not None and parent:
            parent = _get_status_by_id(parent_status_id, user)
            if parent.post_id:
                posts_func.update_post_relations(
                    db.session.query(model.Post)
                    .filter(model.Post.post_id == status.post_id)
                    .one(),
                    [post.post_id for post in parent.post.relations]
                    + [parent.post_id],
                )
        # Start AVIF conversion in background
        posts_func.finalize_post_avif_background(post)

    # Extract and link hashtags from text
    if text:
        hashtag_names = extract_hashtags(text)
        if hashtag_names:
            existing_tags, new_tags = tags.get_or_create_tags_by_names(
                hashtag_names
            )
            all_tags = existing_tags + new_tags
            db.session.flush()
            for tag in all_tags:
                db.session.add(
                    model.StatusHashtag(status.status_id, tag.tag_id)
                )
            # If there's a linked post, also add tags to it
            if status.post_id:
                post = (
                    db.session.query(model.Post)
                    .filter(model.Post.post_id == status.post_id)
                    .one()
                )
                for t in all_tags:
                    if t not in post.tags:
                        post.tags.append(t)

    return status


def update_status(
    status: model.Status, text: Optional[str]
) -> None:
    assert status
    if text is not None:
        status.text = text
        status.last_edit_time = datetime.utcnow()
        # Update hashtags
        status.hashtags.clear()
        hashtag_names = extract_hashtags(text or "")
        if hashtag_names:
            existing_tags, new_tags = tags.get_or_create_tags_by_names(
                hashtag_names
            )
            all_tags = existing_tags + new_tags
            db.session.flush()
            for tag in all_tags:
                db.session.add(
                    model.StatusHashtag(status.status_id, tag.tag_id)
                )


def delete_status(status: model.Status) -> None:
    assert status
    # Clear hashtag entries
    status.hashtags.clear()
    # Clear favorites
    status.favorites.clear()
    # Clear replies: delete StatusReply entries where this is the parent
    for reply in list(status.replies_rel):
        db.session.delete(reply)
    # Clear parent_replies: delete StatusReply entries where this is a child
    # (i.e. this status is replying to someone else)
    for reply in list(status.parent_replies):
        db.session.delete(reply)
    db.session.delete(status)


def get_status_replies(
    status: model.Status, user: Optional[model.User] = None
) -> List[model.Status]:
    reply_ids = [r.child_status_id for r in status.replies_rel]
    if not reply_ids:
        return []
    return (
        db.session.query(model.Status)
        .filter(model.Status.status_id.in_(reply_ids))
        .order_by(model.Status.creation_time.asc())
        .all()
    )


def set_status_favorite(
    status: model.Status, user: model.User
) -> None:
    assert status
    assert user
    existing = (
        db.session.query(model.StatusFavorite)
        .filter(
            model.StatusFavorite.status_id == status.status_id,
            model.StatusFavorite.user_id == user.user_id,
        )
        .one_or_none()
    )
    if existing:
        raise StatusAlreadyFavoritedError("Already favorited.")
    fav = model.StatusFavorite()
    fav.status_id = status.status_id
    fav.user_id = user.user_id
    fav.time = datetime.utcnow()
    db.session.add(fav)


def delete_status_favorite(
    status: model.Status, user: model.User
) -> None:
    assert status
    assert user
    existing = (
        db.session.query(model.StatusFavorite)
        .filter(
            model.StatusFavorite.status_id == status.status_id,
            model.StatusFavorite.user_id == user.user_id,
        )
        .one_or_none()
    )
    if not existing:
        raise StatusNotFavoritedError("Not favorited.")
    db.session.delete(existing)


def repost_status(
    status: model.Status, user: model.User, text: Optional[str] = None
) -> model.Status:
    """Create a repost (retweet). Returns the new repost Status.
    If text is provided, it is included as the reposter's comment."""
    assert status
    assert user
    existing = (
        db.session.query(model.StatusRepost)
        .filter(
            model.StatusRepost.status_id == status.status_id,
            model.StatusRepost.user_id == user.user_id,
        )
        .one_or_none()
    )
    if existing:
        raise StatusAlreadyRepostedError("Already reposted.")
    repost_status_obj = model.Status()
    repost_status_obj.user = user
    repost_status_obj.text = text.strip() if text else None
    repost_status_obj.creation_time = datetime.utcnow()
    repost_status_obj.post_id = status.post_id
    db.session.add(repost_status_obj)
    db.session.flush()

    repost_entry = model.StatusRepost()
    repost_entry.status_id = status.status_id
    repost_entry.repost_status_id = repost_status_obj.status_id
    repost_entry.user_id = user.user_id
    repost_entry.time = datetime.utcnow()
    db.session.add(repost_entry)
    return repost_status_obj


def undo_repost(status: model.Status, user: model.User) -> None:
    assert status
    assert user
    repost_entry = (
        db.session.query(model.StatusRepost)
        .filter(
            model.StatusRepost.status_id == status.status_id,
            model.StatusRepost.user_id == user.user_id,
        )
        .one_or_none()
    )
    if not repost_entry:
        raise StatusNotRepostedError("Not reposted.")
    # Also delete the repost-created status
    repost_status = (
        db.session.query(model.Status)
        .filter(
            model.Status.status_id == repost_entry.repost_status_id
        )
        .one_or_none()
    )
    db.session.delete(repost_entry)
    if repost_status:
        db.session.delete(repost_status)


def _apply_sort(query, sort_str: Optional[str]) -> Any:
    """Apply a sort parameter to a Status query. Supports:
    creation-date (default desc), score, fav-count, repost-count.
    Append ,asc for ascending order."""
    if not sort_str:
        return query.order_by(model.Status.creation_time.desc())
    sort_str = sort_str.strip().lower()
    ascending = sort_str.endswith(",asc")
    base = sort_str.replace(",asc", "")
    column_map = {
        "creation-date": model.Status.creation_time,
        "creation-time": model.Status.creation_time,
        "score": (
            sa.select(sa.func.count(model.StatusFavorite.status_id))
            .where(model.StatusFavorite.status_id == model.Status.status_id)
            .correlate_except(model.StatusFavorite)
            .scalar_subquery()
        ),
        "fav-count": (
            sa.select(sa.func.count(model.StatusFavorite.status_id))
            .where(model.StatusFavorite.status_id == model.Status.status_id)
            .correlate_except(model.StatusFavorite)
            .scalar_subquery()
        ),
        "repost-count": (
            sa.select(sa.func.count(model.StatusRepost.repost_status_id))
            .where(model.StatusRepost.status_id == model.Status.status_id)
            .correlate_except(model.StatusRepost)
            .scalar_subquery()
        ),
    }
    col = column_map.get(base)
    if col is not None:
        return query.order_by(col.asc() if ascending else col.desc())
    return query.order_by(model.Status.creation_time.desc())


def get_status_timeline(
    user: Optional[model.User], offset: int = 0, limit: int = 50,
    feed: Optional[str] = None, sort: Optional[str] = None,
) -> List[model.Status]:
    """Return the global timeline, newest first. If feed='myfeed', show only
    statuses from users followed by `user`. Image-only posts that have a
    Status entry (auto-created when Post is uploaded) appear here too."""
    query = db.session.query(model.Status)
    # Exclude blog posts from the community timeline
    query = query.filter(
        sa.or_(
            model.Status.post_type == "status",
            model.Status.post_type == None,
        )
    )
    if feed == "myfeed" and user and user.user_id:
        from szurubooru.model.user_follow import UserFollow
        followed_ids = (
            sa.select(UserFollow.followee_id)
            .where(UserFollow.follower_id == user.user_id)
            .scalar_subquery()
        )
        query = query.filter(model.Status.user_id.in_(followed_ids))
    elif feed == "myfeed":
        # Not logged in, return nothing
        return []
    query = _apply_sort(query, sort)
    return query.offset(offset).limit(limit).all()


def get_status_timeline_by_tag(
    tag_name: str,
    user: Optional[model.User],
    offset: int = 0,
    limit: int = 50,
    sort: Optional[str] = None,
) -> List[model.Status]:
    """Return statuses containing a specific hashtag."""
    tag = (
        db.session.query(model.Tag)
        .join(model.TagName)
        .filter(model.TagName.name == tag_name)
        .one_or_none()
    )
    if not tag:
        return []
    status_ids = (
        db.session.query(model.StatusHashtag.status_id)
        .filter(model.StatusHashtag.tag_id == tag.tag_id)
        .all()
    )
    if not status_ids:
        return []
    ids = [s[0] for s in status_ids]
    query = (
        db.session.query(model.Status)
        .filter(model.Status.status_id.in_(ids))
    )
    query = _apply_sort(query, sort)
    return query.offset(offset).limit(limit).all()


def get_status_timeline_by_user(
    user_name: str, offset: int = 0, limit: int = 50,
    sort: Optional[str] = None,
) -> List[model.Status]:
    target_user = users.try_get_user_by_name(user_name)
    if not target_user:
        return []
    query = (
        db.session.query(model.Status)
        .filter(model.Status.user_id == target_user.user_id)
    )
    query = _apply_sort(query, sort)
    return query.offset(offset).limit(limit).all()


def create_status_for_post(
    post: model.Post, user: Optional[model.User]
) -> model.Status:
    """Auto-create a Status entry for an image-only upload so it appears
    in the timeline feed."""
    status = model.Status()
    status.user = user or post.user
    status.post_id = post.post_id
    status.text = None
    status.creation_time = datetime.utcnow()
    status.private = post.is_private
    db.session.add(status)

    # Link existing post tags as hashtags
    for tag in post.tags:
        db.session.add(
            model.StatusHashtag(status.status_id, tag.tag_id)
        )
    return status


class StatusSerializer(serialization.BaseSerializer):
    def __init__(self, status: model.Status, auth_user: model.User) -> None:
        self.status = status
        self.auth_user = auth_user

    def _serializers(self) -> Dict[str, Callable[[], Any]]:
        return {
            "id": self.serialize_id,
            "version": self.serialize_version,
            "text": self.serialize_text,
            "creationTime": self.serialize_creation_time,
            "lastEditTime": self.serialize_last_edit_time,
            "postType": self.serialize_post_type,
            "private": self.serialize_private,
            "user": self.serialize_user,
            "post": self.serialize_post,
            "hashtags": self.serialize_hashtags,
            "score": self.serialize_score,
            "favoriteCount": self.serialize_favorite_count,
            "replyCount": self.serialize_reply_count,
            "repostCount": self.serialize_repost_count,
            "ownFavorite": self.serialize_own_favorite,
            "ownRepost": self.serialize_own_repost,
            "isRepost": self.serialize_is_repost,
            "repostOriginal": self.serialize_repost_original,
            "isReply": self.serialize_is_reply,
            "replyTo": self.serialize_reply_to,
            "replies": self.serialize_replies,
        }

    def serialize_id(self) -> Any:
        return self.status.status_id

    def serialize_version(self) -> Any:
        return self.status.version

    def serialize_text(self) -> Any:
        return self.status.text

    def serialize_creation_time(self) -> Any:
        return self.status.creation_time

    def serialize_last_edit_time(self) -> Any:
        return self.status.last_edit_time

    def serialize_post_type(self) -> Any:
        return self.status.post_type or "status"

    def serialize_private(self) -> Any:
        return self.status.private

    def serialize_user(self) -> Any:
        return users.serialize_micro_user(
            self.status.user, self.auth_user
        )

    def serialize_post(self) -> Any:
        if not self.status.post_id:
            return None
        from szurubooru.func import posts as posts_func
        return posts_func.serialize_post(
            self.status.post, self.auth_user
        )

    def serialize_hashtags(self) -> Any:
        return sorted(
            [
                {"name": tag.first_name, "category": tag.category.name}
                for ht in self.status.hashtags
                for tag in [ht.tag]
                if tag and tag.first_name
            ],
            key=lambda x: x["name"],
        )

    def serialize_score(self) -> Any:
        return self.status.score

    def serialize_favorite_count(self) -> Any:
        return self.status.favorite_count

    def serialize_reply_count(self) -> Any:
        return self.status.reply_count

    def serialize_repost_count(self) -> Any:
        return self.status.repost_count

    def serialize_own_favorite(self) -> Any:
        return any(
            f.user_id == self.auth_user.user_id
            for f in self.status.favorites
        )

    def serialize_own_repost(self) -> Any:
        return any(
            r.user_id == self.auth_user.user_id
            for r in self.status.reposted_by
        )

    def serialize_is_repost(self) -> Any:
        # Check if this status was created by a repost
        return db.session.query(
            db.session.query(model.StatusRepost)
            .filter(model.StatusRepost.repost_status_id == self.status.status_id)
            .exists()
        ).scalar()

    def serialize_repost_original(self) -> Any:
        # Walk up the repost chain to find the original with content.
        # If the immediate parent has no text, look further up.
        repost_entry = (
            db.session.query(model.StatusRepost)
            .filter(model.StatusRepost.repost_status_id == self.status.status_id)
            .first()
        )
        if not repost_entry:
            return None
        original = (
            db.session.query(model.Status)
            .filter(model.Status.status_id == repost_entry.status_id)
            .one_or_none()
        )
        if not original:
            return None
        # Walk up chain: if original is itself a repost with no text, go deeper
        seen = {self.status.status_id, original.status_id}
        while True:
            parent_repost = (
                db.session.query(model.StatusRepost)
                .filter(model.StatusRepost.repost_status_id == original.status_id)
                .first()
            )
            if not parent_repost:
                break
            deeper = (
                db.session.query(model.Status)
                .filter(model.Status.status_id == parent_repost.status_id)
                .one_or_none()
            )
            if not deeper or deeper.status_id in seen:
                break
            seen.add(deeper.status_id)
            # If current original has text, stop here
            if original.text:
                break
            original = deeper
        return serialize_micro_status(original, self.auth_user)

    def serialize_is_reply(self) -> Any:
        return len(list(self.status.parent_replies)) > 0

    def serialize_reply_to(self) -> Any:
        replies = list(self.status.parent_replies)
        if not replies:
            return None
        return serialize_micro_status(replies[0].parent, self.auth_user)

    def serialize_replies(self) -> Any:
        replies = get_status_replies(self.status, self.auth_user)
        return [
            serialize_micro_status(r, self.auth_user)
            for r in replies
        ]


def serialize_status(
    status: Optional[model.Status],
    auth_user: model.User,
    options: List[str] = [],
) -> Optional[rest.Response]:
    if not status:
        return None
    return StatusSerializer(status, auth_user).serialize(options)


def serialize_micro_status(
    status: model.Status, auth_user: model.User
) -> Optional[rest.Response]:
    return serialize_status(
        status,
        auth_user=auth_user,
        options=["id", "text", "creationTime", "user"],
    )
