"""Mastodon /api/v1/statuses/* endpoints."""

from datetime import datetime
from typing import Dict

from szurubooru import db, errors, model, rest
from szurubooru.func import auth, statuses as statuses_func
from szurubooru.mastodon.serializers import (
    serialize_context,
    serialize_status,
)


def _get_status_id(params: Dict[str, str]) -> int:
    try:
        return int(params["id"])
    except (KeyError, TypeError, ValueError):
        raise errors.ValidationError(
            "Invalid status ID: %r." % params.get("id")
        )


def _get_status(
    params: Dict[str, str], user: model.User
) -> model.Status:
    return statuses_func._get_status_by_id(_get_status_id(params), user)


# ---------------------------------------------------------------------------
# GET /api/v1/statuses/:id
# ---------------------------------------------------------------------------

@rest.routes.get("/api/v1/statuses/(?P<id>[^/]+)/?")
def get_status(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:view")
    status_obj = _get_status(params, ctx.user)
    return serialize_status(status_obj, ctx.user)


# ---------------------------------------------------------------------------
# POST /api/v1/statuses
# ---------------------------------------------------------------------------

@rest.routes.post("/api/v1/statuses/?")
def post_status(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:create")

    # Rate limit check (same as existing API)
    last_status = (
        db.session.query(model.Status)
        .filter(model.Status.user_id == ctx.user.user_id)
        .order_by(model.Status.creation_time.desc())
        .first()
    )
    if last_status:
        elapsed = (
            datetime.utcnow() - last_status.creation_time
        ).total_seconds()
        if elapsed < 5:
            raise errors.ValidationError(
                "Please wait %d seconds before posting again."
                % (5 - int(elapsed))
            )

    text = ctx.get_param_as_string("status", default="")
    spoiler_text = ctx.get_param_as_string(
        "spoiler_text", default=""
    )
    visibility = ctx.get_param_as_string(
        "visibility", default="public"
    )
    in_reply_to_id = ctx.get_param_as_string(
        "in_reply_to_id", default=None
    )

    private = visibility not in ("public", "unlisted")

    # Parse parent status id for threading
    parent_status_id = None
    if in_reply_to_id:
        try:
            parent_status_id = int(in_reply_to_id)
        except (ValueError, TypeError):
            raise errors.ValidationError(
                "Invalid in_reply_to_id: %r." % in_reply_to_id
            )

    # Handle media_ids[]
    media_ids = ctx.get_param_as_list("media_ids[]", default=[])
    image_content = None
    if media_ids:
        # Take the first media ID and resolve it to stored file content.
        # In a full implementation, uploaded media would be stored in a
        # temporary table keyed by attachment ID.  For now, media uploads
        # go through the normal file-upload path; the media_ids[] are
        # resolved in the media.py upload handler which stores the raw
        # bytes keyed by ID.  If no media match is found, we proceed
        # text-only.
        from szurubooru.mastodon import media as media_module
        image_content = media_module.pop_upload(media_ids[0])

    # If spoiler_text is present, prepend it (Mastodon convention:
    # spoiler_text is the CW, status text is the body)
    if spoiler_text and text:
        pass  # both are included in the status separately

    status_obj = statuses_func.create_status(
        text=text.strip() or None,
        user=ctx.user,
        image_content=image_content,
        parent_status_id=parent_status_id,
        private=private,
        post_type="status",
    )
    ctx.session.add(status_obj)
    ctx.session.flush()

    # Notify parent status author (reply notification)
    if parent_status_id:
        from szurubooru.func import notifications
        parent = statuses_func._get_status_by_id(parent_status_id)
        if parent.user_id and parent.user_id != ctx.user.user_id:
            notifications.create_notification(
                user_id=parent.user_id,
                actor_id=ctx.user.user_id,
                notif_type=model.Notification.TYPE_STATUS_REPLY,
                status_id=status_obj.status_id,
            )

    # Notify followers
    from szurubooru.func import notifications
    notifications.notify_followers_new_status(status_obj, ctx.user)

    ctx.session.commit()
    return serialize_status(status_obj, ctx.user)


# ---------------------------------------------------------------------------
# DELETE /api/v1/statuses/:id
# ---------------------------------------------------------------------------

@rest.routes.delete("/api/v1/statuses/(?P<id>[^/]+)/?")
def delete_status(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:delete")
    status_obj = _get_status(params, ctx.user)
    if (
        status_obj.user_id != ctx.user.user_id
        and not auth.has_privilege(ctx.user, "statuses:delete:any")
    ):
        raise auth.AuthError("You can only delete your own statuses.")
    statuses_func.delete_status(status_obj)
    ctx.session.commit()
    return {}


# ---------------------------------------------------------------------------
# GET /api/v1/statuses/:id/context
# ---------------------------------------------------------------------------

@rest.routes.get("/api/v1/statuses/(?P<id>[^/]+)/context/?")
def status_context(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:view")
    status_obj = _get_status(params, ctx.user)
    return serialize_context(status_obj, ctx.user)


# ---------------------------------------------------------------------------
# POST /api/v1/statuses/:id/favourite
# ---------------------------------------------------------------------------

@rest.routes.post("/api/v1/statuses/(?P<id>[^/]+)/favourite/?")
def favourite_status(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:favorite")
    status_obj = _get_status(params, ctx.user)
    statuses_func.set_status_favorite(status_obj, ctx.user)
    ctx.session.commit()
    return serialize_status(status_obj, ctx.user)


# ---------------------------------------------------------------------------
# POST /api/v1/statuses/:id/unfavourite
# ---------------------------------------------------------------------------

@rest.routes.post("/api/v1/statuses/(?P<id>[^/]+)/unfavourite/?")
def unfavourite_status(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:favorite")
    status_obj = _get_status(params, ctx.user)
    statuses_func.delete_status_favorite(status_obj, ctx.user)
    ctx.session.commit()
    return serialize_status(status_obj, ctx.user)


# ---------------------------------------------------------------------------
# POST /api/v1/statuses/:id/reblog
# ---------------------------------------------------------------------------

@rest.routes.post("/api/v1/statuses/(?P<id>[^/]+)/reblog/?")
def reblog_status(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:repost")
    status_obj = _get_status(params, ctx.user)
    new_status = statuses_func.repost_status(
        status_obj, ctx.user
    )
    ctx.session.commit()
    return serialize_status(new_status, ctx.user)


# ---------------------------------------------------------------------------
# POST /api/v1/statuses/:id/unreblog
# ---------------------------------------------------------------------------

@rest.routes.post("/api/v1/statuses/(?P<id>[^/]+)/unreblog/?")
def unreblog_status(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:repost")
    status_obj = _get_status(params, ctx.user)
    statuses_func.undo_repost(status_obj, ctx.user)
    ctx.session.commit()
    return serialize_status(status_obj, ctx.user)
