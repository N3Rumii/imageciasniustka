"""Mastodon /api/v1/accounts/* endpoints.

IMPORTANT: specific routes (verify_credentials, relationships, lookup)
MUST be defined BEFORE parameterized routes (/:id) so the routing table
checks them first.
"""

from typing import Dict

from szurubooru import db, errors, model, rest
from szurubooru.func import auth, users as users_func
from szurubooru.func import statuses as statuses_func
from szurubooru.mastodon.serializers import (
    serialize_account,
    serialize_relationship,
    serialize_status,
)


def _get_account_id(params: Dict[str, str]) -> str:
    return params["id"]


def _user_by_id(user_id: str) -> model.User:
    """Look up a user by string id, raise 404 if not found."""
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        raise errors.NotFoundError("Account not found.")
    user = (
        db.session.query(model.User)
        .filter(model.User.user_id == uid)
        .one_or_none()
    )
    if not user:
        raise errors.NotFoundError("Account not found.")
    return user


# =========================================================================
# SPECIFIC routes — must come before parameterized /:id routes
# =========================================================================

# -- verify_credentials ---------------------------------------------------

@rest.routes.get("/api/v1/accounts/verify_credentials/?")
def verify_credentials(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "users:view")
    return serialize_account(ctx.user, ctx.user)


# -- relationships --------------------------------------------------------

@rest.routes.get("/api/v1/accounts/relationships/?")
def account_relationships(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    id_list = ctx.get_param_as_list("id", default=[])
    results = []
    for uid in id_list:
        try:
            user = _user_by_id(uid)
            results.append(serialize_relationship(user, ctx.user))
        except errors.NotFoundError:
            pass
    return results


# -- lookup ---------------------------------------------------------------

@rest.routes.get("/api/v1/accounts/lookup/?")
def account_lookup(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    acct = ctx.get_param_as_string("acct")
    user = users_func.try_get_user_by_name(acct)
    if not user:
        raise errors.NotFoundError("Account not found.")
    return serialize_account(user, ctx.user)


# =========================================================================
# PARAMETERIZED routes — /:id and sub-resources
# =========================================================================

# -- GET /api/v1/accounts/:id ---------------------------------------------

@rest.routes.get("/api/v1/accounts/(?P<id>[^/]+)/?")
def get_account(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    user = _user_by_id(_get_account_id(params))
    return serialize_account(user, ctx.user)


# -- GET /api/v1/accounts/:id/statuses ------------------------------------

@rest.routes.get("/api/v1/accounts/(?P<id>[^/]+)/statuses/?")
def account_statuses(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    user = _user_by_id(_get_account_id(params))
    limit = min(ctx.get_param_as_int("limit", default=20), 40)
    offset = ctx.get_param_as_int("offset", default=0)
    max_id = ctx.get_param_as_string("max_id", default=None)
    if max_id:
        try:
            offset = int(max_id)
        except ValueError:
            pass
    results = statuses_func.get_status_timeline_by_user(
        user.name, offset=offset, limit=limit,
    )
    return [serialize_status(s, ctx.user) for s in results]


# -- GET /api/v1/accounts/:id/followers -----------------------------------

@rest.routes.get("/api/v1/accounts/(?P<id>[^/]+)/followers/?")
def account_followers(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    user = _user_by_id(_get_account_id(params))
    from szurubooru.model.user_follow import UserFollow as UF
    limit = min(ctx.get_param_as_int("limit", default=40), 80)
    offset = ctx.get_param_as_int("offset", default=0)
    follower_ids = (
        db.session.query(UF.follower_id)
        .filter(UF.followee_id == user.user_id)
        .offset(offset).limit(limit).all()
    )
    if not follower_ids:
        return []
    users = (
        db.session.query(model.User)
        .filter(model.User.user_id.in_([f[0] for f in follower_ids]))
        .all()
    )
    return [serialize_account(u, ctx.user) for u in users]


# -- GET /api/v1/accounts/:id/following -----------------------------------

@rest.routes.get("/api/v1/accounts/(?P<id>[^/]+)/following/?")
def account_following(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    user = _user_by_id(_get_account_id(params))
    from szurubooru.model.user_follow import UserFollow as UF
    limit = min(ctx.get_param_as_int("limit", default=40), 80)
    offset = ctx.get_param_as_int("offset", default=0)
    followee_ids = (
        db.session.query(UF.followee_id)
        .filter(UF.follower_id == user.user_id)
        .offset(offset).limit(limit).all()
    )
    if not followee_ids:
        return []
    users = (
        db.session.query(model.User)
        .filter(model.User.user_id.in_([f[0] for f in followee_ids]))
        .all()
    )
    return [serialize_account(u, ctx.user) for u in users]


# -- POST /api/v1/accounts/:id/follow -------------------------------------

@rest.routes.post("/api/v1/accounts/(?P<id>[^/]+)/follow/?")
def follow_account(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "users:follow")
    target = _user_by_id(_get_account_id(params))
    from datetime import datetime as _dt
    from szurubooru.model.user_follow import UserFollow as _UF
    existing = (
        db.session.query(_UF)
        .filter(
            _UF.follower_id == ctx.user.user_id,
            _UF.followee_id == target.user_id,
        )
        .one_or_none()
    )
    if not existing:
        follow = _UF()
        follow.follower_id = ctx.user.user_id
        follow.followee_id = target.user_id
        follow.creation_time = _dt.utcnow()
        ctx.session.add(follow)
        ctx.session.commit()
    return serialize_relationship(target, ctx.user)


# -- POST /api/v1/accounts/:id/unfollow -----------------------------------

@rest.routes.post("/api/v1/accounts/(?P<id>[^/]+)/unfollow/?")
def unfollow_account(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "users:follow")
    target = _user_by_id(_get_account_id(params))
    from szurubooru.model.user_follow import UserFollow as _UF
    existing = (
        ctx.session.query(_UF)
        .filter(
            _UF.follower_id == ctx.user.user_id,
            _UF.followee_id == target.user_id,
        )
        .one_or_none()
    )
    if existing:
        ctx.session.delete(existing)
        ctx.session.commit()
    return serialize_relationship(target, ctx.user)
