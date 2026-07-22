from typing import Dict

from szurubooru import model, rest
from szurubooru.func import auth, notifications


@rest.routes.get("/notifications/?")
def get_notifications(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "notifications:list")
    offset = ctx.get_param_as_int("offset", default=0)
    limit = min(ctx.get_param_as_int("limit", default=50), 100)
    result = notifications.get_notifications(ctx.user, offset, limit)
    return {
        "results": [
            notifications.serialize_notification(n, ctx.user)
            for n in result
        ]
    }


@rest.routes.get("/notifications/unread-count/?")
def get_unread_count(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "notifications:list")
    return {"count": notifications.get_unread_count(ctx.user)}


@rest.routes.post("/notification/(?P<notification_id>[^/]+)/read/?")
def mark_notification_read(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "notifications:edit")
    try:
        notification_id = int(params["notification_id"])
    except (KeyError, TypeError, ValueError):
        raise notifications.NotificationNotFoundError(
            "Invalid notification ID."
        )
    notifications.mark_read(notification_id, ctx.user)
    ctx.session.commit()
    return {}


@rest.routes.post("/notifications/read-all/?")
def mark_all_read(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "notifications:edit")
    notifications.mark_all_read(ctx.user)
    ctx.session.commit()
    return {}


@rest.routes.delete("/notification/(?P<notification_id>[^/]+)/?")
def dismiss_notification(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "notifications:edit")
    try:
        notification_id = int(params["notification_id"])
    except (KeyError, TypeError, ValueError):
        raise notifications.NotificationNotFoundError(
            "Invalid notification ID."
        )
    notifications.dismiss_notification(notification_id, ctx.user)
    ctx.session.commit()
    return {}


@rest.routes.delete("/notifications/dismiss-all/?")
def dismiss_all(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "notifications:edit")
    notifications.dismiss_all(ctx.user)
    ctx.session.commit()
    return {}
