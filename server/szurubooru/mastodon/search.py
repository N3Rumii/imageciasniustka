"""Mastodon /api/v2/search endpoint.

Searches across accounts, statuses, and hashtags using ciasniutka's
existing user, status, and tag lookup systems.
"""

from typing import Dict

from szurubooru import model, rest
from szurubooru.func import auth, users as users_func
from szurubooru.func import statuses as statuses_func
from szurubooru.mastodon.serializers import serialize_account, serialize_status


@rest.routes.get("/api/v2/search/?")
def search(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    q = ctx.get_param_as_string("q", default="").strip()
    search_type = ctx.get_param_as_string("type", default=None)
    limit = min(ctx.get_param_as_int("limit", default=20), 40)
    resolve = ctx.get_param_as_bool("resolve", default=False)

    if not q:
        return {"accounts": [], "statuses": [], "hashtags": []}

    accounts = []
    statuses = []
    hashtags = []

    # Account search
    if search_type is None or "accounts" in search_type:
        auth.verify_privilege(ctx.user, "users:list")
        # Try exact username match first
        user = users_func.try_get_user_by_name(q)
        if user:
            accounts.append(serialize_account(user, ctx.user))
        # Partial name search via LIKE
        from szurubooru import db
        partial_users = (
            db.session.query(model.User)
            .filter(model.User.name.ilike("%" + q + "%"))
            .limit(limit)
            .all()
        )
        for u in partial_users:
            if u not in [user] and u.name:  # avoid duplicating the exact match
                accounts.append(serialize_account(u, ctx.user))

    # Hashtag search
    if search_type is None or "hashtags" in search_type:
        from szurubooru import db
        tag_name = q.lstrip("#")
        tags = (
            db.session.query(model.Tag)
            .join(model.TagName)
            .filter(model.TagName.name.ilike("%" + tag_name + "%"))
            .limit(limit)
            .all()
        )
        for tag in tags:
            if tag.first_name:
                hashtags.append({
                    "name": tag.first_name,
                    "url": "",
                    "history": [],
                    "following": False,
                })

    # Status search (by text content)
    if search_type is None or "statuses" in search_type:
        auth.verify_privilege(ctx.user, "statuses:list")
        from szurubooru import db
        status_results = (
            db.session.query(model.Status)
            .filter(
                model.Status.text.ilike("%" + q + "%"),
                model.Status.private == False,  # noqa: E712
            )
            .order_by(model.Status.creation_time.desc())
            .limit(limit)
            .all()
        )
        statuses = [
            serialize_status(s, ctx.user) for s in status_results
        ]

    return {
        "accounts": accounts,
        "statuses": statuses,
        "hashtags": hashtags,
    }
