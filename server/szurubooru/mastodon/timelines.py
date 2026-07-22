"""Mastodon /api/v1/timelines/* endpoints."""

from typing import Dict, List

from szurubooru import rest
from szurubooru.func import auth, statuses as statuses_func
from szurubooru.mastodon.serializers import serialize_status


def _paginated_statuses(
    ctx: rest.Context,
    results: List,
) -> List[dict]:
    """Serialize a list of Status objects into Mastodon format."""
    return [serialize_status(s, ctx.user) for s in results]


# ---------------------------------------------------------------------------
# GET /api/v1/timelines/public
# ---------------------------------------------------------------------------

@rest.routes.get("/api/v1/timelines/public/?")
def public_timeline(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:list")
    limit = min(ctx.get_param_as_int("limit", default=20), 40)
    offset = ctx.get_param_as_int("offset", default=0)
    only_media = ctx.get_param_as_bool("only_media", default=False)
    sort = ctx.get_param_as_string("sort", default=None)

    local = ctx.get_param_as_bool("local", default=None)
    # local/remote filtering has no meaning in a non-federated instance,
    # so we ignore these parameters.

    results = statuses_func.get_status_timeline(
        ctx.user, offset=offset, limit=limit, sort=sort,
    )

    if only_media:
        results = [s for s in results if s.post_id is not None]

    return _paginated_statuses(ctx, results)


# ---------------------------------------------------------------------------
# GET /api/v1/timelines/home
# ---------------------------------------------------------------------------

@rest.routes.get("/api/v1/timelines/home/?")
def home_timeline(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:list")
    limit = min(ctx.get_param_as_int("limit", default=20), 40)
    offset = ctx.get_param_as_int("offset", default=0)
    sort = ctx.get_param_as_string("sort", default=None)

    results = statuses_func.get_status_timeline(
        ctx.user, offset=offset, limit=limit, feed="myfeed", sort=sort,
    )

    return _paginated_statuses(ctx, results)


# ---------------------------------------------------------------------------
# GET /api/v1/timelines/tag/:hashtag
# ---------------------------------------------------------------------------

@rest.routes.get("/api/v1/timelines/tag/(?P<hashtag>[^/]+)/?")
def tag_timeline(
    ctx: rest.Context, params: Dict[str, str]
) -> rest.Response:
    auth.verify_privilege(ctx.user, "statuses:list")
    limit = min(ctx.get_param_as_int("limit", default=20), 40)
    offset = ctx.get_param_as_int("offset", default=0)
    sort = ctx.get_param_as_string("sort", default=None)
    only_media = ctx.get_param_as_bool("only_media", default=False)

    tag_name = params["hashtag"]
    results = statuses_func.get_status_timeline_by_tag(
        tag_name, ctx.user, offset=offset, limit=limit, sort=sort,
    )

    if only_media:
        results = [s for s in results if s.post_id is not None]

    return _paginated_statuses(ctx, results)
