from datetime import datetime
from typing import Dict, List, Optional

from szurubooru import db, errors, model, rest
from szurubooru.func import auth, notifications, statuses, versions


def _get_status_id(params: Dict[str, str]) -> int:
    try:
        return int(params["status_id"])
    except (KeyError, TypeError, ValueError):
        raise errors.ValidationError(
            "Invalid status ID: %r." % params.get("status_id")
        )


def _get_status(
    params: Dict[str, str], user: Optional[model.User] = None
) -> model.Status:
    return statuses._get_status_by_id(_get_status_id(params))


def _serialize_status(
    ctx: rest.Context, status_obj: Optional[model.Status]
) -> rest.Response:
    return statuses.serialize_status(status_obj, ctx.user)


@rest.routes.get("/statuses/?")
def get_statuses(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:list")
    offset = ctx.get_param_as_int("offset", default=0)
    limit = min(ctx.get_param_as_int("limit", default=50), 100)
    tag = ctx.get_param_as_string("tag", default=None)
    user_name = ctx.get_param_as_string("user", default=None)
    feed = ctx.get_param_as_string("feed", default=None)
    sort = ctx.get_param_as_string("sort", default=None)

    if tag:
        result = statuses.get_status_timeline_by_tag(
            tag, ctx.user, offset, limit, sort=sort
        )
    elif user_name:
        result = statuses.get_status_timeline_by_user(
            user_name, offset, limit, sort=sort
        )
    else:
        result = statuses.get_status_timeline(
            ctx.user, offset, limit, feed=feed, sort=sort
        )

    return {
        "results": [
            statuses.serialize_status(s, ctx.user)
            for s in result
        ]
    }


@rest.routes.post("/statuses/?")
def create_status(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:create")

    # Rate limit: 5 seconds between statuses per user
    last_status = (
        db.session.query(model.Status)
        .filter(model.Status.user_id == ctx.user.user_id)
        .order_by(model.Status.creation_time.desc())
        .first()
    )
    if last_status:
        elapsed = (datetime.utcnow() - last_status.creation_time).total_seconds()
        if elapsed < 5:
            raise errors.ValidationError(
                "Please wait %d seconds before posting again."
                % (5 - int(elapsed))
            )

    text = ctx.get_param_as_string("text", default="")
    parent_status_id = ctx.get_param_as_int("parentId", default=None)
    private = ctx.get_param_as_bool("private", default=False)
    post_type = ctx.get_param_as_string("type", default="status")

    has_image = ctx.has_file("content")
    image_content = None
    if has_image:
        image_content = ctx.get_file("content")

    if not text.strip() and not has_image:
        raise errors.ValidationError(
            "Status must have text or an image."
        )

    status_obj = statuses.create_status(
        text=text.strip() or None,
        user=ctx.user,
        image_content=image_content,
        parent_status_id=parent_status_id,
        private=private,
        post_type=post_type,
    )
    ctx.session.add(status_obj)
    ctx.session.flush()
    # Notify parent status author (reply notification)
    if parent_status_id:
        parent = statuses._get_status_by_id(parent_status_id)
        if parent.user_id and parent.user_id != ctx.user.user_id:
            notifications.create_notification(
                user_id=parent.user_id,
                actor_id=ctx.user.user_id,
                notif_type=model.Notification.TYPE_STATUS_REPLY,
                status_id=status_obj.status_id,
            )
    # Notify followers of new status
    notifications.notify_followers_new_status(status_obj, ctx.user)
    ctx.session.commit()
    return _serialize_status(ctx, status_obj)


@rest.routes.get("/status/(?P<status_id>[^/]+)/?")
def get_status(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:view")
    status_obj = _get_status(params)
    return _serialize_status(ctx, status_obj)


@rest.routes.put("/status/(?P<status_id>[^/]+)/?")
def update_status(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:edit")
    status_obj = _get_status(params)
    if status_obj.user_id != ctx.user.user_id:
        raise auth.AuthError("You can only edit your own statuses.")
    versions.verify_version(status_obj, ctx)
    versions.bump_version(status_obj)
    text = ctx.get_param_as_string("text", default=None)
    statuses.update_status(status_obj, text)
    status_obj.last_edit_time = datetime.utcnow()
    ctx.session.commit()
    return _serialize_status(ctx, status_obj)


@rest.routes.delete("/status/(?P<status_id>[^/]+)/?")
def delete_status(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:delete")
    status_obj = _get_status(params)
    if (
        status_obj.user_id != ctx.user.user_id
        and not auth.has_privilege(ctx.user, "statuses:delete:any")
    ):
        raise auth.AuthError("You can only delete your own statuses.")
    statuses.delete_status(status_obj)
    ctx.session.commit()
    return {}


@rest.routes.get("/status/(?P<status_id>[^/]+)/replies/?")
def get_status_replies(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:view")
    status_obj = _get_status(params)
    replies = statuses.get_status_replies(status_obj, ctx.user)
    return {
        "results": [
            statuses.serialize_status(r, ctx.user)
            for r in replies
        ]
    }


@rest.routes.post("/status/(?P<status_id>[^/]+)/favorite/?")
def set_status_favorite(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:favorite")
    status_obj = _get_status(params)
    statuses.set_status_favorite(status_obj, ctx.user)
    ctx.session.commit()
    return _serialize_status(ctx, status_obj)


@rest.routes.delete("/status/(?P<status_id>[^/]+)/favorite/?")
def delete_status_favorite(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:favorite")
    status_obj = _get_status(params)
    statuses.delete_status_favorite(status_obj, ctx.user)
    ctx.session.commit()
    return _serialize_status(ctx, status_obj)


@rest.routes.post("/status/(?P<status_id>[^/]+)/repost/?")
def repost_status(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:repost")

    # Rate limit: 5 seconds between reposts per user
    last_status = (
        db.session.query(model.Status)
        .filter(model.Status.user_id == ctx.user.user_id)
        .order_by(model.Status.creation_time.desc())
        .first()
    )
    if last_status:
        elapsed = (datetime.utcnow() - last_status.creation_time).total_seconds()
        if elapsed < 5:
            raise errors.ValidationError(
                "Please wait %d seconds before posting again."
                % (5 - int(elapsed))
            )

    status_obj = _get_status(params)
    text = ctx.get_param_as_string("text", default=None)
    new_status = statuses.repost_status(status_obj, ctx.user, text=text)
    ctx.session.commit()
    return _serialize_status(ctx, new_status)


@rest.routes.delete("/status/(?P<status_id>[^/]+)/repost/?")
def undo_repost(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:repost")
    status_obj = _get_status(params)
    statuses.undo_repost(status_obj, ctx.user)
    ctx.session.commit()
    return {}
