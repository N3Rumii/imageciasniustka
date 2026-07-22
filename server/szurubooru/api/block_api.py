"""Block API — manage user blocking."""

from typing import Dict

from szurubooru import db, model, rest
from szurubooru.func import auth, blocks, serialization, users


@rest.routes.post("/user/(?P<user_name>[^/]+)/block/?")
def block_user(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    """Block a user."""
    auth.verify_privilege(ctx.user, "users:view")
    target = users.get_user_by_name(params["user_name"])
    blocks.block_user(ctx.user, target)
    ctx.session.commit()
    return {"ok": True, "blocked": True}


@rest.routes.delete("/user/(?P<user_name>[^/]+)/block/?")
def unblock_user(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    """Unblock a user."""
    auth.verify_privilege(ctx.user, "users:view")
    target = users.get_user_by_name(params["user_name"])
    blocks.unblock_user(ctx.user, target)
    ctx.session.commit()
    return {"ok": True, "blocked": False}


@rest.routes.get("/user/(?P<user_name>[^/]+)/block/?")
def check_block(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    """Check if current user has blocked a specific user."""
    auth.verify_privilege(ctx.user, "users:view")
    target = users.get_user_by_name(params["user_name"])
    blocked = blocks.is_blocked_by(ctx.user.user_id, target.user_id)
    return {"blocked": blocked}


@rest.routes.get("/user-blocks/?")
def get_blocked_users(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    """List all users blocked by the current user."""
    auth.verify_privilege(ctx.user, "users:view")
    blocked = blocks.get_blocked_users(ctx.user)
    return {
        "results": [
            users.serialize_user(
                u,
                ctx.user,
                options=serialization.get_serialization_options(ctx),
            )
            for u in blocked
        ]
    }
