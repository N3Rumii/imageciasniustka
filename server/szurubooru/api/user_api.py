from datetime import datetime
from typing import Any, Dict

from szurubooru import db, model, rest, search
from szurubooru.func import auth, serialization, users, versions

_search_executor = search.Executor(search.configs.UserSearchConfig())


def _serialize(
    ctx: rest.Context, user: model.User, **kwargs: Any
) -> rest.Response:
    return users.serialize_user(
        user,
        ctx.user,
        options=serialization.get_serialization_options(ctx),
        **kwargs
    )


@rest.routes.get("/users/?")
def get_users(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "users:list")
    return _search_executor.execute_and_serialize(
        ctx, lambda user: _serialize(ctx, user)
    )


@rest.routes.post("/users/?")
def create_user(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    if ctx.user.user_id is None:
        auth.verify_privilege(ctx.user, "users:create:self")
    else:
        auth.verify_privilege(ctx.user, "users:create:any")

    name = ctx.get_param_as_string("name")
    password = ctx.get_param_as_string("password")
    email = ctx.get_param_as_string("email", default="")
    user = users.create_user(name, password, email)
    if ctx.has_param("rank"):
        users.update_user_rank(user, ctx.get_param_as_string("rank"), ctx.user)
    if ctx.has_param("avatarStyle"):
        users.update_user_avatar(
            user,
            ctx.get_param_as_string("avatarStyle"),
            ctx.get_file("avatar", default=b""),
        )
    ctx.session.add(user)
    ctx.session.commit()

    return _serialize(ctx, user, force_show_email=True)


@rest.routes.get("/user/(?P<user_name>[^/]+)/?")
def get_user(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    user = users.get_user_by_name(params["user_name"])
    if ctx.user.user_id != user.user_id:
        auth.verify_privilege(ctx.user, "users:view")
    return _serialize(ctx, user)


@rest.routes.put("/user/(?P<user_name>[^/]+)/?")
def update_user(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    user = users.get_user_by_name(params["user_name"])
    versions.verify_version(user, ctx)
    versions.bump_version(user)
    infix = "self" if ctx.user.user_id == user.user_id else "any"
    if ctx.has_param("name"):
        auth.verify_privilege(ctx.user, "users:edit:%s:name" % infix)
        users.update_user_name(user, ctx.get_param_as_string("name"))
    if ctx.has_param("password"):
        auth.verify_privilege(ctx.user, "users:edit:%s:pass" % infix)
        users.update_user_password(user, ctx.get_param_as_string("password"))
    if ctx.has_param("email"):
        auth.verify_privilege(ctx.user, "users:edit:%s:email" % infix)
        users.update_user_email(user, ctx.get_param_as_string("email"))
    if ctx.has_param("rank"):
        auth.verify_privilege(ctx.user, "users:edit:%s:rank" % infix)
        users.update_user_rank(user, ctx.get_param_as_string("rank"), ctx.user)
    if ctx.has_param("avatarStyle"):
        auth.verify_privilege(ctx.user, "users:edit:%s:avatar" % infix)
        users.update_user_avatar(
            user,
            ctx.get_param_as_string("avatarStyle"),
            ctx.get_file("avatar", default=b""),
        )
    ctx.session.commit()
    return _serialize(ctx, user)


@rest.routes.delete("/user/(?P<user_name>[^/]+)/?")
def delete_user(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    user = users.get_user_by_name(params["user_name"])
    versions.verify_version(user, ctx)
    infix = "self" if ctx.user.user_id == user.user_id else "any"
    auth.verify_privilege(ctx.user, "users:delete:%s" % infix)
    ctx.session.delete(user)
    ctx.session.commit()
    return {}


@rest.routes.post("/user/(?P<user_name>[^/]+)/follow/?")
def follow_user(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    auth.verify_privilege(ctx.user, "users:follow")
    target_user = users.get_user_by_name(params["user_name"])
    if target_user.user_id == ctx.user.user_id:
        raise users.InvalidFollowError("You cannot follow yourself.")
    existing = (
        db.session.query(model.UserFollow)
        .filter(
            model.UserFollow.follower_id == ctx.user.user_id,
            model.UserFollow.followee_id == target_user.user_id,
        )
        .one_or_none()
    )
    if existing:
        raise users.AlreadyFollowingError(
            "You are already following %r." % target_user.name
        )
    follow = model.UserFollow()
    follow.follower_id = ctx.user.user_id
    follow.followee_id = target_user.user_id
    follow.creation_time = datetime.utcnow()
    db.session.add(follow)
    ctx.session.commit()
    return _serialize(ctx, target_user)


@rest.routes.delete("/user/(?P<user_name>[^/]+)/follow/?")
def unfollow_user(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "users:follow")
    target_user = users.get_user_by_name(params["user_name"])
    existing = (
        db.session.query(model.UserFollow)
        .filter(
            model.UserFollow.follower_id == ctx.user.user_id,
            model.UserFollow.followee_id == target_user.user_id,
        )
        .one_or_none()
    )
    if not existing:
        raise users.NotFollowingError(
            "You are not following %r." % target_user.name
        )
    db.session.delete(existing)
    ctx.session.commit()
    return _serialize(ctx, target_user)


@rest.routes.get("/user/(?P<user_name>[^/]+)/following/?")
def get_user_following(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    target_user = users.get_user_by_name(params["user_name"])
    follows = (
        db.session.query(model.UserFollow)
        .filter(model.UserFollow.follower_id == target_user.user_id)
        .all()
    )
    followee_ids = [f.followee_id for f in follows]
    if not followee_ids:
        return {"results": []}
    followees = (
        db.session.query(model.User)
        .filter(model.User.user_id.in_(followee_ids))
        .all()
    )
    return {
        "results": [
            _serialize(ctx, u, force_show_email=False)
            for u in followees
        ]
    }


@rest.routes.get("/user/(?P<user_name>[^/]+)/followers/?")
def get_user_followers(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    target_user = users.get_user_by_name(params["user_name"])
    follows = (
        db.session.query(model.UserFollow)
        .filter(model.UserFollow.followee_id == target_user.user_id)
        .all()
    )
    follower_ids = [f.follower_id for f in follows]
    if not follower_ids:
        return {"results": []}
    followers = (
        db.session.query(model.User)
        .filter(model.User.user_id.in_(follower_ids))
        .all()
    )
    return {
        "results": [
            _serialize(ctx, u, force_show_email=False)
            for u in followers
        ]
    }


@rest.routes.put("/user/(?P<user_name>[^/]+)/profile/?")
def update_user_profile(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    user = users.get_user_by_name(params["user_name"])
    if ctx.user.user_id != user.user_id:
        raise auth.AuthError("You can only edit your own profile.")
    users.save_profile(
        user,
        bio=ctx.get_param_as_string("bio", default=None),
        css=ctx.get_param_as_string("css", default=None),
        accent_color=ctx.get_param_as_string("accentColor", default=None),
        layout=ctx.get_param_as_string("layout", default=None),
        embeds=ctx.get_param_as_string("embeds", default=None),
        about=ctx.get_param_as_string("about", default=None),
        links=ctx.get_param_as_string("links", default=None),
    )
    ctx.session.commit()
    return _serialize(ctx, user)


@rest.routes.post("/user/(?P<user_name>[^/]+)/profile-header/?")
def upload_profile_header(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    user = users.get_user_by_name(params["user_name"])
    if ctx.user.user_id != user.user_id:
        raise auth.AuthError("You can only edit your own profile.")
    content = ctx.get_file("content")
    if not content:
        raise errors.ValidationError("Header image required.")
    url = users.upload_header(user, content)
    ctx.session.commit()
    return {"url": url}
