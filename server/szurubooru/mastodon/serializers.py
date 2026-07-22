"""Mastodon JSON shape serializers.

Each serializer converts a ciasniutka model instance into a dict
matching the Mastodon REST API response format.  All date-times are
ISO-8601 with a trailing "Z" (UTC).

Convention: every public function is named `serialize_<entity>()`
and returns `Optional[dict]`.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from szurubooru import config, db, model
from szurubooru.func import users as users_func
from szurubooru.func import posts as posts_func
from szurubooru.func import statuses as statuses_func


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.isoformat("T") + "Z"


def _text_to_html(text: Optional[str]) -> str:
    """Wrap plain text in <p>, preserve newlines as <br>."""
    if not text:
        return ""
    import html as _html
    escaped = _html.escape(text)
    paras = escaped.split("\n\n")
    out = []
    for p in paras:
        lines = p.split("\n")
        out.append("<p>" + "<br/>".join(lines) + "</p>")
    return "".join(out)


def _data_url(path: str) -> str:
    base = config.config["data_url"].rstrip("/")
    return f"{base}/{path.lstrip('/')}"


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

def serialize_account(
    user: model.User,
    auth_user: Optional[model.User] = None,
) -> dict:
    """Serialize a User into a Mastodon Account dict."""
    avatar_url = users_func.get_avatar_url(user) if user.name else ""
    header_url = user.profile_header_url or ""

    # statuses_count
    statuses_count = (
        db.session.query(model.Status)
        .filter(model.Status.user_id == user.user_id)
        .count()
    )

    # last_status_at
    last_status = (
        db.session.query(model.Status.creation_time)
        .filter(model.Status.user_id == user.user_id)
        .order_by(model.Status.creation_time.desc())
        .first()
    )
    last_status_at = _iso(last_status[0]) if last_status else None

    # fields from profile_links (format: "name:url" per line)
    fields = []
    if user.profile_links:
        for line in user.profile_links.split("\n"):
            line = line.strip()
            if ":" in line:
                name, _, value = line.partition(":")
                fields.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "verified_at": None,
                })

    return {
        "id": str(user.user_id),
        "username": user.name or "",
        "acct": user.name or "",
        "display_name": user.name or "",
        "locked": False,
        "bot": False,
        "discoverable": True,
        "group": False,
        "created_at": _iso(user.creation_time),
        "note": _text_to_html(user.profile_bio or ""),
        "url": _data_url(f"user/{user.name}"),
        "avatar": avatar_url,
        "avatar_static": avatar_url,
        "header": header_url,
        "header_static": header_url,
        "followers_count": user.followers_count,
        "following_count": user.following_count,
        "statuses_count": statuses_count,
        "last_status_at": last_status_at,
        "emojis": [],
        "fields": fields,
    }


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def serialize_status(
    status: model.Status,
    auth_user: Optional[model.User] = None,
) -> dict:
    """Serialize a Status into a Mastodon Status dict."""

    # parent / reply info
    in_reply_to_id = None
    in_reply_to_account_id = None
    parent_replies = list(status.parent_replies)
    if parent_replies:
        parent_status = parent_replies[0].parent
        in_reply_to_id = str(parent_status.status_id)
        if parent_status.user_id:
            in_reply_to_account_id = str(parent_status.user_id)

    # media attachments from linked Post
    media_attachments = []
    if status.post_id and status.post:
        media_attachments.append(_serialize_post_as_attachment(status.post))

    # tags from hashtags
    tags = []
    for ht in status.hashtags:
        tag = ht.tag
        if tag and tag.first_name:
            tags.append({
                "name": tag.first_name,
                "url": _data_url(f"tags/{tag.first_name}"),
            })

    # visibility
    visibility = "private" if status.private else "public"

    # reblog
    reblog = None
    if statuses_func.StatusSerializer(status, auth_user).serialize_is_repost():
        repost_entry = (
            db.session.query(model.StatusRepost)
            .filter(model.StatusRepost.repost_status_id == status.status_id)
            .first()
        )
        if repost_entry:
            original = (
                db.session.query(model.Status)
                .filter(model.Status.status_id == repost_entry.status_id)
                .one_or_none()
            )
            if original:
                reblog = serialize_status(original, auth_user)

    # own flags
    own_fav = False
    own_repost = False
    if auth_user and auth_user.user_id:
        own_fav = any(
            f.user_id == auth_user.user_id
            for f in status.favorites
        )
        own_repost = any(
            r.user_id == auth_user.user_id
            for r in status.reposted_by
        )

    return {
        "id": str(status.status_id),
        "created_at": _iso(status.creation_time),
        "in_reply_to_id": in_reply_to_id,
        "in_reply_to_account_id": in_reply_to_account_id,
        "sensitive": False,
        "spoiler_text": "",
        "visibility": visibility,
        "language": None,
        "uri": _data_url(f"status/{status.status_id}"),
        "url": _data_url(f"status/{status.status_id}"),
        "replies_count": status.reply_count,
        "reblogs_count": status.repost_count,
        "favourites_count": status.favorite_count,
        "favourited": own_fav,
        "reblogged": own_repost,
        "muted": False,
        "bookmarked": False,
        "content": _text_to_html(status.text),
        "reblog": reblog,
        "application": {"name": "ciasniutka", "website": None},
        "account": serialize_account(status.user, auth_user)
                   if status.user else {},
        "media_attachments": media_attachments,
        "mentions": [],
        "tags": tags,
        "emojis": [],
        "card": None,
        "poll": None,
        "pinned": False,
    }


def _serialize_post_as_attachment(post: model.Post) -> dict:
    """Serialize a Post into a Mastodon MediaAttachment dict."""
    post_type = post.type or "image"
    if post_type in ("image", "image-animated"):
        mtype = "image"
    elif post_type in ("video", "flash"):
        mtype = "video"
    elif post_type == "audio":
        mtype = "audio"
    else:
        mtype = "image"

    content_url = posts_func.get_post_content_url(post)
    thumbnail_url = posts_func.get_post_thumbnail_url(post)

    return {
        "id": str(post.post_id),
        "type": mtype,
        "url": content_url,
        "preview_url": thumbnail_url,
        "remote_url": None,
        "preview_remote_url": None,
        "text_url": None,
        "meta": {"original": {}},
        "description": None,
        "blurhash": None,
    }


# ---------------------------------------------------------------------------
# Relationship
# ---------------------------------------------------------------------------

def serialize_relationship(
    user: model.User,
    auth_user: model.User,
) -> dict:
    """Serialize the relationship between auth_user and another user."""
    if not auth_user or not auth_user.user_id:
        return {
            "id": str(user.user_id),
            "following": False,
            "followed_by": False,
            "blocking": False,
            "blocked_by": False,
            "muting": False,
            "muting_notifications": False,
            "requested": False,
            "domain_blocking": False,
            "showing_reblogs": True,
            "endorsed": False,
            "notifying": False,
            "note": "",
        }

    from szurubooru.model.user_follow import UserFollow as UF

    following = (
        db.session.query(UF)
        .filter(
            UF.follower_id == auth_user.user_id,
            UF.followee_id == user.user_id,
        )
        .one_or_none()
        is not None
    )
    followed_by = (
        db.session.query(UF)
        .filter(
            UF.follower_id == user.user_id,
            UF.followee_id == auth_user.user_id,
        )
        .one_or_none()
        is not None
    )

    return {
        "id": str(user.user_id),
        "following": following,
        "followed_by": followed_by,
        "blocking": False,
        "blocked_by": False,
        "muting": False,
        "muting_notifications": False,
        "requested": False,
        "domain_blocking": False,
        "showing_reblogs": True,
        "endorsed": False,
        "notifying": False,
        "note": "",
    }


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

_NOTIF_TYPE_MAP: Dict[str, str] = {
    model.Notification.TYPE_STATUS_FAVORITE: "favourite",
    model.Notification.TYPE_STATUS_REPLY: "mention",
    model.Notification.TYPE_NEW_STATUS: "status",
    model.Notification.TYPE_NEW_POST: "status",
    model.Notification.TYPE_POST_FAVORITE: "favourite",
    model.Notification.TYPE_POST_COMMENT: "mention",
    model.Notification.TYPE_POST_LIKE: "favourite",
    model.Notification.TYPE_POST_DISLIKE: "reblog",
}


def serialize_notification(
    notif: model.Notification,
    auth_user: model.User,
) -> dict:
    mastodon_type = _NOTIF_TYPE_MAP.get(notif.type, "mention")

    account = (
        serialize_account(notif.actor, auth_user)
        if notif.actor
        else None
    )

    status = None
    if notif.status_id and notif.status:
        status = serialize_status(notif.status, auth_user)

    return {
        "id": str(notif.notification_id),
        "type": mastodon_type,
        "created_at": _iso(notif.creation_time),
        "account": account,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Context (ancestors + descendants for thread view)
# ---------------------------------------------------------------------------

def serialize_context(
    status: model.Status,
    auth_user: model.User,
) -> dict:
    """Build Mastodon Context for a status thread."""
    # Ancestors: walk up the parent chain
    ancestors = []
    seen = {status.status_id}
    current = status
    while True:
        parent_replies = list(current.parent_replies)
        if not parent_replies:
            break
        parent = parent_replies[0].parent
        if parent.status_id in seen:
            break
        seen.add(parent.status_id)
        ancestors.append(serialize_status(parent, auth_user))
        current = parent
    ancestors.reverse()  # oldest first

    # Descendants: direct replies
    replies = statuses_func.get_status_replies(status, auth_user)
    descendants = [
        serialize_status(r, auth_user) for r in replies
    ]

    return {
        "ancestors": ancestors,
        "descendants": descendants,
    }


# ---------------------------------------------------------------------------
# Instance
# ---------------------------------------------------------------------------

def serialize_instance_v1() -> dict:
    """Mastodon v1 instance info."""
    from szurubooru.func import posts as _posts
    from szurubooru.func import users as _users

    return {
        "uri": config.config["data_url"].rstrip("/"),
        "title": config.config["name"],
        "short_description": "",
        "description": "",
        "email": config.config.get("contact_email", ""),
        "version": "4.0.0 (ciasniutka mastodon compat)",
        "urls": {},
        "stats": {
            "user_count": _users.get_user_count(),
            "status_count": _posts.get_post_count(),
            "domain_count": 0,
        },
        "thumbnail": None,
        "languages": ["en"],
        "registrations": False,
        "approval_required": False,
        "invites_enabled": False,
    }


def serialize_instance_v2() -> dict:
    """Mastodon v2 instance info."""
    v1 = serialize_instance_v1()
    v1.update({
        "configuration": {
            "urls": {},
            "accounts": {"max_featured_tags": 0},
            "statuses": {
                "max_characters": 1000,
                "max_media_attachments": 1,
                "characters_reserved_per_url": 23,
            },
            "media_attachments": {
                "supported_mime_types": [
                    "image/jpeg", "image/png", "image/gif",
                    "image/webp", "image/avif", "video/mp4",
                ],
                "image_size_limit": 20971520,
                "image_matrix_limit": 16777216,
                "video_size_limit": 52428800,
                "video_frame_rate_limit": 60,
                "video_matrix_limit": 2304000,
            },
            "polls": {"max_options": 0, "max_characters_per_option": 0,
                      "min_expiration": 0, "max_expiration": 0},
            "translation": {"enabled": False},
        },
        "rules": [],
        "domain_blocks": {},
    })
    return v1
