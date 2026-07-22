from datetime import datetime
from typing import Dict, List, Optional

from szurubooru import db, model, rest, search
from szurubooru.func import auth, pools, serialization, snapshots, versions

_search_executor_config = search.configs.PoolSearchConfig()
_search_executor = search.Executor(_search_executor_config)


def _serialize(ctx: rest.Context, pool: model.Pool) -> rest.Response:
    return pools.serialize_pool(
        pool, options=serialization.get_serialization_options(ctx)
    )


def _get_pool(params: Dict[str, str], user: model.User) -> model.Pool:
    return pools.get_pool_by_id(params["pool_id"], user)


@rest.routes.get("/pools/?")
def get_pools(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "pools:list")
    _search_executor_config.user = ctx.user
    return _search_executor.execute_and_serialize(
        ctx, lambda pool: _serialize(ctx, pool)
    )


@rest.routes.post("/pool/?")
def create_pool(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    auth.verify_privilege(ctx.user, "pools:create")

    names = ctx.get_param_as_string_list("names")
    category = ctx.get_param_as_string("category")
    description = ctx.get_param_as_string("description", default="")
    posts = ctx.get_param_as_int_list("posts", default=[])
    is_private = ctx.get_param_as_bool("private", default=False)
    whitelist_raw = ctx.get_param_as_list("whitelist", default=[])

    pool = pools.create_pool(names, category, posts)
    pool.last_edit_time = datetime.utcnow()
    pools.update_pool_description(pool, description)
    if is_private:
        whitelist_ids = []
        for item in whitelist_raw:
            if isinstance(item, int) or (
                isinstance(item, str) and item.isdigit()
            ):
                whitelist_ids.append(int(item))
            elif isinstance(item, str) and item.strip():
                from szurubooru.func import users
                u = users.get_user_by_name(item.strip())
                if u:
                    whitelist_ids.append(u.user_id)
        if not whitelist_ids:
            whitelist_ids.append(ctx.user.user_id)
        pools.update_pool_whitelist(pool, whitelist_ids)
    ctx.session.add(pool)
    ctx.session.flush()
    snapshots.create(pool, ctx.user)
    ctx.session.commit()
    return _serialize(ctx, pool)


@rest.routes.get("/pool/(?P<pool_id>[^/]+)/?")
def get_pool(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    auth.verify_privilege(ctx.user, "pools:view")
    pool = _get_pool(params, ctx.user)
    return _serialize(ctx, pool)


@rest.routes.put("/pool/(?P<pool_id>[^/]+)/?")
def update_pool(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    pool = _get_pool(params, ctx.user)
    versions.verify_version(pool, ctx)
    versions.bump_version(pool)
    if ctx.has_param("names"):
        auth.verify_privilege(ctx.user, "pools:edit:names")
        pools.update_pool_names(pool, ctx.get_param_as_string_list("names"))
    if ctx.has_param("category"):
        auth.verify_privilege(ctx.user, "pools:edit:category")
        pools.update_pool_category_name(
            pool, ctx.get_param_as_string("category")
        )
    if ctx.has_param("description"):
        auth.verify_privilege(ctx.user, "pools:edit:description")
        pools.update_pool_description(
            pool, ctx.get_param_as_string("description")
        )
    if ctx.has_param("posts"):
        auth.verify_privilege(ctx.user, "pools:edit:posts")
        posts = ctx.get_param_as_int_list("posts")
        pools.update_pool_posts(pool, posts)
    pool.last_edit_time = datetime.utcnow()
    ctx.session.flush()
    snapshots.modify(pool, ctx.user)
    ctx.session.commit()
    return _serialize(ctx, pool)


@rest.routes.delete("/pool/(?P<pool_id>[^/]+)/?")
def delete_pool(ctx: rest.Context, params: Dict[str, str]) -> rest.Response:
    pool = _get_pool(params, ctx.user)
    versions.verify_version(pool, ctx)
    auth.verify_privilege(ctx.user, "pools:delete")
    snapshots.delete(pool, ctx.user)
    pools.delete(pool)
    ctx.session.commit()
    return {}


@rest.routes.post("/pool-merge/?")
def merge_pools(
    ctx: rest.Context, _params: Dict[str, str] = {}
) -> rest.Response:
    source_pool_id = ctx.get_param_as_string("remove")
    target_pool_id = ctx.get_param_as_string("mergeTo")
    source_pool = pools.get_pool_by_id(source_pool_id, ctx.user)
    target_pool = pools.get_pool_by_id(target_pool_id, ctx.user)
    versions.verify_version(source_pool, ctx, "removeVersion")
    versions.verify_version(target_pool, ctx, "mergeToVersion")
    versions.bump_version(target_pool)
    auth.verify_privilege(ctx.user, "pools:merge")
    pools.merge_pools(source_pool, target_pool)
    snapshots.merge(source_pool, target_pool, ctx.user)
    ctx.session.commit()
    return _serialize(ctx, target_pool)
