"""Mastodon /api/v1/notifications/* endpoints."""

from typing import Dict

from szurubooru import rest
from szurubooru.func import auth, notifications as notif_func
from szurubooru.mastodon.serializers import serialize_notification


@rest.routes.get("/api/v1/notifications/?")
def get_notifications(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "notifications:list")
    limit = min(ctx.get_param_as_int("limit", default=20), 40)
    offset = ctx.get_param_as_int("offset", default=0)
    results = notif_func.get_notifications(
        ctx.user, offset=offset, limit=limit
    )
    return [
        serialize_notification(n, ctx.user) for n in results
    ]


@rest.routes.post("/api/v1/notifications/(?P<id>[^/]+)/dismiss/?")
def dismiss_notification(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "notifications:edit")
    try:
        notif_id = int(params["id"])
    except (KeyError, ValueError, TypeError):
        raise notif_func.NotificationNotFoundError(
            "Invalid notification ID."
        )
    notif_func.dismiss_notification(notif_id, ctx.user)
    ctx.session.commit()
    return {}


@rest.routes.post("/api/v1/notifications/clear/?")
def clear_notifications(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "notifications:edit")
    notif_func.dismiss_all(ctx.user)
    ctx.session.commit()
    return {}
